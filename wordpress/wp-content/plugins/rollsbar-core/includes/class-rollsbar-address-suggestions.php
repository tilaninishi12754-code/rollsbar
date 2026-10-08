<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Staging-only DaData proxy for interactive checkout address suggestions.
 *
 * The API token stays server-side. Customer-facing responses intentionally
 * exclude provider country labels and unrestricted provider address strings.
 */
final class RollsBar_Address_Suggestions {

	private const API_URL          = 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address';
	private const MAX_RESULTS      = 7;
	private const MIN_QUERY_LENGTH = 3;
	private const MAX_QUERY_LENGTH = 160;
	private const RATE_LIMIT       = 90;

	public static function init(): void {
		add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
	}

	public static function register_routes(): void {
		register_rest_route(
			'rollsbar/v1',
			'/address-suggestions',
			array(
				'methods'             => WP_REST_Server::READABLE,
				'callback'            => array( __CLASS__, 'suggest' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'query' => array(
						'required'          => true,
						'sanitize_callback' => 'sanitize_text_field',
					),
				),
			)
		);

		register_rest_route(
			'rollsbar/v1',
			'/address-resolve',
			array(
				'methods'             => WP_REST_Server::CREATABLE,
				'callback'            => array( __CLASS__, 'resolve' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'token' => array(
						'required'          => true,
						'sanitize_callback' => 'sanitize_text_field',
					),
				),
			)
		);
	}

	public static function suggest( WP_REST_Request $request ) {
		$available = self::ensure_available();
		if ( is_wp_error( $available ) ) {
			return $available;
		}

		$limited = self::check_rate_limit();
		if ( is_wp_error( $limited ) ) {
			return $limited;
		}

		$query = trim( (string) $request->get_param( 'query' ) );
		$length = function_exists( 'mb_strlen' ) ? mb_strlen( $query ) : strlen( $query );
		if ( $length < self::MIN_QUERY_LENGTH || $length > self::MAX_QUERY_LENGTH ) {
			return new WP_Error(
				'rollsbar_address_query_length',
				'Введите не менее 3 символов адреса.',
				array( 'status' => 400 )
			);
		}

		$result = self::provider_request( $query, self::MAX_RESULTS );
		if ( is_wp_error( $result ) ) {
			return $result;
		}

		$out  = array();
		$seen = array();
		foreach ( $result as $suggestion ) {
			if ( ! is_array( $suggestion ) ) {
				continue;
			}

			$data = isset( $suggestion['data'] ) && is_array( $suggestion['data'] ) ? $suggestion['data'] : array();
			$country_iso = strtoupper( trim( (string) ( $data['country_iso_code'] ?? '' ) ) );
			if ( '' !== $country_iso && 'RU' !== $country_iso ) {
				continue;
			}

			$display = self::build_local_display( $data );
			$lookup  = trim( (string) ( $suggestion['unrestricted_value'] ?? '' ) );
			if ( '' === $display || '' === $lookup || isset( $seen[ $display ] ) ) {
				continue;
			}

			$seen[ $display ] = true;
			$out[] = array(
				'display' => $display,
				'token'   => self::sign_lookup( $lookup ),
			);
		}

		return rest_ensure_response(
			array(
				'suggestions' => $out,
				'attribution' => array(
					'label' => 'DaData',
					'url'   => 'https://dadata.ru/',
				),
			)
		);
	}

	public static function resolve( WP_REST_Request $request ) {
		$available = self::ensure_available();
		if ( is_wp_error( $available ) ) {
			return $available;
		}

		$limited = self::check_rate_limit();
		if ( is_wp_error( $limited ) ) {
			return $limited;
		}

		$lookup = self::verify_lookup( (string) $request->get_param( 'token' ) );
		if ( is_wp_error( $lookup ) ) {
			return $lookup;
		}

		$result = self::provider_request( $lookup, 1 );
		if ( is_wp_error( $result ) ) {
			return $result;
		}
		if ( empty( $result[0] ) || ! is_array( $result[0] ) ) {
			return new WP_Error(
				'rollsbar_address_not_resolved',
				'Не удалось уточнить выбранный адрес.',
				array( 'status' => 422 )
			);
		}

		$data = isset( $result[0]['data'] ) && is_array( $result[0]['data'] ) ? $result[0]['data'] : array();
		$country_iso = strtoupper( trim( (string) ( $data['country_iso_code'] ?? '' ) ) );
		if ( '' !== $country_iso && 'RU' !== $country_iso ) {
			return new WP_Error(
				'rollsbar_address_outside_supported_country',
				'Этот адрес нельзя использовать для доставки Rolls Bar.',
				array( 'status' => 422 )
			);
		}

		$display = self::build_local_display( $data );
		$lat     = self::coordinate_or_null( $data['geo_lat'] ?? null, -90.0, 90.0 );
		$lon     = self::coordinate_or_null( $data['geo_lon'] ?? null, -180.0, 180.0 );
		$qc_geo  = isset( $data['qc_geo'] ) && is_numeric( $data['qc_geo'] ) ? (int) $data['qc_geo'] : null;
		$policy  = RollsBar_Geocode_Policy::evaluate( $qc_geo );

		if ( null === $lat || null === $lon ) {
			$policy = RollsBar_Geocode_Policy::evaluate( null );
		}

		return rest_ensure_response(
			array(
				'display'  => $display,
				'locality' => self::locality( $data ),
				'street'   => trim( (string) ( $data['street_with_type'] ?? '' ) ),
				'house'    => self::house( $data ),
				'lat'      => $lat,
				'lon'      => $lon,
				'qc_geo'   => $qc_geo,
				'precision'=> $policy,
			)
		);
	}

	private static function ensure_available() {
		if ( 'staging' !== wp_get_environment_type() ) {
			return new WP_Error( 'rollsbar_address_not_available', 'Not found.', array( 'status' => 404 ) );
		}

		if ( ! defined( 'ROLLSBAR_DADATA_API_KEY' ) || '' === trim( (string) ROLLSBAR_DADATA_API_KEY ) ) {
			return new WP_Error(
				'rollsbar_address_provider_unconfigured',
				'Подсказки адреса временно недоступны.',
				array( 'status' => 503 )
			);
		}

		return true;
	}

	private static function check_rate_limit() {
		$ip = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : 'unknown';
		$key = 'rb_addr_rl_' . substr( hash_hmac( 'sha256', $ip, wp_salt( 'nonce' ) ), 0, 32 );
		$count = (int) get_transient( $key );

		if ( $count >= self::RATE_LIMIT ) {
			return new WP_Error(
				'rollsbar_address_rate_limited',
				'Слишком много запросов. Попробуйте через минуту.',
				array( 'status' => 429 )
			);
		}

		set_transient( $key, $count + 1, MINUTE_IN_SECONDS );
		return true;
	}

	private static function provider_request( string $query, int $count ) {
		$payload = array(
			'query'    => $query,
			'count'    => max( 1, min( 20, $count ) ),
			'language' => 'ru',
		);

		if ( $count > 1 ) {
			$payload['locations_boost'] = array(
				array( 'city' => 'Симферополь' ),
			);
		}

		$response = wp_remote_post(
			self::API_URL,
			array(
				'timeout' => 5,
				'headers' => array(
					'Accept'        => 'application/json',
					'Content-Type'  => 'application/json',
					'Authorization' => 'Token ' . trim( (string) ROLLSBAR_DADATA_API_KEY ),
				),
				'body'    => wp_json_encode( $payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ),
			)
		);

		if ( is_wp_error( $response ) ) {
			return new WP_Error(
				'rollsbar_address_provider_unreachable',
				'Сервис адресов временно недоступен.',
				array( 'status' => 502 )
			);
		}

		$status = (int) wp_remote_retrieve_response_code( $response );
		$body   = json_decode( (string) wp_remote_retrieve_body( $response ), true );
		if ( 200 !== $status || ! is_array( $body ) || ! isset( $body['suggestions'] ) || ! is_array( $body['suggestions'] ) ) {
			return new WP_Error(
				'rollsbar_address_provider_error',
				'Сервис адресов временно недоступен.',
				array( 'status' => 502 )
			);
		}

		return $body['suggestions'];
	}

	private static function locality( array $data ): string {
		$settlement = trim( (string) ( $data['settlement_with_type'] ?? '' ) );
		if ( '' !== $settlement ) {
			return $settlement;
		}

		return trim( (string) ( $data['city_with_type'] ?? '' ) );
	}

	private static function house( array $data ): string {
		$parts = array();
		$type  = trim( (string) ( $data['house_type'] ?? '' ) );
		$house = trim( (string) ( $data['house'] ?? '' ) );
		if ( '' !== $house ) {
			$parts[] = trim( $type . ' ' . $house );
		}

		$block_type = trim( (string) ( $data['block_type'] ?? '' ) );
		$block      = trim( (string) ( $data['block'] ?? '' ) );
		if ( '' !== $block ) {
			$parts[] = trim( $block_type . ' ' . $block );
		}

		return implode( ' ', array_filter( $parts ) );
	}

	private static function build_local_display( array $data ): string {
		$parts = array_filter(
			array(
				self::locality( $data ),
				trim( (string) ( $data['street_with_type'] ?? '' ) ),
				self::house( $data ),
			)
		);

		return implode( ', ', array_values( array_unique( $parts ) ) );
	}

	private static function coordinate_or_null( $value, float $min, float $max ): ?float {
		if ( ! is_numeric( $value ) ) {
			return null;
		}
		$number = (float) $value;
		return $number >= $min && $number <= $max ? $number : null;
	}

	private static function sign_lookup( string $lookup ): string {
		$payload = rtrim( strtr( base64_encode( $lookup ), '+/', '-_' ), '=' );
		$signature = hash_hmac( 'sha256', $payload, wp_salt( 'auth' ) );
		return $payload . '.' . $signature;
	}

	private static function verify_lookup( string $token ) {
		if ( strlen( $token ) > 1200 || false === strpos( $token, '.' ) ) {
			return new WP_Error( 'rollsbar_address_token_invalid', 'Некорректный адрес.', array( 'status' => 400 ) );
		}

		list( $payload, $signature ) = explode( '.', $token, 2 );
		$expected = hash_hmac( 'sha256', $payload, wp_salt( 'auth' ) );
		if ( ! hash_equals( $expected, $signature ) ) {
			return new WP_Error( 'rollsbar_address_token_invalid', 'Некорректный адрес.', array( 'status' => 400 ) );
		}

		$padding = strlen( $payload ) % 4;
		if ( $padding ) {
			$payload .= str_repeat( '=', 4 - $padding );
		}
		$decoded = base64_decode( strtr( $payload, '-_', '+/' ), true );
		if ( false === $decoded || '' === trim( $decoded ) || strlen( $decoded ) > 600 ) {
			return new WP_Error( 'rollsbar_address_token_invalid', 'Некорректный адрес.', array( 'status' => 400 ) );
		}

		return $decoded;
	}
}

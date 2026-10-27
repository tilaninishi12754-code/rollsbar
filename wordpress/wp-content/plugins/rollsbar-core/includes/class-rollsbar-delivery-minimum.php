<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

/** Workbook-derived identity rules. Never infer a boundary from a coordinate. */
final class RollsBar_Delivery_Minimum {
	public static function rules(): array {
		static $rules;
		if ( null === $rules ) {
			$rules = json_decode( file_get_contents( dirname( __DIR__ ) . '/data/delivery-minimum.json' ), true, 512, JSON_THROW_ON_ERROR );
		}
		return $rules['rules'];
	}

	public static function normalize( string $value ): string {
		return trim( preg_replace( '/[\s.\-]+/u', ' ', str_replace( 'ё', 'е', mb_strtolower( $value, 'UTF-8' ) ) ) );
	}

	public static function classify( array $data ): array {
		$unknown = array( 'status' => 'unresolved', 'minimum' => null, 'message' => 'Не удалось определить условия доставки. Уточните адрес до дома или свяжитесь с нами: +7 978 688-22-88.' );
		if ( empty( $data['house'] ) || empty( $data['house_fias_id'] ) ) {
			$unknown['message'] = 'Выберите точный адрес с номером дома из подсказок.';
			return $unknown;
		}
		// Scope every same-named street/locality to the provider's administrative identity.
		$city = self::normalize( (string) ( $data['city'] ?? '' ) );
		$area = self::normalize( (string) ( $data['area'] ?? '' ) );
		$region = self::normalize( (string) ( $data['region'] ?? '' ) );
		if ( 'крым' !== $region || ( 'симферополь' !== $city && 'симферопольский' !== $area ) ) { return $unknown; }
		$street = self::normalize( (string) ( $data['street'] ?? '' ) );
		if ( 'симферополь' === $city && in_array( $street, array( 'кечкеметская', 'беспалова' ), true ) ) {
			$unknown['status'] = 'ambiguous';
			$unknown['message'] = 'Для этого участка улицы условия доставки требуют уточнения. Позвоните: +7 978 688-22-88.';
			return $unknown;
		}
		$matches = array();
		foreach ( self::rules() as $rule ) {
			// These are whole-identity rules with a verified FIAS house. Coordinates
			// never determine a minimum, split a street, or imply polygon membership.
			// The independent geocode policy retains the original qc_geo restrictions.
			if ( ! empty( $data['planning_structure_fias_id'] ) && in_array( self::normalize( (string) ( $data['planning_structure'] ?? '' ) ), array_map( array( __CLASS__, 'normalize' ), $rule['area_aliases'] ?? array() ), true ) ) { $matches[] = $rule; continue; }
			$type = $rule['type'];
			if ( 'unresolved' === $type ) { continue; }
			$key = 'street' === $type ? 'street' : ( 'locality' === $type ? ( ! empty( $data['settlement'] ) ? 'settlement' : 'city' ) : 'planning_structure' );
			if ( empty( $data[ $key . '_fias_id' ] ) ) { continue; }
			if ( 'street' === $type && ( 'симферополь' !== $city || ! empty( $data['settlement'] ) ) ) { continue; }
			$value = self::normalize( (string) ( $data[ $key ] ?? '' ) );
			foreach ( $rule['aliases'] as $alias ) {
				if ( $value === self::normalize( $alias ) ) { $matches[] = $rule; break; }
			}
		}
		$amounts = array_unique( array_column( $matches, 'minimum' ) );
		if ( 1 !== count( $amounts ) ) { return $unknown; }
		$minimum = (int) reset( $amounts );
		return array( 'status' => 'resolved', 'minimum' => $minimum, 'basis' => 'fias_identity', 'sources' => array_column( $matches, 'cell' ), 'message' => 'Бесплатная доставка при заказе от ' . number_format( $minimum, 0, '.', ' ' ) . ' ₽.' );
	}

	/** Signed provider identity; client-supplied minima never enter this contract. */
	public static function proof( array $data, string $display ): string {
		$keys = array( 'qc_geo', 'house', 'house_fias_id', 'geo_lat', 'geo_lon', 'region', 'city', 'city_fias_id', 'area', 'settlement', 'settlement_fias_id', 'street', 'street_fias_id', 'planning_structure', 'planning_structure_fias_id' );
		$payload = base64_encode( wp_json_encode( array( 'data' => array_intersect_key( $data, array_flip( $keys ) ), 'display' => $display, 'expires' => time() + 12 * HOUR_IN_SECONDS ) ) );
		return $payload . '.' . hash_hmac( 'sha256', $payload, wp_salt( 'auth' ) );
	}

	public static function verify( string $proof, string $address, float $amount ): array {
		$invalid = array( 'status' => 'unresolved', 'minimum' => null, 'message' => 'Выберите адрес с домом из подсказок, чтобы определить условия доставки.' );
		if ( strlen( $proof ) > 10000 || 1 !== substr_count( $proof, '.' ) ) { return $invalid; }
		list( $payload, $signature ) = explode( '.', $proof, 2 );
		if ( ! hash_equals( hash_hmac( 'sha256', $payload, wp_salt( 'auth' ) ), $signature ) ) { return $invalid; }
		$decoded = json_decode( (string) base64_decode( $payload, true ), true );
		if ( ! is_array( $decoded ) || ( $decoded['expires'] ?? 0 ) < time() || trim( $address ) !== ( $decoded['display'] ?? null ) || ! is_array( $decoded['data'] ?? null ) ) { return $invalid; }
		$result = self::classify( $decoded['data'] );
		if ( 'resolved' === $result['status'] && (int) round( $amount * 100 ) < $result['minimum'] * 100 ) {
			$result['status'] = 'below_minimum';
			$result['message'] = 'Для доставки добавьте товары на ' . number_format( $result['minimum'] - $amount, 2, ',', ' ' ) . ' ₽. Минимальный заказ — ' . $result['minimum'] . ' ₽.';
		}
		return $result;
	}
}

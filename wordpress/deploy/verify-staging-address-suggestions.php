<?php
/**
 * Runtime verification for staging-only RollsBar DaData address routes.
 *
 * Execute through WP-CLI after the staging plugin and server-side DaData key
 * are installed. The script intentionally prints only safe local displays and
 * precision metadata; provider raw strings/country metadata are never logged.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit( 1 );
}

function rollsbar_address_smoke_fail( string $message ): void {
	fwrite( STDERR, 'ADDRESS SUGGESTIONS FAIL: ' . $message . PHP_EOL );
	exit( 1 );
}

function rollsbar_address_smoke_request( string $method, string $route, array $params ): array {
	$request = new WP_REST_Request( $method, $route );
	foreach ( $params as $key => $value ) {
		$request->set_param( $key, $value );
	}

	$response = rest_do_request( $request );
	if ( is_wp_error( $response ) ) {
		rollsbar_address_smoke_fail( $response->get_error_message() );
	}
	if ( $response->get_status() >= 400 ) {
		$data = $response->get_data();
		$message = is_array( $data ) && ! empty( $data['message'] ) ? (string) $data['message'] : 'HTTP ' . $response->get_status();
		rollsbar_address_smoke_fail( $message );
	}

	$data = $response->get_data();
	if ( ! is_array( $data ) ) {
		rollsbar_address_smoke_fail( 'REST response is not an array.' );
	}
	return $data;
}

function rollsbar_address_smoke_first_suggestion( string $query ): array {
	$payload = rollsbar_address_smoke_request(
		'GET',
		'/rollsbar/v1/address-suggestions',
		array( 'query' => $query )
	);

	if ( empty( $payload['suggestions'][0] ) || ! is_array( $payload['suggestions'][0] ) ) {
		rollsbar_address_smoke_fail( 'No suggestion returned for a runtime probe.' );
	}

	$item = $payload['suggestions'][0];
	foreach ( array( 'country', 'country_iso', 'country_iso_code', 'value', 'unrestricted_value' ) as $forbidden ) {
		if ( array_key_exists( $forbidden, $item ) ) {
			rollsbar_address_smoke_fail( 'Forbidden provider field leaked into customer suggestion payload.' );
		}
	}

	$display = isset( $item['display'] ) ? (string) $item['display'] : '';
	$token   = isset( $item['token'] ) ? (string) $item['token'] : '';
	if ( '' === $display || '' === $token ) {
		rollsbar_address_smoke_fail( 'Suggestion is missing safe display or signed token.' );
	}
	if ( false !== mb_stripos( $display, 'Россия' ) || false !== mb_stripos( $display, 'Украина' ) ) {
		rollsbar_address_smoke_fail( 'Country label leaked into customer display.' );
	}

	return $item;
}

function rollsbar_address_smoke_resolve( array $item ): array {
	$payload = rollsbar_address_smoke_request(
		'POST',
		'/rollsbar/v1/address-resolve',
		array( 'token' => (string) $item['token'] )
	);

	foreach ( array( 'country', 'country_iso', 'country_iso_code', 'value', 'unrestricted_value' ) as $forbidden ) {
		if ( array_key_exists( $forbidden, $payload ) ) {
			rollsbar_address_smoke_fail( 'Forbidden provider field leaked into resolved customer payload.' );
		}
	}

	$display = isset( $payload['display'] ) ? (string) $payload['display'] : '';
	if ( false !== mb_stripos( $display, 'Россия' ) || false !== mb_stripos( $display, 'Украина' ) ) {
		rollsbar_address_smoke_fail( 'Country label leaked into resolved customer display.' );
	}
	if ( ! isset( $payload['lat'], $payload['lon'] ) || ! is_numeric( $payload['lat'] ) || ! is_numeric( $payload['lon'] ) ) {
		rollsbar_address_smoke_fail( 'Resolved coordinates are missing.' );
	}
	if ( empty( $payload['precision'] ) || ! is_array( $payload['precision'] ) ) {
		rollsbar_address_smoke_fail( 'Precision policy is missing from resolved payload.' );
	}

	return $payload;
}

$exact_item = rollsbar_address_smoke_first_suggestion( 'Республика Крым, Симферополь, улица Гагарина, 17' );
$exact      = rollsbar_address_smoke_resolve( $exact_item );
if ( 0 !== (int) $exact['qc_geo'] || true !== ( $exact['precision']['allow_auto_zone'] ?? null ) ) {
	rollsbar_address_smoke_fail( 'Exact-house probe did not resolve as fail-open qc_geo=0.' );
}

$low_item = rollsbar_address_smoke_first_suggestion( 'Республика Крым, Симферопольский район, село Дубки, улица Раздерина, 12' );
$low      = rollsbar_address_smoke_resolve( $low_item );
$low_qc   = isset( $low['qc_geo'] ) && is_numeric( $low['qc_geo'] ) ? (int) $low['qc_geo'] : null;
if ( null === $low_qc || $low_qc < 1 || true !== ( $low['precision']['requires_confirmation'] ?? null ) || false !== ( $low['precision']['allow_auto_zone'] ?? null ) ) {
	rollsbar_address_smoke_fail( 'Low-precision probe did not fail closed.' );
}

echo 'ADDRESS SUGGESTIONS RUNTIME PASS' . PHP_EOL;
echo 'exact_qc_geo=' . (int) $exact['qc_geo'] . ' allow_auto_zone=yes' . PHP_EOL;
echo 'low_precision_qc_geo=' . $low_qc . ' allow_auto_zone=no' . PHP_EOL;
echo 'country_labels_exposed=no' . PHP_EOL;

<?php
/**
 * Runtime verifier for the prepared Yandex Metrica integration.
 *
 * No network request is made. The test temporarily injects a synthetic counter
 * ID into the existing Rolls Bar settings, verifies registration/configuration,
 * and restores the exact original option before returning.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit( 1 );
}

$fail = static function ( string $message ): void {
	fwrite( STDERR, $message . "\n" );
	throw new RuntimeException( $message );
};

if ( ! class_exists( 'RollsBar_Analytics' ) || ! class_exists( 'RollsBar_Settings' ) ) {
	fwrite( STDERR, "Analytics dependencies are not loaded.\n" );
	exit( 1 );
}

$original_exists = get_option( 'rollsbar_settings', null ) !== null;
$original = get_option( 'rollsbar_settings', array() );
$original = is_array( $original ) ? $original : array();
$original_counter = RollsBar_Analytics::counter_id();

try {
	$goals = RollsBar_Analytics::goals();
	$required = array(
		'add_to_cart',
		'open_cart',
		'begin_checkout',
		'submit_order',
		'purchase',
		'phone_click',
	);
	foreach ( $required as $goal ) {
		if ( ! isset( $goals[ $goal ] ) || $goal !== (string) $goals[ $goal ] ) {
			$fail( "Required analytics goal is missing or unstable: {$goal}" );
		}
	}

	foreach ( $goals as $goal_id ) {
		if ( preg_match( '/[\\\\\/#&?="]/', (string) $goal_id ) ) {
			$fail( 'Analytics goal ID contains a character forbidden by the Metrica JavaScript-event goal rules.' );
		}
	}

	if ( 'rollsbar_analytics_consent_v1' !== RollsBar_Analytics::consent_storage_key() ) {
		$fail( 'Analytics consent storage key changed unexpectedly.' );
	}

	$invalid = RollsBar_Settings::sanitize( array( 'metrika_counter_id' => 'abc-12' ) );
	if ( ! empty( $invalid['metrika_counter_id'] ) ) {
		$fail( 'Invalid Metrica counter ID was not rejected.' );
	}
	$valid = RollsBar_Settings::sanitize( array( 'metrika_counter_id' => '12345678' ) );
	if ( '12345678' !== (string) ( $valid['metrika_counter_id'] ?? '' ) ) {
		$fail( 'Valid numeric Metrica counter ID was not accepted.' );
	}

	$synthetic = $original;
	$synthetic['metrika_counter_id'] = '12345678';
	update_option( 'rollsbar_settings', $synthetic, false );
	if ( ! RollsBar_Analytics::is_enabled() || '12345678' !== RollsBar_Analytics::counter_id() ) {
		$fail( 'Synthetic Metrica counter did not enable the prepared integration.' );
	}

	wp_dequeue_script( 'rollsbar-analytics' );
	wp_deregister_script( 'rollsbar-analytics' );
	wp_dequeue_style( 'rollsbar-analytics-consent' );
	wp_deregister_style( 'rollsbar-analytics-consent' );
	RollsBar_Analytics::enqueue_assets();

	if ( ! wp_script_is( 'rollsbar-analytics', 'enqueued' ) ) {
		$fail( 'Analytics script was not enqueued for a valid synthetic counter.' );
	}
	if ( ! wp_style_is( 'rollsbar-analytics-consent', 'enqueued' ) ) {
		$fail( 'Analytics consent styles were not enqueued for a valid synthetic counter.' );
	}

	$before = wp_scripts()->get_data( 'rollsbar-analytics', 'before' );
	$before_text = is_array( $before ) ? implode( "\n", $before ) : (string) $before;
	foreach ( array( '"counterId":"12345678"', '"webvisor":false', '"trackLinks":false', '"sendTitle":false' ) as $needle ) {
		if ( false === strpos( $before_text, $needle ) ) {
			$fail( "Analytics runtime config is missing privacy-safe invariant: {$needle}" );
		}
	}

	$script_file = ROLLSBAR_CORE_DIR . 'assets/js/analytics.js';
	if ( ! is_readable( $script_file ) ) {
		$fail( 'Analytics JavaScript file is missing.' );
	}
	$script = (string) file_get_contents( $script_file );
	foreach ( array( 'https://mc.yandex.ru/metrika/tag.js', "'reachGoal'", "readConsent()!=='allow'", 'data-rollsbar-analytics-allow', 'added_to_cart', 'phone_click', 'submit_order' ) as $needle ) {
		if ( false === strpos( $script, $needle ) ) {
			$fail( "Analytics JavaScript is missing required wiring: {$needle}" );
		}
	}
	if ( false !== strpos( $script, 'webvisor:true' ) || false !== strpos( $script, 'webvisor: true' ) ) {
		$fail( 'Webvisor must not be enabled by the prepared integration.' );
	}

	$banner_capture = static function (): string {
		ob_start();
		RollsBar_Analytics::render_consent_banner();
		return (string) ob_get_clean();
	};
	$banner = $banner_capture();
	foreach ( array( 'data-rollsbar-cookie-consent', 'data-rollsbar-analytics-deny', 'data-rollsbar-analytics-allow', '/cookies/' ) as $needle ) {
		if ( false === strpos( $banner, $needle ) ) {
			$fail( "Analytics consent notice is missing: {$needle}" );
		}
	}
} catch ( Throwable $error ) {
	fwrite( STDERR, 'Analytics runtime smoke failed: ' . $error->getMessage() . "\n" );
	exit( 1 );
} finally {
	if ( $original_exists ) {
		update_option( 'rollsbar_settings', $original, false );
	} else {
		delete_option( 'rollsbar_settings' );
	}
}

$restored_counter = RollsBar_Analytics::counter_id();
if ( $restored_counter !== $original_counter ) {
	fwrite( STDERR, "Analytics verifier did not restore the original counter setting.\n" );
	exit( 1 );
}

echo "ANALYTICS PREPARATION RUNTIME PASS\n";
echo 'live_counter_configured=' . ( '' !== $original_counter ? 'yes' : 'no' ) . "\n";
echo "synthetic_counter_loader=pass\n";
echo "consent_gate=required_before_tag_load\n";
echo "webvisor=off\n";
echo "marketing_tools=not_configured\n";
echo 'required_goals=' . implode( ',', $required ) . "\n";

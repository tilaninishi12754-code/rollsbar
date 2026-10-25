<?php
// Local WordPress adapters only; execute real enqueue callbacks, never WordPress/HTTP.
define( 'ABSPATH', __DIR__ );
$root = dirname( __DIR__, 2 );
$input = json_decode( stream_get_contents( STDIN ), true, 512, JSON_THROW_ON_ERROR );
$component = $input['component'] ?? 'both';
$calls = array();
$hooks = array();
define( 'ROLLSBAR_CORE_VERSION', '0.1.8' );
define( 'ROLLSBAR_CORE_FILE', $root . '/wordpress/wp-content/plugins/rollsbar-core/rollsbar-core.php' );
function add_action( $hook, $callback, ...$args ) { $GLOBALS['hooks'][ $hook ][] = $callback; }
function add_filter( ...$args ) {}
function wp_get_theme() { return new class { public function get( $key ) { return '0.1.0'; } }; }
function get_stylesheet_directory() { return $GLOBALS['root'] . '/wordpress/wp-content/themes/rollsbar-theme'; }
function get_template_directory() { return get_stylesheet_directory(); }
function get_template_directory_uri() { return 'https://fixture.test/theme'; }
function get_stylesheet_uri() { return get_template_directory_uri() . '/style.css'; }
function is_page( $slugs ) { return $GLOBALS['input']['legal'] ?? true; }
function is_front_page() { return false; }
function is_admin() { return false; }
function is_checkout() { return $GLOBALS['input']['checkout'] ?? true; }
function is_cart() { return false; }
function is_order_received_page() { return false; }
function wp_get_environment_type() { return 'production'; }
function rest_url( $path ) { return 'https://fixture.test/wp-json/' . $path; }
function wp_json_encode( ...$args ) { return json_encode( ...$args ); }
function plugins_url( $path, $file ) { return 'https://fixture.test/plugin/' . $path; }
function wp_enqueue_style( ...$args ) { $GLOBALS['calls'][] = array( 'style', $args ); }
function wp_enqueue_script( ...$args ) { $GLOBALS['calls'][] = array( 'script', $args ); }
function wp_add_inline_script( ...$args ) { $GLOBALS['calls'][] = array( 'inline', $args ); }
class RollsBar_Settings {
	public static function get( $key ) { return ( $GLOBALS['input']['analytics'] ?? true ) ? '1234567' : ''; }
}

if ( 'plugin' !== $component ) {
	require $input['theme_source'] ?? get_template_directory() . '/functions.php';
}
if ( 'theme' !== $component ) {
	require $input['checkout_source'] ?? $root . '/wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php';
	require $input['analytics_source'] ?? $root . '/wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-analytics.php';
}

if ( 'enqueue' === ( $input['mode'] ?? 'enqueue' ) ) {
	if ( 'plugin' !== $component ) {
		foreach ( $hooks['wp_enqueue_scripts'] ?? array() as $callback ) { $callback(); }
	}
	if ( 'theme' !== $component ) {
		RollsBar_Checkout::enqueue_checkout_assets();
		RollsBar_Analytics::enqueue_assets();
	}
	echo json_encode( $calls, JSON_THROW_ON_ERROR );
} else {
	if ( isset( $input['read_scope'] ) ) {
		ini_set( 'open_basedir', $input['read_scope'] );
	}
	$versions = array();
	foreach ( $input['items'] as $item ) {
		$versions[] = array(
			'theme' => rollsbar_theme_asset_version( $item['path'], $item['fallback'] ),
			'plugin' => RollsBar_Asset_Version::for_file( $item['path'], $item['fallback'] ),
		);
	}
	if ( isset( $input['rewrite'] ) ) {
		// Only a newly created test fixture can be rewritten for the memoization test.
		$path = realpath( $input['items'][0]['path'] );
		$directory = realpath( $input['fixture_directory'] );
		if ( false === $path || false === $directory || dirname( $path ) !== $directory ) { exit( 2 ); }
		file_put_contents( $path, $input['rewrite'] );
		$versions[] = array(
			'theme' => rollsbar_theme_asset_version( $path, 'memo-fallback' ),
			'plugin' => RollsBar_Asset_Version::for_file( $path, 'memo-fallback' ),
		);
	}
	echo json_encode( $versions, JSON_THROW_ON_ERROR );
}

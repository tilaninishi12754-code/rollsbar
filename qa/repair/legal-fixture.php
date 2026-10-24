<?php
// Isolated WordPress adapters: execute the real provisioner, checkout/review
// classes, footer and verifier. No WordPress DB, HTTP request or email transport.
namespace Automattic\WooCommerce\Blocks {
	class Package {
		public static function container() { return new class {
			public function get( $service ) { return new class {
				public function get_additional_fields() { return $GLOBALS['fields']; }
			}; }
		}; }
	}
}
namespace {
	define( 'ABSPATH', __DIR__ ); define( 'OBJECT', 'OBJECT' );
	$root = dirname( __DIR__, 2 ); $variant = $argv[1]; $fixture_theme = $argv[2];
	$pages = array(); $settings = array(); $fields = array();
	class WP_Post {
		public $ID; public $post_name; public $post_status; public $post_content;
		public function __construct( array $data ) { foreach ( array( 'ID', 'post_name', 'post_status', 'post_content' ) as $k ) { $this->$k = $data[$k]; } }
	}
	function get_page_by_path( $slug, ...$unused ) { return $GLOBALS['pages'][$slug] ?? null; }
	function get_post( $id ) { foreach ( $GLOBALS['pages'] as $p ) { if ( $p->ID === $id ) { return $p; } } return null; }
	function wp_insert_post( $data, ...$unused ) { $data['ID'] = count( $GLOBALS['pages'] ) + 1; $GLOBALS['pages'][$data['post_name']] = new WP_Post( $data ); return $data['ID']; }
	function update_post_meta( ...$unused ) {}
	function update_option( $key, $value, ...$unused ) { $GLOBALS['settings'][$key] = $value; }
	function get_option( $key, $fallback = false ) { return $GLOBALS['settings'][$key] ?? $fallback; }
	function wp_parse_args( $value, $defaults ) { return array_merge( $defaults, $value ); }
	function is_wp_error( $value ) { return false; }
	function wp_strip_all_tags( $value ) { return strip_tags( $value ); }
	function wp_kses_post( $value ) { return $value; }
	function esc_url( $value ) { return htmlspecialchars( $value, ENT_QUOTES, 'UTF-8' ); }
	function esc_html( $value ) { return esc_url( $value ); }
	function esc_attr( $value ) { return esc_url( $value ); }
	function home_url( $path = '/' ) { return 'https://staging.rollsbar.ru' . $path; }
	function absint( $value ) { return abs( (int) $value ); }
	function get_template_directory() { return $GLOBALS['fixture_theme']; }
	function get_template_directory_uri() { return '/theme'; }
	function get_theme_mod( $key ) { return 0; }
	function is_front_page() { return 'internal-page' !== $GLOBALS['variant']; }
	function wp_footer() {}
	function add_action( ...$unused ) {}
	function woocommerce_register_additional_checkout_field( $field ) { $GLOBALS['fields'][$field['id']] = $field; }
	putenv( 'PROJECT_ROOT=' . $root );
	ob_start(); ( static function () use ( $root ) { require $root . '/wordpress/deploy/provision-legal-pages.php'; } )(); ob_end_clean();
	require $root . '/wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-settings.php';
	require $root . '/wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php';
	require $root . '/wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-reviews.php';
	RollsBar_Checkout::register_additional_fields();
	switch ( $variant ) {
		case 'wrong-terms': $settings['woocommerce_terms_page_id'] = 999; break;
		case 'wrong-privacy': $settings['wp_page_for_privacy_policy'] = 999; break;
		case 'missing-page': unset( $pages['pravovaya-informaciya'] ); break;
		case 'draft-page': $pages['pravovaya-informaciya']->post_status = 'draft'; break;
		case 'empty-page': $pages['publichnaya-oferta']->post_content = '<p> </p>'; break;
		case 'stale-page': $pages['cookies']->post_content .= '<a href="privacy.html">Privacy</a>'; break;
		case 'sber-russian': $pages['bezopasnost-onlajn-oplaty']->post_content .= 'СберБанк'; break;
		case 'sber-latin': $pages['bezopasnost-onlajn-oplaty']->post_content .= 'SberBank'; break;
		case 'missing-checkout-consent': unset( $fields['rollsbar/privacy-consent'] ); break;
		case 'optional-checkout-consent': $fields['rollsbar/privacy-consent']['required'] = false; break;
		case 'missing-delivery-disclosure': $pages['dostavka-i-oplata']->post_content = 'Самовывоз'; break;
		case 'missing-requisites': $pages['rekvizity-prodavca']->post_content = 'Продавец'; break;
	}
	require $argv[3] ?? $root . '/wordpress/deploy/verify-staging-legal-pages.php';
	// Also execute the existing payment-at-receipt verifier with in-memory Woo.
	function WC() { return new class {
		public function payment_gateways() { return new class {
			public function payment_gateways() { return array( 'cod' => (object) array( 'enabled' => 'yes', 'title' => 'Оплата при получении' ) ); }
		}; }
	}; }
	require $root . '/wordpress/deploy/verify-staging-payment-readiness.php';
}

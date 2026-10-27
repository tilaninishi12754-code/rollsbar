<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

/** Native Woo shipping/rates and pre-order validation. Staging batch only. */
final class RollsBar_Delivery_Checkout {
	public static function init(): void {
		if ( 'staging' !== wp_get_environment_type() ) { return; }
		add_action( 'woocommerce_shipping_init', array( __CLASS__, 'load_method' ) );
		add_filter( 'woocommerce_shipping_methods', static function ( $methods ) { $methods['rollsbar_delivery'] = 'RollsBar_Native_Delivery_Method'; return $methods; } );
		add_filter( 'rest_request_before_callbacks', array( __CLASS__, 'validate_request' ), 10, 3 );
		add_action( 'woocommerce_blocks_loaded', static function () {
			woocommerce_store_api_register_endpoint_data( array(
				'endpoint' => \Automattic\WooCommerce\StoreApi\Schemas\V1\CheckoutSchema::IDENTIFIER,
				'namespace' => 'rollsbar-delivery',
				'data_callback' => static fn() => array( 'address_proof' => '' ),
				'schema_callback' => static fn() => array( 'address_proof' => array( 'type' => 'string', 'readonly' => false, 'context' => array( 'view', 'edit' ) ) ),
				'schema_type' => ARRAY_A,
			) );
		} );
	}

	public static function load_method(): void {
		if ( class_exists( 'RollsBar_Native_Delivery_Method' ) ) { return; }
		require_once __DIR__ . '/class-rollsbar-native-delivery-method.php';
	}

	public static function mode(): string {
		$chosen = WC()->session->get( 'chosen_shipping_methods', array() );
		$rate = 1 === count( $chosen ) ? (string) reset( $chosen ) : '';
		if ( 'rollsbar_delivery' === $rate ) { return 'delivery'; }
		if ( str_starts_with( $rate, 'pickup_location:' ) ) { return 'pickup'; }
		return WC()->session->get( 'rollsbar_cart_mode', 'delivery' );
	}

	public static function choose_mode( string $mode ): void {
		if ( 'staging' !== wp_get_environment_type() ) { return; }
		WC()->cart->calculate_shipping();
		$chosen = array();
		foreach ( WC()->shipping()->get_packages() as $id => $package ) {
			foreach ( $package['rates'] as $rate_id => $rate ) {
				if ( ( 'pickup' === $mode && 'pickup_location' === $rate->get_method_id() ) || ( 'delivery' === $mode && 'rollsbar_delivery' === $rate->get_method_id() ) ) { $chosen[ $id ] = $rate_id; break; }
			}
		}
		if ( $chosen ) { WC()->session->set( 'chosen_shipping_methods', $chosen ); WC()->cart->calculate_totals(); }
	}

	public static function validate_request( $response, $handler, $request ) {
		if ( null !== $response || 'POST' !== $request->get_method() || ! preg_match( '#^/wc/store/v[0-9]+/checkout$#', $request->get_route() ) ) { return $response; }
		if ( ! WC()->cart || ! WC()->session ) { wc_load_cart(); }
		$chosen = WC()->session->get( 'chosen_shipping_methods', array() );
		if ( 1 !== count( $chosen ) ) { return new WP_Error( 'rollsbar_delivery_mode', 'Выберите доставку или самовывоз.', array( 'status' => 400 ) ); }
		$rate = (string) reset( $chosen );
		// The native controller still validates that this pickup rate actually exists.
		if ( str_starts_with( $rate, 'pickup_location:' ) ) { return $response; }
		if ( 'rollsbar_delivery' !== $rate ) { return new WP_Error( 'rollsbar_delivery_mode', 'Выберите доступный способ получения.', array( 'status' => 400 ) ); }
		$shipping = (array) $request->get_param( 'shipping_address' );
		$billing = (array) $request->get_param( 'billing_address' );
		$address = (string) ( $shipping['address_1'] ?? $billing['address_1'] ?? '' );
		$extensions = (array) $request->get_param( 'extensions' );
		$proof = (string) ( $extensions['rollsbar-delivery']['address_proof'] ?? '' );
		// Native line totals after discounts; exclude fees, shipping and taxes.
		WC()->cart->calculate_totals();
		$result = RollsBar_Delivery_Minimum::verify( $proof, $address, (float) WC()->cart->get_cart_contents_total() );
		return 'resolved' === $result['status'] ? $response : new WP_Error( 'rollsbar_delivery_' . $result['status'], $result['message'], array( 'status' => 400, 'minimum' => $result['minimum'] ) );
	}
}

<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

require_once __DIR__ . '/class-rollsbar-asset-version.php';

/**
 * Checkout behavior owned by Rolls Bar Core.
 *
 * Uses the WooCommerce Additional Checkout Fields API so the fields work with
 * the modern Checkout Block / Store API instead of relying on legacy classic
 * checkout hooks.
 */
final class RollsBar_Checkout {

	private const FIELD_PREFIX = 'rollsbar/';
	private static array $contact_template_buffers = array();

	public static function init(): void {
		add_action( 'init', array( __CLASS__, 'canonical_staging_host' ), -100 );
		add_filter( 'wp_headers', array( __CLASS__, 'dynamic_page_headers' ) );
		add_filter( 'rest_request_after_callbacks', array( __CLASS__, 'clear_completed_note' ), 20, 3 );
		add_filter( 'option_woocommerce_cod_settings', array( __CLASS__, 'receipt_payment_settings' ) );
		add_filter( 'woocommerce_order_get_payment_method_title', array( __CLASS__, 'receipt_payment_title' ), 20, 2 );
		add_filter( 'woocommerce_order_shipping_to_display', array( __CLASS__, 'pickup_order_display' ), 20, 2 );
		add_action( 'woocommerce_init', array( __CLASS__, 'register_additional_fields' ) );
		add_action( 'wp_enqueue_scripts', array( __CLASS__, 'enqueue_checkout_assets' ) );
		add_filter( 'wp_resource_hints', array( __CLASS__, 'checkout_resource_hints' ), 20, 2 );
		add_action( 'wp_enqueue_scripts', array( __CLASS__, 'native_checkout_scripts' ), 100 );
		add_filter( 'woocommerce_get_country_locale', array( __CLASS__, 'field_locale' ) );
		add_filter( 'woocommerce_validate_phone', array( __CLASS__, 'validate_phone' ), 10, 3 );
		add_action( 'template_redirect', array( __CLASS__, 'prepare_native_customer' ) );
		add_filter( 'rest_pre_dispatch', array( __CLASS__, 'prepare_store_request' ), 10, 3 );
		add_action( 'woocommerce_blocks_checkout_enqueue_data', array( __CLASS__, 'native_field_data' ), 5 );
		add_filter( 'option_pickup_location_pickup_locations', array( __CLASS__, 'pickup_locations' ) );
		add_filter( 'pre_wp_mail', array( __CLASS__, 'block_internal_mail' ), PHP_INT_MAX, 2 );
		add_filter( 'wp_mail', array( __CLASS__, 'remove_internal_reply_headers' ), PHP_INT_MAX );
		add_filter( 'woocommerce_checkout_registration_enabled', '__return_false' );
		add_filter( 'woocommerce_checkout_registration_required', '__return_false' );
		add_filter( 'option_woocommerce_enable_delayed_account_creation', '__return_false' );
		add_filter( 'default_option_woocommerce_enable_delayed_account_creation', '__return_false' );
		add_filter( 'render_block_woocommerce/order-confirmation-summary', array( __CLASS__, 'omit_internal_contact_html' ) );
		add_action( 'woocommerce_before_template_part', array( __CLASS__, 'before_contact_template' ), PHP_INT_MAX, 4 );
		add_action( 'woocommerce_after_template_part', array( __CLASS__, 'after_contact_template' ), PHP_INT_MIN, 4 );
		add_filter( 'wp_speculation_rules_href_exclude_paths', array( __CLASS__, 'commerce_speculation_exclusions' ) );
		add_filter( 'render_block_data', static function ( $block ) {
			if ( 'woocommerce/checkout-shipping-method-block' === ( $block['blockName'] ?? '' ) ) {
				$block['attrs']['shippingText'] = 'Доставка';
				$block['attrs']['localPickupText'] = 'Самовывоз';
				$block['attrs']['title'] = 'Способ получения';
			}
			return $block;
		} );
	}

	/** Dynamic documents must fetch the current version; versioned assets stay cached. */
	public static function dynamic_page_headers( array $headers ): array {
		if ( 'staging' === wp_get_environment_type() && ( is_front_page() || is_checkout() || is_cart() ) ) {
			$headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private';
			$headers['Expires'] = 'Wed, 11 Jan 1984 05:00:00 GMT';
		}
		return $headers;
	}

	public static function clear_completed_note( $response, $handler, $request ) {
		if ( 'POST' !== $request->get_method() || ! preg_match( '#^/wc/store/v[0-9]+/checkout$#', $request->get_route() ) || is_wp_error( $response ) || ! $response instanceof WP_REST_Response ) { return $response; }
		$data = $response->get_data();
		if ( is_array( $data ) && $response->get_status() >= 200 && $response->get_status() < 300 && ! empty( $data['order_id'] ) && 'success' === ( $data['payment_result']['payment_status'] ?? '' ) && WC()->session ) {
			WC()->session->__unset( 'store_api_customer_note' );
			WC()->session->save_data();
		}
		return $response;
	}

	public static function canonical_staging_host_target( string $host, string $uri, string $method ): string {
		if ( 'staging' !== wp_get_environment_type() || ! in_array( $method, array( 'GET', 'HEAD' ), true ) ) { return ''; }
		$home = home_url( '/' );
		$canonical = wp_parse_url( $home, PHP_URL_HOST );
		if ( ! $canonical || strtolower( $host ) !== strtolower( $canonical ) . '.' ) { return ''; }
		return rtrim( $home, '/' ) . '/' . ltrim( $uri, '/' );
	}

	public static function canonical_staging_host(): void {
		$target = self::canonical_staging_host_target( (string) ( $_SERVER['HTTP_HOST'] ?? '' ), (string) ( $_SERVER['REQUEST_URI'] ?? '/' ), (string) ( $_SERVER['REQUEST_METHOD'] ?? '' ) );
		if ( '' !== $target ) {
			wp_safe_redirect( $target, 301, 'RollsBar canonical staging host' );
			exit;
		}
	}

	/** Stateful native Woo documents must load only on actual activation. */
	public static function receipt_payment_settings( $settings ): array {
		$settings = is_array( $settings ) ? $settings : array();
		$settings['title'] = 'Наличными или картой при получении';
		$settings['description'] = 'Оплатите заказ наличными или картой при получении.';
		$settings['instructions'] = $settings['description'];
		return $settings;
	}

	public static function receipt_payment_title( $title, $order ): string {
		return 'cod' === $order->get_payment_method() ? 'Наличными или картой при получении' : (string) $title;
	}

	/** Presentation only: keep native order shipping, tax address and historical metadata. */
	public static function pickup_order_display( $display, $order ): string {
		$methods = $order->get_shipping_methods();
		if ( 1 !== count( $methods ) ) { return (string) $display; }
		$method = reset( $methods );
		if ( 'pickup_location' !== $method->get_method_id() || (float) $method->get_total() > 0 ) { return (string) $display; }
		$address = (string) ( $method->get_meta( 'pickup_location' ) ?: $method->get_meta( 'pickup_address' ) );
		return 'Самовывоз' . ( $address ? ': ' . esc_html( $address ) : '' );
	}

	/** Stateful native Woo documents must load only on actual activation. */
	public static function commerce_speculation_exclusions( array $paths ): array {
		foreach ( array( wc_get_cart_url(), wc_get_checkout_url() ) as $url ) {
			$path = (string) wp_parse_url( $url, PHP_URL_PATH );
			if ( '' !== $path && '/' !== $path ) {
				$paths[] = rtrim( $path, '/' );
				$paths[] = rtrim( $path, '/' ) . '/*';
			}
		}
		$product = get_post_type_object( 'product' );
		if ( $product && is_array( $product->rewrite ) && ! empty( $product->rewrite['slug'] ) ) {
			$slug = preg_replace( '/%[^%]+%/', '*', trim( $product->rewrite['slug'], '/' ) );
			$paths[] = '/' . $slug . '/*';
		}
		return array_values( array_unique( $paths ) );
	}

	/** Presentation only, after native order access checks; never filter order data. */
	public static function omit_internal_contact_html( string $html ): string {
		return preg_replace_callback( '#<(li|p)\b[^>]*>.*?</\1>#is', static function ( $match ) {
			return false !== stripos( $match[0], '@checkout.rollsbar.invalid' ) ? '' : $match[0];
		}, $html );
	}

	/** Classic order-details presentation can also follow a native Block checkout. */
	public static function before_contact_template( $name, $path, $located, $args ): void {
		if ( 'order/order-details-customer.php' !== $name || empty( $args['order'] ) || ! $args['order'] instanceof WC_Order || false === stripos( $args['order']->get_billing_email(), '@checkout.rollsbar.invalid' ) ) {
			return;
		}
		self::$contact_template_buffers[] = ob_get_level();
		ob_start();
	}

	public static function after_contact_template( $name, $path, $located, $args ): void {
		if ( 'order/order-details-customer.php' !== $name || ! self::$contact_template_buffers || ob_get_level() !== end( self::$contact_template_buffers ) + 1 ) {
			return;
		}
		array_pop( self::$contact_template_buffers );
		echo self::omit_internal_contact_html( ob_get_clean() ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- native rendered template, contact row removed only.
	}

	/** Supported Woo phone validator; keep requiredness in the native fields. */
	public static function validate_phone( bool $valid, $phone, $country = null ): bool {
		unset( $country );
		$digits = preg_replace( '/\D/', '', (string) $phone );
		// Requiredness stays with Woo. A prefix is not a complete contact number.
		return $valid && ( '' === trim( (string) $phone ) || ( strlen( $digits ) >= 10 && strlen( $digits ) <= 15 ) );
	}

	/** Same contract is consumed by Blocks countryData and Store API validation. */
	public static function field_locale( array $locale ): array {
		foreach ( array( 'last_name', 'company', 'address_2', 'state', 'postcode' ) as $key ) {
			$locale['RU'][ $key ] = array( 'required' => false, 'hidden' => true );
		}
		$locale['RU']['first_name'] = array( 'label' => 'Имя', 'optionalLabel' => 'Имя', 'required' => false, 'hidden' => false );
		$locale['RU']['phone'] = array( 'label' => 'Телефон', 'required' => true, 'hidden' => false, 'index' => 20 );
		// Callback requests accept missing/unresolved customer addresses in either mode.
		// Delivery information is advisory; native Woo remains the submission authority.
		$locale['RU']['address_1'] = array( 'label' => 'Город, улица и дом', 'optionalLabel' => 'Город, улица и дом', 'required' => false, 'hidden' => false );
		$locale['RU']['city'] = array( 'required' => false, 'hidden' => true );
		// Woo 11.1.2 keeps country as the required locale lookup key. Its preset
		// RU control remains native; presentation omits it from the customer UI.
		$locale['RU']['country'] = array( 'required' => true, 'hidden' => false );
		return $locale;
	}

	/** Reserved, non-deliverable compatibility identity; never a customer contact. */
	public static function internal_email(): string {
		if ( ! WC()->session ) {
			wc_load_cart();
		}
		$id = WC()->session ? WC()->session->get_customer_id() : '';
		if ( '' === (string) $id ) {
			throw new RuntimeException( 'Native Woo session is required for checkout compatibility identity.' );
		}
		return 'guest-' . substr( hash_hmac( 'sha256', (string) $id, wp_salt( 'auth' ) ), 0, 32 ) . '@checkout.rollsbar.invalid';
	}

	public static function prepare_native_customer(): void {
		if ( ! is_checkout() || is_order_received_page() || ! WC()->customer ) {
			return;
		}
		$purpose = strtolower( (string) ( $_SERVER['HTTP_SEC_PURPOSE'] ?? $_SERVER['HTTP_PURPOSE'] ?? '' ) );
		if ( false !== strpos( $purpose, 'prefetch' ) || false !== strpos( $purpose, 'prerender' ) ) {
			return;
		}
		WC()->customer->set_billing_country( 'RU' );
		WC()->customer->set_shipping_country( 'RU' );
		if ( ! is_user_logged_in() ) {
			WC()->customer->set_billing_email( self::internal_email() );
		}
		WC()->customer->save();
	}

	/** Runs before REST schema validation; keeps the native endpoint and payload. */
	public static function prepare_store_request( $result, $server, $request ) {
		unset( $server );
		if ( ! in_array( $request->get_method(), array( 'POST', 'PUT' ), true ) || ! preg_match( '#^/wc/store/v[0-9]+/(checkout|cart/update-customer)$#', $request->get_route() ) ) {
			return $result;
		}
		$billing = (array) $request->get_param( 'billing_address' );
		$billing['country'] = 'RU';
		if ( ! is_user_logged_in() ) {
			$billing['email'] = self::internal_email();
			$request->set_param( 'create_account', false );
		}
		$request->set_param( 'billing_address', $billing );
		$shipping = (array) $request->get_param( 'shipping_address' );
		$shipping['country'] = 'RU';
		$request->set_param( 'shipping_address', $shipping );
		return $result;
	}

	/** Populate the public registry before core's priority-10 add (duplicates are ignored).
	 * Woo 11.1.2 requires the contact block; hiding its native field configuration
	 * avoids a second input/lifecycle while preserving the seeded billing email.
	 */
	public static function native_field_data(): void {
		$container = \Automattic\WooCommerce\Blocks\Package::container();
		$fields = $container->get( \Automattic\WooCommerce\Blocks\Domain\Services\CheckoutFields::class );
		$data = array_merge( $fields->get_core_fields(), $fields->get_additional_fields() );
		foreach ( self::field_locale( array() )['RU'] as $key => $config ) {
			$data[ $key ] = array_merge( $data[ $key ] ?? array(), $config );
		}
		foreach ( array( 'entrance', 'door-code', 'floor', 'apartment-office' ) as $key ) {
			$id = self::FIELD_PREFIX . $key;
			if ( isset( $data[ $id ] ) ) { $data[ $id ]['optionalLabel'] = $data[ $id ]['label']; }
		}
		$data['email']['hidden'] = true;
		$container->get( \Automattic\WooCommerce\Blocks\Assets\AssetDataRegistry::class )->add( 'defaultFields', $data );
	}

	public static function pickup_locations( $locations ) {
		if ( is_array( $locations ) && isset( $locations[0] ) ) {
			$locations[0]['name'] = 'Симферополь, Кечкеметская улица, 1';
		}
		return $locations;
	}

	/** Fail closed for all mail transports using wp_mail, including delayed emails. */
	public static function block_internal_mail( $result, array $attributes ) {
		$destinations = implode( ',', (array) ( $attributes['to'] ?? array() ) ) . ',' . implode( ',', (array) ( $attributes['headers'] ?? array() ) );
		return false !== stripos( $destinations, '@checkout.rollsbar.invalid' ) ? false : $result;
	}

	/** Woo admin emails use the billing email as Reply-To; it is not a contact. */
	public static function remove_internal_reply_headers( array $attributes ): array {
		$headers = $attributes['headers'] ?? array();
		$lines = is_array( $headers ) ? $headers : explode( "\n", $headers );
		$lines = array_values( array_filter( $lines, static function ( $line ) {
			return false === stripos( $line, '@checkout.rollsbar.invalid' );
		} ) );
		$attributes['headers'] = is_array( $headers ) ? $lines : implode( "\n", $lines );
		if ( isset( $attributes['message'] ) ) {
			$attributes['message'] = preg_replace( '/guest-[a-f0-9]{32}@checkout\.rollsbar\.invalid/i', 'Email не предоставлен', $attributes['message'] );
		}
		return $attributes;
	}

	public static function register_additional_fields(): void {
		if ( ! function_exists( 'woocommerce_register_additional_checkout_field' ) ) {
			return;
		}

		$fields = array(
			'entrance' => array(
				'label'    => 'Подъезд',
				'required' => false,
			),
			'door-code' => array(
				'label'    => 'Домофон',
				'required' => false,
			),
			'floor' => array(
				'label'    => 'Этаж',
				'required' => false,
			),
			'apartment-office' => array(
				'label'    => 'Квартира / офис',
				'required' => false,
			),
		);

		foreach ( $fields as $id => $config ) {
			woocommerce_register_additional_checkout_field(
				array(
					'id'         => self::FIELD_PREFIX . $id,
					'label'      => $config['label'],
					'location'   => 'order',
					'type'       => 'text',
					'required'   => $config['required'],
					'attributes' => array(
						'autocomplete' => 'off',
					),
				)
			);
		}

		// Owner-approved callback request: phone plus explicit consent are required.
		// Never precheck or fabricate consent. Name/address remain optional.
		woocommerce_register_additional_checkout_field(
			array(
				'id'            => self::FIELD_PREFIX . 'privacy-consent',
				'label'         => 'Я ознакомлен(а) с Политикой обработки персональных данных и даю согласие на обработку персональных данных для оформления и исполнения заказа.',
				'location'      => 'order',
				'type'          => 'checkbox',
				'required'      => true,
				'error_message' => 'Подтвердите согласие на обработку персональных данных для оформления заказа.',
			)
		);
	}

	public static function enqueue_checkout_assets(): void {
		if ( function_exists( 'is_front_page' ) && is_front_page() ) {
			wp_register_script( 'rollsbar-checkout-return', false, array(), ROLLSBAR_CORE_VERSION, true );
			wp_enqueue_script( 'rollsbar-checkout-return' );
			wp_add_inline_script( 'rollsbar-checkout-return', self::return_ui_script() );
		}
		if ( ! function_exists( 'is_checkout' ) || ! is_checkout() ) {
			return;
		}

		wp_enqueue_style(
			'rollsbar-checkout',
			plugins_url( 'assets/css/checkout.css', ROLLSBAR_CORE_FILE ),
			array(),
			RollsBar_Asset_Version::for_file( dirname( __DIR__ ) . '/assets/css/checkout.css', ROLLSBAR_CORE_VERSION )
		);

		wp_enqueue_script(
			'rollsbar-checkout',
			plugins_url( 'assets/js/checkout.js', ROLLSBAR_CORE_FILE ),
			array(),
			RollsBar_Asset_Version::for_file( dirname( __DIR__ ) . '/assets/js/checkout.js', ROLLSBAR_CORE_VERSION ),
			true
		);

		$address_suggestions_enabled = 'staging' === wp_get_environment_type()
			&& defined( 'ROLLSBAR_DADATA_API_KEY' )
			&& '' !== trim( (string) ROLLSBAR_DADATA_API_KEY );

		wp_add_inline_script(
			'rollsbar-checkout',
			'window.rollsBarCheckoutConfig=' . wp_json_encode(
				array(
					'phonePrefix'        => '+7 ',
					'deliverySelection'  => self::delivery_selection(),
					'internalEmail'      => is_user_logged_in() ? '' : self::internal_email(),
					'mapUrl'             => 'staging' === wp_get_environment_type() ? add_query_arg( 'ver', RollsBar_Asset_Version::for_file( dirname( __DIR__ ) . '/assets/delivery-map.html', ROLLSBAR_CORE_VERSION ), plugins_url( 'assets/delivery-map.html', ROLLSBAR_CORE_FILE ) ) : '',
					'addressSuggestions' => array(
						'enabled'      => $address_suggestions_enabled,
						'suggestUrl'   => rest_url( 'rollsbar/v1/address-suggestions' ),
						'resolveUrl'   => rest_url( 'rollsbar/v1/address-resolve' ),
						'minChars'     => 3,
						'debounceMs'   => 300,
						'attribution'  => 'DaData',
					),
				),
				JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
			) . ';',
			'before'
		);
	}

	/** Restore only verified selection metadata; the native customer owns address storage. */
	private static function delivery_selection() {
		if ( ! WC()->session || ! WC()->customer ) { return null; }
		$proof = (string) WC()->session->get( 'rollsbar_delivery_address_proof', '' );
		$address = WC()->customer->get_shipping_address_1();
		$decision = RollsBar_Delivery_Minimum::verify( $proof, $address, 1000000000 );
		if ( null === $decision['minimum'] ) { return null; }
		$data = json_decode( (string) base64_decode( explode( '.', $proof )[0], true ), true )['data'];
		return array( 'display' => $address, 'delivery' => $decision, 'address_proof' => $proof, 'qc_geo' => $data['qc_geo'] ?? null, 'lat' => $data['geo_lat'] ?? null, 'lon' => $data['geo_lon'] ?? null, 'precision' => RollsBar_Geocode_Policy::evaluate( $data['qc_geo'] ?? null ) );
	}

	public static function native_checkout_scripts(): void {
		if ( is_checkout() && ! is_order_received_page() && has_block( 'woocommerce/checkout', wc_get_page_id( 'checkout' ) ) ) {
			// Woo's block render schedules this dequeue after the theme has already
			// printed its head. Do it at enqueue time for the designated native page.
			wp_dequeue_script( 'wc-checkout' );
		}
	}

	/** The active checkout has no reason to speculate on the separate cart page. */
	public static function checkout_resource_hints( array $urls, string $relation ): array {
		if ( is_checkout() && ! is_order_received_page() && in_array( $relation, array( 'prefetch', 'prerender' ), true ) ) { return array(); }
		return $urls;
	}

	/** Presentation state only: preserve the menu position when the modal closes. */
	public static function return_ui_script(): string {
		return <<<'JS'
(function(){
 'use strict';
 var key='rollsbar_checkout_return_scroll';
 window.addEventListener('pageshow',function(event){if(event.persisted){try{sessionStorage.setItem('rollsbar_refresh_scroll',String(scrollY));}catch(error){}location.reload();}});
 document.addEventListener('click',function(event){
  var link=event.target.closest('.rollsbar-drawer-checkout');
  if(!link||event.defaultPrevented||link.getAttribute('aria-disabled')==='true')return;
  try{sessionStorage.setItem(key,String(scrollY));}catch(error){}
 });
 function restore(){
  var previous,refreshed;
  try{refreshed=sessionStorage.getItem('rollsbar_refresh_scroll');sessionStorage.removeItem('rollsbar_refresh_scroll');previous=refreshed===null?sessionStorage.getItem(key):refreshed;sessionStorage.removeItem(key);}catch(error){return;}
  if(previous===null||!/^\d+(\.\d+)?$/.test(previous))return;
  var from;
  if(refreshed===null){try{from=new URL(document.referrer);}catch(error){return;}
   if(from.origin!==location.origin||from.pathname!=='/checkout/')return;}
  // Initial cart/header sizing must not anchor the restored menu 22px away.
  // End the guard as soon as native cart initialization settles, or on user input.
  var root=document.documentElement,anchor=root.style.overflowAnchor,observer;
  var events=['pointerdown','wheel','touchstart','keydown'],released=false;
  function release(){
   if(released)return;released=true;
   root.style.overflowAnchor=anchor;
   if(observer)observer.disconnect();
   events.forEach(function(type){document.removeEventListener(type,release,true);});
  }
  root.style.overflowAnchor='none';
  scrollTo({top:Number(previous),behavior:'instant'});
  events.forEach(function(type){document.addEventListener(type,release,{capture:true,once:true});});
  function ready(){
   var card=document.querySelector('.rollsbar-product-card');
   if(card&&card.getAttribute('aria-busy')==='false'){
    if(observer)observer.disconnect();
    requestAnimationFrame(function(){requestAnimationFrame(release);});
   }
  }
  observer=new MutationObserver(ready);
  observer.observe(document.body,{subtree:true,attributes:true,attributeFilter:['aria-busy']});
  ready();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',restore,{once:true});else restore();
})();
JS;
	}
}

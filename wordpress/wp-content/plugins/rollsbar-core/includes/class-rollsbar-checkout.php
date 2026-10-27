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

	public static function init(): void {
		add_action( 'woocommerce_init', array( __CLASS__, 'register_additional_fields' ) );
		add_action( 'wp_enqueue_scripts', array( __CLASS__, 'enqueue_checkout_assets' ) );
		add_filter( 'woocommerce_get_country_locale', array( __CLASS__, 'field_locale' ) );
		add_action( 'template_redirect', array( __CLASS__, 'prepare_native_customer' ) );
		add_filter( 'rest_pre_dispatch', array( __CLASS__, 'prepare_store_request' ), 10, 3 );
		add_action( 'woocommerce_blocks_checkout_enqueue_data', array( __CLASS__, 'native_field_data' ), 5 );
		add_filter( 'option_pickup_location_pickup_locations', array( __CLASS__, 'pickup_locations' ) );
		add_filter( 'pre_wp_mail', array( __CLASS__, 'block_internal_mail' ), PHP_INT_MAX, 2 );
		add_filter( 'wp_mail', array( __CLASS__, 'remove_internal_reply_headers' ), PHP_INT_MAX );
		add_filter( 'woocommerce_checkout_registration_enabled', '__return_false' );
		add_filter( 'woocommerce_checkout_registration_required', '__return_false' );
	}

	/** Same contract is consumed by Blocks countryData and Store API validation. */
	public static function field_locale( array $locale ): array {
		foreach ( array( 'last_name', 'company', 'address_2', 'state', 'postcode' ) as $key ) {
			$locale['RU'][ $key ] = array( 'required' => false, 'hidden' => true );
		}
		$locale['RU']['first_name'] = array( 'label' => 'Имя', 'required' => true, 'hidden' => false );
		$locale['RU']['phone'] = array( 'label' => 'Телефон', 'required' => true, 'hidden' => false, 'index' => 20 );
		$locale['RU']['address_1'] = array( 'label' => 'Адрес', 'required' => true, 'hidden' => false );
		$locale['RU']['city'] = array( 'label' => 'Населённый пункт', 'optionalLabel' => 'Населённый пункт (необязательно)', 'required' => false, 'hidden' => false );
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
		$data['city']['optionalLabel'] = 'Населённый пункт (необязательно)';
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

		// The approved legal baseline requires personal-data consent to be a
		// separate explicit action, not bundled into acceptance of the offer.
		// WooCommerce's Additional Checkout Fields API enforces a required
		// checkbox in Checkout Block / Store API as part of order validation.
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
					'internalEmail'      => is_user_logged_in() ? '' : self::internal_email(),
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

	/** Presentation state only: preserve the menu position when the modal closes. */
	public static function return_ui_script(): string {
		return <<<'JS'
(function(){
 'use strict';
 var key='rollsbar_checkout_return_scroll';
 document.addEventListener('click',function(event){
  var link=event.target.closest('.rollsbar-drawer-checkout');
  if(!link||event.defaultPrevented||link.getAttribute('aria-disabled')==='true')return;
  try{sessionStorage.setItem(key,String(scrollY));}catch(error){}
 });
 function restore(){
  var previous;
  try{previous=sessionStorage.getItem(key);sessionStorage.removeItem(key);}catch(error){return;}
  if(previous===null||!/^\d+(\.\d+)?$/.test(previous))return;
  var from;
  try{from=new URL(document.referrer);}catch(error){return;}
  if(from.origin!==location.origin||from.pathname!=='/checkout/')return;
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

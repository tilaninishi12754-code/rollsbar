<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

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
	}

	public static function register_additional_fields(): void {
		if ( ! function_exists( 'woocommerce_register_additional_checkout_field' ) ) {
			return;
		}

		$fields = array(
			'entrance' => array(
				'label'    => 'Подъезд',
				'required' => RollsBar_Settings::get_bool( 'checkout_entrance_required' ),
			),
			'door-code' => array(
				'label'    => 'Код двери / домофона',
				'required' => RollsBar_Settings::get_bool( 'checkout_door_code_required' ),
			),
			'floor' => array(
				'label'    => 'Этаж',
				'required' => RollsBar_Settings::get_bool( 'checkout_floor_required' ),
			),
			'apartment-office' => array(
				'label'    => 'Квартира / офис',
				'required' => RollsBar_Settings::get_bool( 'checkout_apartment_required' ),
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
	}

	public static function enqueue_checkout_assets(): void {
		if ( ! function_exists( 'is_checkout' ) || ! is_checkout() ) {
			return;
		}

		wp_enqueue_style(
			'rollsbar-checkout',
			plugins_url( 'assets/css/checkout.css', ROLLSBAR_CORE_FILE ),
			array(),
			ROLLSBAR_CORE_VERSION
		);

		wp_enqueue_script(
			'rollsbar-checkout',
			plugins_url( 'assets/js/checkout.js', ROLLSBAR_CORE_FILE ),
			array(),
			ROLLSBAR_CORE_VERSION,
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
}

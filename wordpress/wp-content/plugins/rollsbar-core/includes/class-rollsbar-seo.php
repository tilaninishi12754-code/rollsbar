<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * SEO responsibilities owned by Rolls Bar Core:
 * - project-specific transactional noindex rules;
 * - one minimal Restaurant entity sourced from canonical Rolls Bar settings.
 *
 * Titles, descriptions, canonicals, Open Graph and XML sitemaps belong to the
 * selected SEO plugin/layer on staging. WooCommerce remains the Product schema owner.
 */
final class RollsBar_SEO {

	public static function init(): void {
		add_filter( 'wp_robots', array( __CLASS__, 'filter_robots' ) );
		add_action( 'wp_head', array( __CLASS__, 'output_restaurant_schema' ), 30 );
	}

	public static function filter_robots( array $robots ): array {
		$is_transactional = false;

		if ( function_exists( 'is_cart' ) && is_cart() ) {
			$is_transactional = true;
		}

		if ( function_exists( 'is_checkout' ) && is_checkout() ) {
			$is_transactional = true;
		}

		if ( function_exists( 'is_account_page' ) && is_account_page() ) {
			$is_transactional = true;
		}

		if ( is_search() ) {
			$is_transactional = true;
		}

		if ( $is_transactional ) {
			$robots['noindex'] = true;
			$robots['follow']  = true;
			unset( $robots['index'] );
		}

		return $robots;
	}

	public static function output_restaurant_schema(): void {
		if ( ! is_front_page() ) {
			return;
		}

		/**
		 * Set this filter to false if another SEO/schema owner takes responsibility
		 * for the Restaurant/LocalBusiness entity.
		 */
		if ( ! apply_filters( 'rollsbar_output_restaurant_schema', true ) ) {
			return;
		}

		$phone    = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'phone_href', '+79786882288' ) : '+79786882288';
		$city     = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'city', 'Симферополь' ) : 'Симферополь';
		$address  = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'address', 'Кечкеметская улица, 1' ) : 'Кечкеметская улица, 1';
		$telegram = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'telegram_url', '' ) : '';
		$vk       = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'vk_url', '' ) : '';

		$schema = array(
			'@context'  => 'https://schema.org',
			'@type'     => 'Restaurant',
			'@id'       => trailingslashit( home_url( '/' ) ) . '#restaurant',
			'name'      => 'Rolls Bar',
			'url'       => home_url( '/' ),
			'telephone' => $phone,
			'menu'      => home_url( '/' ),
			'address'   => array(
				'@type'           => 'PostalAddress',
				'streetAddress'   => $address,
				'addressLocality' => $city,
			),
		);

		$logo_id = (int) get_theme_mod( 'custom_logo' );
		if ( $logo_id ) {
			$logo = wp_get_attachment_image_url( $logo_id, 'full' );
			if ( $logo ) {
				$schema['logo']  = $logo;
				$schema['image'] = $logo;
			}
		}

		$same_as = array_values(
			array_filter(
				array(
					esc_url_raw( $telegram ),
					esc_url_raw( $vk ),
				)
			)
		);

		if ( $same_as ) {
			$schema['sameAs'] = $same_as;
		}

		echo "\n<script type=\"application/ld+json\" class=\"rollsbar-schema-restaurant\">";
		echo wp_json_encode(
			$schema,
			JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP
		); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
		echo "</script>\n";
	}
}

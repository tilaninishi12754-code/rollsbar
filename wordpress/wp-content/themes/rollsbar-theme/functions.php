<?php
/**
 * Rolls Bar theme bootstrap.
 *
 * Presentation only. Store/business rules belong in rollsbar-core.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_action(
	'after_setup_theme',
	static function () {
		add_theme_support( 'title-tag' );
		add_theme_support( 'post-thumbnails' );
		add_theme_support( 'woocommerce' );
		add_theme_support( 'wc-product-gallery-zoom' );
		add_theme_support( 'wc-product-gallery-lightbox' );
		add_theme_support( 'wc-product-gallery-slider' );
	}
);

add_action(
	'wp_enqueue_scripts',
	static function () {
		$version = wp_get_theme()->get( 'Version' );
		wp_enqueue_style(
			'rollsbar-theme',
			get_stylesheet_uri(),
			array(),
			$version
		);
	}
);

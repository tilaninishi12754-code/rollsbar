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
		add_theme_support( 'custom-logo' );
		add_theme_support( 'woocommerce' );
		add_theme_support( 'wc-product-gallery-zoom' );
		add_theme_support( 'wc-product-gallery-lightbox' );
		add_theme_support( 'wc-product-gallery-slider' );

		register_nav_menus(
			array(
				'primary' => 'Основное меню',
				'footer'  => 'Меню в подвале',
			)
		);
	}
);

add_action(
	'wp_enqueue_scripts',
	static function () {
		$theme   = wp_get_theme();
		$version = $theme->get( 'Version' );

		wp_enqueue_style(
			'rollsbar-theme',
			get_stylesheet_uri(),
			array(),
			$version
		);

		wp_enqueue_style(
			'rollsbar-app',
			get_template_directory_uri() . '/assets/css/app.css',
			array( 'rollsbar-theme' ),
			$version
		);

		// The custom front page renders WooCommerce add-to-cart buttons itself,
		// so explicitly load Woo's native AJAX handler and fragment refresh there.
		// WooCommerce no longer guarantees cart fragments on every page by default.
		if ( class_exists( 'WooCommerce' ) && is_front_page() ) {
			wp_enqueue_script( 'wc-add-to-cart' );
			wp_enqueue_script( 'wc-cart-fragments' );
		}

		wp_enqueue_script(
			'rollsbar-app',
			get_template_directory_uri() . '/assets/js/app.js',
			array(),
			$version,
			true
		);
	}
);

function rollsbar_cart_count(): int {
	if ( ! function_exists( 'WC' ) || ! WC()->cart ) {
		return 0;
	}

	return (int) WC()->cart->get_cart_contents_count();
}

function rollsbar_cart_total(): string {
	if ( ! function_exists( 'WC' ) || ! WC()->cart ) {
		return wc_price( 0 );
	}

	return WC()->cart->get_cart_subtotal();
}

function rollsbar_cart_badge_markup(): string {
	$count = rollsbar_cart_count();

	return sprintf(
		'<span class="rollsbar-cart-count" aria-label="%1$d товаров">%1$d</span>',
		$count
	);
}

add_filter(
	'woocommerce_add_to_cart_fragments',
	static function ( array $fragments ): array {
		$fragments['.rollsbar-cart-count'] = rollsbar_cart_badge_markup();

		ob_start();
		?>
		<span class="rollsbar-mobile-cart__inner">
			<span>Корзина</span>
			<?php echo rollsbar_cart_badge_markup(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
		</span>
		<?php
		$fragments['.rollsbar-mobile-cart__inner'] = (string) ob_get_clean();

		return $fragments;
	}
);

function rollsbar_product_image_url( WC_Product $product ): string {
	$image_id = $product->get_image_id();

	if ( $image_id ) {
		$image = wp_get_attachment_image_url( $image_id, 'large' );
		if ( $image ) {
			return $image;
		}
	}

	$source = (string) $product->get_meta( '_rollsbar_source_image', true );

	return $source ? esc_url_raw( $source ) : wc_placeholder_img_src( 'large' );
}

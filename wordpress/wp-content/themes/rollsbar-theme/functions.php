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

		$legal_slugs = array(
			'pravovaya-informaciya',
			'rekvizity-prodavca',
			'publichnaya-oferta',
			'dostavka-i-oplata',
			'oplata-i-vozvrat',
			'politika-konfidencialnosti',
			'soglasie-na-obrabotku-personalnyh-dannyh',
			'cookies',
			'bezopasnost-onlajn-oplaty',
		);
		if ( is_page( $legal_slugs ) ) {
			wp_enqueue_style(
				'rollsbar-legal',
				get_template_directory_uri() . '/assets/css/legal.css',
				array( 'rollsbar-app' ),
				$version
			);
		}

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
		if ( class_exists( 'WC_AJAX' ) && is_front_page() ) {
			wp_localize_script( 'rollsbar-app', 'rollsbarCart', array(
				'url' => WC_AJAX::get_endpoint( 'rollsbar_cart' ),
				'nonce' => wp_create_nonce( 'rollsbar_cart' ),
			) );
		}
	}
);

/** Compact catalog price; Woo remains the source of active, tax-adjusted prices. */
function rollsbar_catalog_price_html( WC_Product $product ): string {
	if ( ! $product->is_type( 'variable' ) ) {
		return $product->get_price_html();
	}

	$minimum = $product->get_variation_price( 'min', true );
	if ( '' === $minimum || false === $minimum ) {
		return '';
	}

	return '<span class="rollsbar-price__from">от</span> ' . wc_price( $minimum );
}

function rollsbar_cart_count(): int {
	if ( ! function_exists( 'WC' ) || ! WC()->cart ) {
		return 0;
	}

	return (int) WC()->cart->get_cart_contents_count();
}

/** One read-only detail record per canonical source ID, shared by catalog and Hits. */
function rollsbar_product_detail_data( WC_Product $product ): array {
	$is_variable = $product->is_type( 'variable' );
	$description = trim( wp_strip_all_tags( $product->get_description() ?: $product->get_short_description() ) );
	$selection = rollsbar_product_selection_data( $product );

	return array(
		'name'        => $product->get_name(),
		'description' => $description ?: 'Описание в открытом меню не указано.',
		'media'       => rollsbar_product_image_markup( $product, array( 'loading' => 'eager' ) ),
		'price'       => wp_kses_post( rollsbar_catalog_price_html( $product ) ),
		'variable'    => $is_variable,
		'selection'   => $selection,
		'action_url'  => $selection['required'] ? $product->get_permalink() : $product->add_to_cart_url(),
		// Native Woo action identity only; never the key for detail lookup.
		'woo_id'      => $product->get_id(),
	);
}

/** Read-only selector contract. Woo owns variation identity, price and availability. */
function rollsbar_product_selection_data( WC_Product $product ): array {
	$raw_options = (string) $product->get_meta( '_rollsbar_options_json', true );
	$options = array();
	$decoded = '' !== $raw_options ? json_decode( $raw_options, true ) : array();
	$blocked = ! is_array( $decoded );
	foreach ( is_array( $decoded ) ? $decoded : array() as $group ) {
		if ( ! is_array( $group ) ) { $blocked = true; continue; }
		$choices = array_values( array_filter( is_array( $group['choices'] ?? null ) ? $group['choices'] : array(), static fn( $value ) => is_string( $value ) && '' !== trim( $value ) ) );
		$options[] = array(
			'label'   => is_string( $group['label'] ?? null ) ? $group['label'] : 'Опция',
			'choices' => $choices,
			'pending' => ! empty( $group['pending'] ) || ! $choices,
		);
	}
	$variations = array();
	if ( $product->is_type( 'variable' ) ) {
		foreach ( $product->get_available_variations( 'objects' ) as $variation ) {
			$attributes = $variation->get_attributes();
			// A wildcard row cannot specify a complete choice in this selector.
			$complete = $attributes && ! in_array( '', $attributes, true );
			$price = '' !== $variation->get_price() ? wc_price( wc_get_price_to_display( $variation ) ) : '';
			$variations[] = array(
				'id'         => $variation->get_id(),
				'attributes' => $attributes,
				'label'      => wp_strip_all_tags( wc_get_formatted_variation( $variation, true, count( $attributes ) > 1, false ) ),
				'price_html' => wp_kses_post( $price ),
				'price_label'=> html_entity_decode( wp_strip_all_tags( $price ), ENT_QUOTES, 'UTF-8' ),
				'available'  => $complete && '' !== $price && $variation->variation_is_active() && $variation->variation_is_visible() && $variation->is_purchasable() && $variation->is_in_stock(),
			);
		}
	}
	return array(
		'required'   => $product->is_type( 'variable' ) || '' !== $raw_options,
		'label'      => has_term( 'pizza', 'product_cat', $product->get_id() ) ? 'Размер' : ( 'Наггетсы' === $product->get_name() ? 'Количество' : 'Вариант' ),
		'variations' => $variations,
		'options'    => $options,
		'blocked'    => $blocked || ( '' !== $raw_options && ! $options ),
	);
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

/** Header presentation only: reuse Woo's existing subtotal and fragment refresh. */
function rollsbar_header_cart_total_markup(): string {
	return '<span class="rollsbar-header-cart-total">' . esc_html( wp_strip_all_tags( rollsbar_cart_total() ) ) . '</span>';
}

add_filter(
	'woocommerce_add_to_cart_fragments',
	static function ( array $fragments ): array {
		$fragments['.rollsbar-cart-count'] = rollsbar_cart_badge_markup();
		$fragments['.rollsbar-header-cart-total'] = rollsbar_header_cart_total_markup();

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

/**
 * Resolve the canonical presentation image without mutating product data.
 *
 * An explicitly configured Woo image remains the admin override. Products
 * imported from the approved catalog retain their original source URL in
 * _rollsbar_source_image. Products with neither use the approved branded
 * fallback instead of WooCommerce's generic placeholder.
 *
 * @return array{url:string,source:string,attachment_id:int,kind:string,position:string}
 */
function rollsbar_resolve_product_image( WC_Product $product, string $size = 'large' ): array {
	$image_id = (int) $product->get_image_id();

	if ( $image_id ) {
		$image = wp_get_attachment_image_url( $image_id, $size );
		if ( $image ) {
			return array(
				'url'           => (string) $image,
				'source'        => 'featured',
				'attachment_id' => $image_id,
				'kind'          => 'image',
				'position'      => '',
			);
		}
	}

	// Exact approved VK sprite slices whose source IDs survive in catalog.json.
	$approved_sprites = array(
		'tyahan-sea'     => '20%',
		'tyahan-chicken' => '40%',
	);
	$source_id        = (string) $product->get_meta( '_rollsbar_source_id', true );
	if ( isset( $approved_sprites[ $source_id ] ) ) {
		return array(
			'url'           => get_theme_file_uri( 'assets/images/vk-products-row1.webp' ),
			'source'        => 'approved-sprite',
			'attachment_id' => 0,
			'kind'          => 'sprite',
			'position'      => $approved_sprites[ $source_id ],
		);
	}

	$source = esc_url_raw( trim( (string) $product->get_meta( '_rollsbar_source_image', true ) ) );
	if ( $source ) {
		return array(
			'url'           => $source,
			'source'        => 'catalog',
			'attachment_id' => 0,
			'kind'          => 'image',
			'position'      => '',
		);
	}

	return array(
		'url'           => '',
		'source'        => 'fallback',
		'attachment_id' => 0,
		'kind'          => 'fallback',
		'position'      => '',
	);
}

function rollsbar_product_image_url( WC_Product $product, string $size = 'large' ): string {
	$image = rollsbar_resolve_product_image( $product, $size );

	return $image['url'];
}

/** Render the shared catalog/detail image or the exact approved fallback. */
function rollsbar_product_image_markup( WC_Product $product, array $attributes = array() ): string {
	$image = rollsbar_resolve_product_image( $product );
	$name  = $product->get_name();

	if ( 'sprite' === $image['kind'] ) {
		return sprintf(
			'<span class="rollsbar-product-sprite rollsbar-product-sprite--row1" style="background-position:%1$s 50%%" role="img" aria-label="%2$s" data-rollsbar-product-image-source="%3$s"></span>',
			esc_attr( $image['position'] ),
			esc_attr( $name ),
			esc_attr( $image['url'] . '#' . $image['position'] )
		);
	}

	if ( ! $image['url'] ) {
		return sprintf(
			'<span class="rollsbar-product-fallback" role="img" aria-label="%s">ROLLS BAR</span>',
			esc_attr( $name )
		);
	}

	$attributes = array_merge(
		array(
			'src'                         => $image['url'],
			'alt'                         => $name,
			'loading'                     => 'lazy',
			'decoding'                    => 'async',
			'referrerpolicy'              => 'no-referrer',
			'data-rollsbar-product-image' => '',
		),
		$attributes
	);

	$markup = array();
	foreach ( $attributes as $attribute => $value ) {
		$markup[] = sprintf( '%s="%s"', esc_attr( (string) $attribute ), esc_attr( (string) $value ) );
	}

	return '<img ' . implode( ' ', $markup ) . '>';
}

/** Use the same canonical image identity in WooCommerce's main product image. */
add_filter(
	'woocommerce_single_product_image_thumbnail_html',
	static function ( string $html, int $attachment_id ): string {
		if ( ! function_exists( 'is_product' ) || ! is_product() ) {
			return $html;
		}

		global $product;
		if ( ! $product instanceof WC_Product ) {
			return $html;
		}

		$main_image_id = (int) $product->get_image_id();
		if ( $attachment_id && $attachment_id !== $main_image_id ) {
			return $html;
		}

		$image  = rollsbar_resolve_product_image( $product );
		if ( 'featured' === $image['source'] ) {
			return $html;
		}

		$markup = rollsbar_product_image_markup(
			$product,
			array(
				'class'   => 'wp-post-image',
				'loading' => 'eager',
			)
		);

		if ( 'image' !== $image['kind'] ) {
			return '<div class="woocommerce-product-gallery__image--placeholder rollsbar-product-media rollsbar-product-detail-media">' . $markup . '</div>';
		}

		$full_image = $image['attachment_id']
			? wp_get_attachment_image_url( $image['attachment_id'], 'full' )
			: $image['url'];
		$full_image = $full_image ?: $image['url'];

		return sprintf(
			'<div data-thumb="%1$s" class="woocommerce-product-gallery__image rollsbar-product-media rollsbar-product-detail-media"><a href="%2$s">%3$s</a></div>',
			esc_url( $image['url'] ),
			esc_url( $full_image ),
			$markup
		);
	},
	20,
	2
);

<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class RollsBar_Product_Fields {

	public static function init(): void {
		add_action( 'woocommerce_product_options_general_product_data', array( __CLASS__, 'render_fields' ) );
		add_action( 'woocommerce_admin_process_product_object', array( __CLASS__, 'save_fields' ) );
		add_action( 'woocommerce_single_product_summary', array( __CLASS__, 'render_frontend_meta' ), 24 );
	}

	public static function render_fields(): void {
		echo '<div class="options_group">';
		echo '<p style="padding:0 12px 2px;"><strong>Rolls Bar — карточка товара</strong><br><span class="description">Размер карточки и дизайн фиксированы темой. Здесь меняется только содержимое.</span></p>';

		woocommerce_wp_textarea_input(
			array(
				'id'          => '_rollsbar_composition',
				'label'       => 'Состав / ингредиенты',
				'rows'        => 4,
				'desc_tip'    => true,
				'description' => 'Отдельное поле состава. Исходное описание товара сохраняется независимо и не затирается.',
			)
		);

		woocommerce_wp_text_input(
			array(
				'id'          => '_rollsbar_weight_display',
				'label'       => 'Вес / объём',
				'placeholder' => 'Например: 280 г',
				'desc_tip'    => true,
				'description' => 'Показываемое клиенту значение. Не обязательно совпадает с транспортным весом WooCommerce.',
			)
		);

		woocommerce_wp_text_input(
			array(
				'id'                => '_rollsbar_calories',
				'label'             => 'Калории, ккал',
				'type'              => 'number',
				'custom_attributes' => array( 'min' => '0', 'step' => '0.01' ),
			)
		);
		woocommerce_wp_text_input(
			array(
				'id'                => '_rollsbar_protein',
				'label'             => 'Белки, г',
				'type'              => 'number',
				'custom_attributes' => array( 'min' => '0', 'step' => '0.01' ),
			)
		);
		woocommerce_wp_text_input(
			array(
				'id'                => '_rollsbar_fat',
				'label'             => 'Жиры, г',
				'type'              => 'number',
				'custom_attributes' => array( 'min' => '0', 'step' => '0.01' ),
			)
		);
		woocommerce_wp_text_input(
			array(
				'id'                => '_rollsbar_carbs',
				'label'             => 'Углеводы, г',
				'type'              => 'number',
				'custom_attributes' => array( 'min' => '0', 'step' => '0.01' ),
			)
		);

		echo '<p class="form-field"><span class="description">КБЖУ полностью опциональны: если значения пустые, блок на сайте не выводится.</span></p>';
		echo '</div>';
	}

	public static function save_fields( WC_Product $product ): void {
		if ( isset( $_POST['_rollsbar_composition'] ) ) {
			$product->update_meta_data(
				'_rollsbar_composition',
				sanitize_textarea_field( wp_unslash( $_POST['_rollsbar_composition'] ) )
			);
		}

		$text_fields = array(
			'_rollsbar_weight_display',
			'_rollsbar_calories',
			'_rollsbar_protein',
			'_rollsbar_fat',
			'_rollsbar_carbs',
		);

		foreach ( $text_fields as $key ) {
			if ( isset( $_POST[ $key ] ) ) {
				$product->update_meta_data(
					$key,
					sanitize_text_field( wp_unslash( $_POST[ $key ] ) )
				);
			}
		}
	}

	public static function composition( WC_Product $product ): string {
		return trim( (string) $product->get_meta( '_rollsbar_composition', true ) );
	}

	public static function weight_display( WC_Product $product ): string {
		return trim( (string) $product->get_meta( '_rollsbar_weight_display', true ) );
	}

	public static function nutrition( WC_Product $product ): array {
		return array_filter(
			array(
				'Калории'   => trim( (string) $product->get_meta( '_rollsbar_calories', true ) ),
				'Белки'     => trim( (string) $product->get_meta( '_rollsbar_protein', true ) ),
				'Жиры'      => trim( (string) $product->get_meta( '_rollsbar_fat', true ) ),
				'Углеводы'  => trim( (string) $product->get_meta( '_rollsbar_carbs', true ) ),
			),
			static fn( string $value ): bool => '' !== $value
		);
	}

	public static function render_frontend_meta(): void {
		global $product;

		if ( ! $product instanceof WC_Product ) {
			return;
		}

		$composition = self::composition( $product );
		$weight      = self::weight_display( $product );
		$kbju        = self::nutrition( $product );

		if ( ! $composition && ! $weight && ! $kbju ) {
			return;
		}

		echo '<section class="rollsbar-product-facts" aria-label="Характеристики товара">';

		if ( $composition ) {
			echo '<div class="rollsbar-product-composition"><strong>Состав / ингредиенты:</strong><br>' . nl2br( esc_html( $composition ) ) . '</div>';
		}

		if ( $weight ) {
			echo '<p><strong>Вес / объём:</strong> ' . esc_html( $weight ) . '</p>';
		}

		if ( $kbju ) {
			echo '<dl class="rollsbar-kbju">';
			foreach ( $kbju as $label => $value ) {
				$suffix = 'Калории' === $label ? ' ккал' : ' г';
				echo '<div><dt>' . esc_html( $label ) . '</dt><dd>' . esc_html( $value . $suffix ) . '</dd></div>';
			}
			echo '</dl>';
		}

		echo '</section>';
	}
}

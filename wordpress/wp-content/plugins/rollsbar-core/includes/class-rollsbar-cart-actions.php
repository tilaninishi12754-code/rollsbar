<?php
/** Catalog actions backed exclusively by the customer's native Woo cart. */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class RollsBar_Cart_Actions {

	public static function init(): void {
		add_action( 'wc_ajax_rollsbar_cart', array( __CLASS__, 'ajax' ) );
		add_filter( 'woocommerce_get_item_data', array( __CLASS__, 'item_data' ), 10, 2 );
		add_action( 'woocommerce_checkout_create_order_line_item', array( __CLASS__, 'order_item' ), 10, 4 );
	}

	public static function snapshot(): array {
		$counts = array();
		$lines = array();
		foreach ( WC()->cart->get_cart() as $key => $item ) {
			$product = wc_get_product( $item['product_id'] );
			$id = $product ? (string) $product->get_meta( '_rollsbar_source_id', true ) : '';
			if ( '' !== $id ) { $counts[ $id ] = ( $counts[ $id ] ?? 0 ) + (int) $item['quantity']; }
			$actual = empty( $item['variation_id'] ) ? $product : wc_get_product( $item['variation_id'] );
			if ( ! $product || ! $actual ) { continue; }
			$labels = array();
			if ( $actual->is_type( 'variation' ) ) {
				$label = has_term( 'pizza', 'product_cat', $product->get_id() ) ? 'Размер' : ( 'Наггетсы' === $product->get_name() ? 'Количество' : 'Вариант' );
				$labels[] = $label . ': ' . wp_strip_all_tags( wc_get_formatted_variation( $actual, true, false, false ) );
			}
			foreach ( $item['rollsbar_options'] ?? array() as $option ) { $labels[] = $option['label'] . ': ' . $option['value']; }
			$lines[] = array(
				'key' => (string) $key,
				'source_id' => $id,
				'variation_id' => (int) ( $item['variation_id'] ?? 0 ),
				'name' => $product->get_name() . ( $labels ? ' · ' . implode( ', ', $labels ) : '' ),
				'quantity' => (int) $item['quantity'],
				'unit_price' => html_entity_decode( wp_strip_all_tags( WC()->cart->get_product_price( $actual ) ), ENT_QUOTES, 'UTF-8' ),
				'options' => $item['rollsbar_options'] ?? array(),
				'media' => function_exists( 'rollsbar_product_image_markup' ) ? rollsbar_product_image_markup( $product ) : $product->get_image(),
			);
		}
		$upsells = array();
		foreach ( RollsBar_Catalog_Importer::upsell_products() as $product ) {
			$upsells[] = array( 'source_id' => $product->get_meta( '_rollsbar_source_id', true ), 'product_id' => $product->get_id(), 'name' => $product->get_name(), 'price' => html_entity_decode( wp_strip_all_tags( WC()->cart->get_product_price( $product ) ), ENT_QUOTES, 'UTF-8' ), 'available' => $product->is_purchasable() && $product->is_in_stock() );
		}
		return array( 'counts' => (object) $counts, 'lines' => $lines, 'upsells' => $upsells, 'mode' => class_exists( 'RollsBar_Delivery_Checkout' ) ? RollsBar_Delivery_Checkout::mode() : WC()->session->get( 'rollsbar_cart_mode', 'delivery' ), 'subtotal' => html_entity_decode( wp_strip_all_tags( WC()->cart->get_cart_subtotal() ), ENT_QUOTES, 'UTF-8' ) );
	}

	/** Exact option whitelist; labels/price/availability from the browser are never trusted. */
	public static function options( WC_Product $product, array $selected ): array {
		$raw = (string) $product->get_meta( '_rollsbar_options_json', true );
		$groups = '' === $raw ? array() : json_decode( $raw, true );
		if ( ! is_array( $groups ) || ( '' !== $raw && ! $groups ) || count( $groups ) !== count( $selected ) ) {
			throw new Exception( 'Выберите доступные опции товара.' );
		}
		$result = array();
		foreach ( $groups as $index => $group ) {
			$value = $selected[ $index ] ?? null;
			if ( ! is_array( $group ) || ! empty( $group['pending'] ) || ! is_string( $value ) || ! is_array( $group['choices'] ?? null ) || ! in_array( $value, $group['choices'], true ) ) {
				throw new Exception( 'Выберите доступные опции товара.' );
			}
			$result[] = array( 'label' => $group['label'] ?? 'Опция', 'value' => $value );
		}
		return $result;
	}

	/** Shared mutation seam, also exercised by deterministic local PHP QA. */
	public static function mutate( array $request ): void {
		// Approved drawer's indicative receiving mode; native checkout still owns shipping/rates.
		if ( 'mode' === ( $request['operation'] ?? '' ) ) {
			if ( ! in_array( $request['mode'] ?? '', array( 'delivery', 'pickup' ), true ) ) { throw new Exception( 'Недопустимый способ получения.' ); }
			WC()->session->set( 'rollsbar_cart_mode', $request['mode'] );
			if ( class_exists( 'RollsBar_Delivery_Checkout' ) ) { RollsBar_Delivery_Checkout::choose_mode( $request['mode'] ); }
			return;
		}
		if ( in_array( $request['operation'] ?? '', array( 'line_plus', 'line_minus', 'line_remove' ), true ) ) {
			$key = is_string( $request['key'] ?? null ) ? $request['key'] : '';
			$items = WC()->cart->get_cart();
			if ( ! isset( $items[ $key ] ) ) { throw new Exception( 'Товар уже удалён из корзины.' ); }
			$item = $items[ $key ];
			// Catalog variation counters must still be unambiguous in the current server cart.
			if ( array_key_exists( 'source_id', $request ) ) {
				$parent = wc_get_product( $item['product_id'] );
				$matching = array_filter( $items, static function( $line ) use ( $item ) { return (int) $line['product_id'] === (int) $item['product_id']; } );
				if ( ! $parent || ! has_term( 'pizza', 'product_cat', $parent->get_id() ) || $parent->get_meta( '_rollsbar_source_id', true ) !== $request['source_id'] || count( $matching ) !== 1 || empty( $item['variation_id'] ) || ( $request['variation_id'] ?? null ) !== (int) $item['variation_id'] ) { throw new Exception( 'Выберите размер пиццы или измените товар в корзине.' ); }
			}
			$quantity = 'line_remove' === $request['operation'] ? 0 : max( 0, (int) $item['quantity'] + ( 'line_plus' === $request['operation'] ? 1 : -1 ) );
			if ( $quantity > $item['quantity'] ) {
				$actual = wc_get_product( $item['variation_id'] ?: $item['product_id'] );
				if ( ! $actual || ! $actual->is_purchasable() || ! $actual->is_in_stock() ) { throw new Exception( 'Товар недоступен.' ); }
				$quantities = WC()->cart->get_cart_item_quantities();
				$stock_id = $actual->get_stock_managed_by_id();
				if ( $actual->is_sold_individually() && $quantity > 1 ) { throw new Exception( 'Этот товар можно заказать только один раз.' ); }
				if ( ! $actual->has_enough_stock( ( $quantities[ $stock_id ] ?? 0 ) + 1 ) ) { throw new Exception( 'Недостаточно товара в наличии.' ); }
			}
			if ( ! apply_filters( 'woocommerce_update_cart_validation', true, $key, $item, $quantity ) || ! WC()->cart->set_quantity( $key, $quantity ) ) { throw new Exception( 'Не удалось изменить количество.' ); }
			return;
		}
		$product = wc_get_product( absint( $request['product_id'] ?? 0 ) );
		if ( ! $product || ! $product->is_type( array( 'simple', 'variable' ) ) || 'publish' !== $product->get_status() || '' === (string) $product->get_meta( '_rollsbar_source_id', true ) || $product->get_meta( '_rollsbar_source_id', true ) !== ( $request['source_id'] ?? '' ) ) {
			throw new Exception( 'Товар недоступен.' );
		}
		$operation = $request['operation'] ?? '';
		if ( ! in_array( $operation, array( 'add', 'minus' ), true ) ) { throw new Exception( 'Недопустимое действие.' ); }
		if ( 'minus' === $operation ) {
			// Only ordinary simple products expose card counters. Never decrement an arbitrary option line.
			if ( ! $product->is_type( 'simple' ) || '' !== (string) $product->get_meta( '_rollsbar_options_json', true ) ) { throw new Exception( 'Выберите товар в корзине.' ); }
			foreach ( WC()->cart->get_cart() as $key => $item ) {
				if ( (int) $item['product_id'] === $product->get_id() && empty( $item['variation_id'] ) && empty( $item['rollsbar_options'] ) ) {
					$quantity = max( 0, (int) $item['quantity'] - 1 );
					if ( ! apply_filters( 'woocommerce_update_cart_validation', true, $key, $item, $quantity ) || ! WC()->cart->set_quantity( $key, $quantity ) ) { throw new Exception( 'Не удалось изменить количество.' ); }
					return;
				}
			}
			return;
		}
		$options = self::options( $product, is_array( $request['options'] ?? null ) ? $request['options'] : array() );
		// JSON integer only: never truncate, abs(), or silently turn zero into one.
		$quantity = array_key_exists( 'quantity', $request ) ? $request['quantity'] : 1;
		if ( ! is_int( $quantity ) || $quantity < 1 ) { throw new Exception( 'Количество должно быть целым числом не меньше 1.' ); }
		$variation_id = absint( $request['variation_id'] ?? 0 );
		$attributes = array();
		if ( $product->is_type( 'variable' ) ) {
			$variation = wc_get_product( $variation_id );
			if ( ! $variation || ! $variation->is_type( 'variation' ) || $variation->get_parent_id() !== $product->get_id() || ! $variation->variation_is_active() || ! $variation->variation_is_visible() || ! $variation->is_purchasable() || ! $variation->is_in_stock() ) { throw new Exception( 'Нет доступных вариантов.' ); }
			$attributes = $variation->get_variation_attributes();
			if ( ! $attributes || in_array( '', $attributes, true ) ) { throw new Exception( 'Выберите доступный вариант.' ); }
		} elseif ( $variation_id ) { throw new Exception( 'Недопустимый вариант.' ); }
		$data = $options ? array( 'rollsbar_options' => $options ) : array();
		if ( ! apply_filters( 'woocommerce_add_to_cart_validation', true, $product->get_id(), $quantity, $variation_id, $attributes, $data ) || ! WC()->cart->add_to_cart( $product->get_id(), $quantity, $variation_id, $attributes, $data ) ) { throw new Exception( 'Не удалось добавить товар в корзину.' ); }
		do_action( 'woocommerce_ajax_added_to_cart', $product->get_id() );
	}

	public static function ajax(): void {
		check_ajax_referer( 'rollsbar_cart', 'nonce' );
		if ( ! WC()->cart ) { wc_load_cart(); }
		$request = json_decode( wp_unslash( $_POST['request'] ?? '{}' ), true );
		try {
			if ( ! is_array( $request ) ) { throw new Exception( 'Недопустимое действие.' ); }
			if ( 'read' !== ( $request['operation'] ?? '' ) ) { self::mutate( $request ); }
			WC()->cart->calculate_totals();
			$response = self::snapshot() + array( 'fragments' => apply_filters( 'woocommerce_add_to_cart_fragments', array() ), 'cart_hash' => WC()->cart->get_cart_hash() );
			// Persist before JSON can reach the next request; shutdown may flush output first.
			WC()->session->save_data();
			wp_send_json_success( $response );
		} catch ( Exception $error ) {
			$notices = wc_get_notices( 'error' );
			$message = $notices ? implode( ' ', array_column( $notices, 'notice' ) ) : $error->getMessage();
			wc_clear_notices();
			WC()->cart->calculate_totals();
			$response = self::snapshot() + array( 'message' => wp_strip_all_tags( $message ) );
			WC()->session->save_data();
			wp_send_json_error( $response );
		}
	}

	public static function item_data( array $data, array $item ): array {
		foreach ( $item['rollsbar_options'] ?? array() as $option ) { $data[] = array( 'key' => $option['label'], 'value' => $option['value'] ); }
		return $data;
	}

	public static function order_item( $item, $key, $values, $order ): void {
		foreach ( $values['rollsbar_options'] ?? array() as $option ) { $item->add_meta_data( $option['label'], $option['value'] ); }
	}
}

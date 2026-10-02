<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Operator-facing order helpers for Rolls Bar.
 *
 * WooCommerce's Additional Checkout Fields API remains the storage owner.
 * This class only reads those values through the official CheckoutFields
 * service and presents a compact Rolls Bar summary to staff.
 */
final class RollsBar_Order_Details {

	private const FIELD_LABELS = array(
		'rollsbar/entrance'         => 'Подъезд',
		'rollsbar/door-code'        => 'Код двери / домофона',
		'rollsbar/floor'            => 'Этаж',
		'rollsbar/apartment-office' => 'Квартира / офис',
	);

	public static function init(): void {
		add_action(
			'woocommerce_admin_order_data_after_shipping_address',
			array( __CLASS__, 'render_admin_delivery_details' ),
			30,
			1
		);

		// HPOS order screen.
		add_filter( 'manage_woocommerce_page_wc-orders_columns', array( __CLASS__, 'add_order_list_columns' ), 20 );
		add_action( 'manage_woocommerce_page_wc-orders_custom_column', array( __CLASS__, 'render_order_list_column' ), 20, 2 );

		// Legacy order storage fallback while the site is still in migration/staging.
		add_filter( 'manage_edit-shop_order_columns', array( __CLASS__, 'add_order_list_columns' ), 20 );
		add_action( 'manage_shop_order_posts_custom_column', array( __CLASS__, 'render_legacy_order_list_column' ), 20, 2 );
	}

	/**
	 * @return array<string,string>
	 */
	public static function additional_fields( WC_Order $order ): array {
		if (
			! class_exists( '\Automattic\WooCommerce\Blocks\Package' ) ||
			! class_exists( '\Automattic\WooCommerce\Blocks\Domain\Services\CheckoutFields' )
		) {
			return array();
		}

		try {
			$checkout_fields = \Automattic\WooCommerce\Blocks\Package::container()->get(
				\Automattic\WooCommerce\Blocks\Domain\Services\CheckoutFields::class
			);
		} catch ( Throwable $exception ) {
			return array();
		}

		$result = array();

		foreach ( self::FIELD_LABELS as $field_id => $label ) {
			$value = $checkout_fields->get_field_from_object( $field_id, $order, 'other' );
			$value = is_scalar( $value ) ? trim( (string) $value ) : '';

			if ( '' !== $value ) {
				$result[ $label ] = $value;
			}
		}

		return $result;
	}

	public static function fulfillment_label( WC_Order $order ): string {
		$shipping = trim( (string) $order->get_shipping_method() );

		return $shipping ?: 'Не определён';
	}

	public static function add_order_list_columns( array $columns ): array {
		$operator_columns = array(
			'rollsbar_customer' => 'Имя',
			'rollsbar_phone'    => 'Телефон',
			'rollsbar_address'  => 'Адрес',
			'rollsbar_zone'     => 'Зона доставки',
			'rollsbar_time'     => 'Время',
		);

		$result   = array();
		$inserted = false;

		foreach ( $columns as $key => $label ) {
			$result[ $key ] = 'order_number' === $key ? 'Заказ' : $label;

			if ( 'order_number' === $key ) {
				$result   = array_merge( $result, $operator_columns );
				$inserted = true;
			}
		}

		return $inserted ? $result : array_merge( $operator_columns, $result );
	}

	public static function render_order_list_column( string $column, $order ): void {
		$order = self::resolve_order( $order );

		if ( ! $order ) {
			return;
		}

		$value = '';

		switch ( $column ) {
			case 'rollsbar_customer':
				$value = self::customer_name( $order );
				break;
			case 'rollsbar_phone':
				$value = trim( (string) $order->get_billing_phone() );
				break;
			case 'rollsbar_address':
				$value = self::delivery_address( $order );
				break;
			case 'rollsbar_zone':
				$value = self::delivery_zone_label( $order );
				break;
			case 'rollsbar_time':
				$value = self::order_time( $order );
				break;
			default:
				return;
		}

		echo esc_html( $value ?: '—' );
	}

	public static function render_legacy_order_list_column( string $column, int $post_id ): void {
		self::render_order_list_column( $column, $post_id );
	}

	private static function resolve_order( $order ): ?WC_Order {
		if ( $order instanceof WC_Order ) {
			return $order;
		}

		$resolved = wc_get_order( absint( $order ) );
		return $resolved instanceof WC_Order ? $resolved : null;
	}

	private static function customer_name( WC_Order $order ): string {
		$name = trim( $order->get_billing_first_name() . ' ' . $order->get_billing_last_name() );

		if ( '' === $name ) {
			$name = trim( $order->get_shipping_first_name() . ' ' . $order->get_shipping_last_name() );
		}

		return $name;
	}

	private static function delivery_address( WC_Order $order ): string {
		$use_shipping = '' !== trim( (string) $order->get_shipping_address_1() );
		$address_1    = $use_shipping ? $order->get_shipping_address_1() : $order->get_billing_address_1();
		$address_2    = $use_shipping ? $order->get_shipping_address_2() : $order->get_billing_address_2();
		$fields       = self::additional_fields( $order );
		$apartment    = trim( (string) ( $fields['Квартира / офис'] ?? '' ) );

		$parts = array_filter(
			array(
				trim( (string) $address_1 ),
				trim( (string) $address_2 ),
				$apartment ? 'кв./офис ' . $apartment : '',
			)
		);

		return implode( ', ', array_unique( $parts ) );
	}

	private static function delivery_zone_label( WC_Order $order ): string {
		$zone = trim( (string) $order->get_meta( '_rollsbar_delivery_zone', true ) );

		if ( $zone ) {
			return $zone;
		}

		$fulfillment = self::fulfillment_label( $order );
		return false !== stripos( $fulfillment, 'самовывоз' ) ? 'Самовывоз' : '';
	}

	private static function order_time( WC_Order $order ): string {
		$date = $order->get_date_created();
		return $date ? wc_format_datetime( $date, 'H:i' ) : '';
	}

	public static function render_admin_delivery_details( WC_Order $order ): void {
		if ( ! $order instanceof WC_Order ) {
			return;
		}

		$fields = self::additional_fields( $order );
		$status = (string) $order->get_meta( '_rollsbar_telegram_status', true );

		echo '<div class="rollsbar-admin-order-summary" style="margin-top:14px;padding-top:12px;border-top:1px solid #ddd;">';
		echo '<p><strong>' . esc_html__( 'Rolls Bar — детали заказа', 'rollsbar-core' ) . '</strong></p>';
		echo '<p><strong>' . esc_html__( 'Получение:', 'rollsbar-core' ) . '</strong> ' . esc_html( self::fulfillment_label( $order ) ) . '</p>';

		if ( $fields ) {
			foreach ( $fields as $label => $value ) {
				echo '<p><strong>' . esc_html( $label ) . ':</strong> ' . esc_html( $value ) . '</p>';
			}
		} else {
			echo '<p style="color:#777;">' . esc_html__( 'Дополнительные адресные поля не заполнены.', 'rollsbar-core' ) . '</p>';
		}

		if ( $status ) {
			echo '<p><strong>' . esc_html__( 'Telegram:', 'rollsbar-core' ) . '</strong> ' . esc_html( self::telegram_status_label( $status ) ) . '</p>';
		}

		echo '</div>';
	}

	private static function telegram_status_label( string $status ): string {
		$labels = array(
			'queued'         => 'в очереди',
			'sent'           => 'отправлено',
			'failed'         => 'ошибка отправки',
			'not_configured' => 'не настроено',
		);

		return $labels[ $status ] ?? $status;
	}
}

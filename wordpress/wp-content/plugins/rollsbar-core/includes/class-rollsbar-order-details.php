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

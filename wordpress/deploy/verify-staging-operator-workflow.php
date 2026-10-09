<?php
/**
 * Self-cleaning runtime smoke for the Rolls Bar operator order workflow.
 *
 * Creates a temporary pending order without running checkout or actionable
 * status transitions, verifies operator-facing columns/details, then deletes
 * the order in finally. No email or Telegram delivery is triggered.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit( 1 );
}

if ( ! class_exists( 'WooCommerce' ) || ! class_exists( 'RollsBar_Order_Details' ) ) {
	fwrite( STDERR, "required runtime classes missing\n" );
	exit( 1 );
}

$admin = get_user_by( 'login', 'rollsbar_staging_admin' );
if ( ! $admin instanceof WP_User ) {
	fwrite( STDERR, "staging admin user missing\n" );
	exit( 1 );
}
wp_set_current_user( $admin->ID );

if ( ! current_user_can( 'manage_woocommerce' ) ) {
	fwrite( STDERR, "staging admin lacks manage_woocommerce\n" );
	exit( 1 );
}

// Belt-and-suspenders: this smoke never performs an actionable status change,
// but explicitly disable known Woo email channels and RollsBar status queueing.
add_filter( 'woocommerce_email_enabled_new_order', '__return_false', 999 );
add_filter( 'woocommerce_email_enabled_customer_on_hold_order', '__return_false', 999 );
add_filter( 'woocommerce_email_enabled_customer_processing_order', '__return_false', 999 );
remove_action(
	'woocommerce_order_status_changed',
	array( 'RollsBar_Notifications', 'queue_when_order_is_actionable' ),
	30
);

/**
 * Delete only recent orders carrying our exact smoke marker.
 */
$cleanup_smoke_orders = static function (): int {
	$deleted = 0;
	$recent  = wc_get_orders(
		array(
			'limit'   => 50,
			'orderby' => 'date',
			'order'   => 'DESC',
			'return'  => 'objects',
		)
	);

	foreach ( $recent as $candidate ) {
		if ( $candidate instanceof WC_Order && 'rollsbar_operator_smoke' === $candidate->get_created_via() ) {
			$candidate->delete( true );
			++$deleted;
		}
	}

	return $deleted;
};

$orphan_cleanup = $cleanup_smoke_orders();
echo 'preexisting_smoke_orders_cleaned=' . (int) $orphan_cleanup . "\n";

$order     = null;
$exit_code = 0;

try {
	echo "smoke_stage=find_product\n";
	$products = wc_get_products(
		array(
			'status' => 'publish',
			'limit'  => 1,
			'return' => 'objects',
		)
	);
	$product = $products[0] ?? null;
	if ( ! $product instanceof WC_Product ) {
		throw new RuntimeException( 'No published product available for operator smoke' );
	}

	echo "smoke_stage=create_order\n";
	$order = wc_create_order(
		array(
			'status'      => 'pending',
			'created_via' => 'rollsbar_operator_smoke',
		)
	);
	if ( ! $order instanceof WC_Order ) {
		throw new RuntimeException( 'Temporary order creation failed' );
	}

	echo "smoke_stage=populate_order\n";
	$order->set_billing_first_name( 'Тест' );
	$order->set_billing_last_name( 'Оператор' );
	$order->set_billing_phone( '+79780000000' );
	$order->set_billing_email( 'operator-smoke@example.invalid' );
	$order->set_shipping_first_name( 'Тест' );
	$order->set_shipping_last_name( 'Оператор' );
	$order->set_shipping_address_1( 'Кечкеметская улица, 1' );
	$order->set_shipping_city( 'Симферополь' );
	$order->set_customer_note( 'Тест операторского интерфейса. Не выполнять.' );
	$order->update_meta_data( '_rollsbar_delivery_zone', 'Тестовая зона' );
	$order->update_meta_data( '_rollsbar_telegram_status', 'not_configured' );

	// Official WooCommerce Additional Checkout Fields order/contact group prefix.
	// Keep the documented value literal here so the smoke does not depend on the
	// visibility of an internal class constant in a particular Woo release.
	$other_prefix = '_wc_other/';
	$order->update_meta_data( $other_prefix . 'rollsbar/entrance', '2' );
	$order->update_meta_data( $other_prefix . 'rollsbar/door-code', '15' );
	$order->update_meta_data( $other_prefix . 'rollsbar/floor', '4' );
	$order->update_meta_data( $other_prefix . 'rollsbar/apartment-office', '27' );

	$shipping = new WC_Order_Item_Shipping();
	$shipping->set_method_title( 'Доставка курьером' );
	$shipping->set_method_id( 'flat_rate' );
	$shipping->set_total( '0' );
	$order->add_item( $shipping );
	$order->add_product( $product, 1 );
	$order->calculate_totals();
	$order->save();

	$order_id = $order->get_id();
	if ( $order_id <= 0 ) {
		throw new RuntimeException( 'Temporary order has no ID' );
	}

	echo "smoke_stage=reload_order\n";
	$reloaded = wc_get_order( $order_id );
	if ( ! $reloaded instanceof WC_Order ) {
		throw new RuntimeException( 'Temporary order cannot be reloaded' );
	}
	if ( 'pending' !== $reloaded->get_status() ) {
		throw new RuntimeException( 'Temporary order unexpectedly changed status' );
	}
	if ( 'rollsbar_operator_smoke' !== $reloaded->get_created_via() ) {
		throw new RuntimeException( 'Temporary order marker missing' );
	}

	echo "smoke_stage=verify_columns\n";
	$columns = RollsBar_Order_Details::add_order_list_columns(
		array(
			'cb'           => '<input type="checkbox">',
			'order_number' => 'Order',
			'order_status' => 'Status',
		)
	);
	$expected_columns = array(
		'rollsbar_customer' => 'Имя',
		'rollsbar_phone'    => 'Телефон',
		'rollsbar_address'  => 'Адрес',
		'rollsbar_zone'     => 'Зона доставки',
		'rollsbar_time'     => 'Время',
	);
	foreach ( $expected_columns as $key => $label ) {
		if ( ( $columns[ $key ] ?? '' ) !== $label ) {
			throw new RuntimeException( 'Operator column missing: ' . $key );
		}
	}

	$rendered_columns = array();
	foreach ( array_keys( $expected_columns ) as $column ) {
		ob_start();
		RollsBar_Order_Details::render_order_list_column( $column, $reloaded );
		$rendered_columns[ $column ] = trim( wp_strip_all_tags( (string) ob_get_clean() ) );
	}

	$column_expectations = array(
		'rollsbar_customer' => 'Тест Оператор',
		'rollsbar_phone'    => '+79780000000',
		'rollsbar_address'  => 'Кечкеметская улица, 1, кв./офис 27',
		'rollsbar_zone'     => 'Тестовая зона',
	);
	foreach ( $column_expectations as $column => $expected ) {
		if ( $rendered_columns[ $column ] !== $expected ) {
			throw new RuntimeException( $column . ' mismatch: ' . $rendered_columns[ $column ] );
		}
	}
	if ( ! preg_match( '/^\\d{2}:\\d{2}$/', $rendered_columns['rollsbar_time'] ) ) {
		throw new RuntimeException( 'Order time column is not HH:MM' );
	}

	echo "smoke_stage=verify_additional_fields\n";
	$extra = RollsBar_Order_Details::additional_fields( $reloaded );
	$expected_extra = array(
		'Подъезд'              => '2',
		'Код двери / домофона' => '15',
		'Этаж'                 => '4',
		'Квартира / офис'      => '27',
	);
	foreach ( $expected_extra as $label => $value ) {
		if ( ( $extra[ $label ] ?? '' ) !== $value ) {
			throw new RuntimeException( 'Additional field mismatch: ' . $label );
		}
	}

	echo "smoke_stage=verify_detail_panel\n";
	ob_start();
	RollsBar_Order_Details::render_admin_delivery_details( $reloaded );
	$detail_html = (string) ob_get_clean();
	$detail_text = wp_strip_all_tags( $detail_html );

	foreach (
		array(
			'Rolls Bar — детали заказа',
			'Получение:',
			'Доставка курьером',
			'Подъезд:',
			'Код двери / домофона:',
			'Этаж:',
			'Квартира / офис:',
			'Telegram:',
			'не настроено',
		) as $needle
	) {
		if ( false === strpos( $detail_text, $needle ) ) {
			throw new RuntimeException( 'Admin order detail missing: ' . $needle );
		}
	}

	if ( count( $reloaded->get_items() ) < 1 ) {
		throw new RuntimeException( 'Order item list is empty' );
	}
	if ( '' === trim( (string) $reloaded->get_customer_note() ) ) {
		throw new RuntimeException( 'Customer comment missing' );
	}

	echo "OPERATOR WORKFLOW RUNTIME PASS\n";
	echo "temporary_order_created=yes\n";
	echo "order_status=pending_only\n";
	echo "external_email_sent=no\n";
	echo "external_telegram_sent=no\n";
	echo "operator_columns=name,phone,address,zone,time\n";
	echo "additional_address_fields=4\n";
	echo "order_items_visible=yes\n";
	echo "customer_comment_persisted=yes\n";
	echo "production_touched=no\n";
} catch ( Throwable $exception ) {
	fwrite( STDERR, 'OPERATOR WORKFLOW RUNTIME FAIL: ' . $exception->getMessage() . "\n" );
	$exit_code = 1;
} finally {
	echo "smoke_stage=cleanup\n";
	if ( $order instanceof WC_Order && $order->get_id() > 0 ) {
		$order_id = $order->get_id();
		$order->delete( true );
		if ( wc_get_order( $order_id ) ) {
			fwrite( STDERR, "temporary order cleanup failed\n" );
			$exit_code = 1;
		} else {
			echo "temporary_order_cleanup=pass\n";
		}
	}

	$remaining_smoke_orders = 0;
	$recent = wc_get_orders(
		array(
			'limit'   => 50,
			'orderby' => 'date',
			'order'   => 'DESC',
			'return'  => 'objects',
		)
	);
	foreach ( $recent as $candidate ) {
		if ( $candidate instanceof WC_Order && 'rollsbar_operator_smoke' === $candidate->get_created_via() ) {
			++$remaining_smoke_orders;
		}
	}
	echo 'remaining_smoke_orders=' . (int) $remaining_smoke_orders . "\n";
	if ( 0 !== $remaining_smoke_orders ) {
		$exit_code = 1;
	}
}

if ( 0 !== $exit_code ) {
	exit( $exit_code );
}

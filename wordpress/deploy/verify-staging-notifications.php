<?php
/**
 * Runtime smoke for Rolls Bar order notifications.
 *
 * This test intentionally intercepts wp_mail() and Telegram HTTP requests.
 * It proves the WordPress/WooCommerce integration, Action Scheduler queue,
 * success/idempotency behavior and retry path without contacting real users.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit( 1 );
}

if ( ! class_exists( 'WooCommerce' ) || ! class_exists( 'RollsBar_Notifications' ) ) {
	fwrite( STDERR, "Notification dependencies are not loaded.\n" );
	exit( 1 );
}

$created_orders = array();
$captured_mail  = array();
$telegram_calls = 0;
$telegram_body  = array();

$telegram_token_filter = static function (): string {
	return '123456:ROLLSBAR_QA_TOKEN';
};
$telegram_chat_filter = static function (): string {
	return '-1001234567890';
};
$new_order_recipient_filter = static function (): string {
	return 'rollsbar-notification-qa@example.com';
};
$mail_interceptor = static function ( $pre, array $atts ) use ( &$captured_mail ) {
	$captured_mail[] = $atts;
	return true;
};
$telegram_success_interceptor = static function ( $pre, array $args, string $url ) use ( &$telegram_calls, &$telegram_body ) {
	if ( false === strpos( $url, 'https://api.telegram.org/bot' ) ) {
		return $pre;
	}

	++$telegram_calls;
	$telegram_body = isset( $args['body'] ) && is_array( $args['body'] ) ? $args['body'] : array();

	return array(
		'headers'  => array(),
		'body'     => wp_json_encode( array( 'ok' => true, 'result' => array( 'message_id' => 1 ) ) ),
		'response' => array( 'code' => 200, 'message' => 'OK' ),
		'cookies'  => array(),
		'filename' => null,
	);
};
$telegram_failure_interceptor = static function ( $pre, array $args, string $url ) {
	unset( $args );

	if ( false === strpos( $url, 'https://api.telegram.org/bot' ) ) {
		return $pre;
	}

	return array(
		'headers'  => array(),
		'body'     => wp_json_encode( array( 'ok' => false ) ),
		'response' => array( 'code' => 500, 'message' => 'Synthetic QA failure' ),
		'cookies'  => array(),
		'filename' => null,
	);
};

$fail = static function ( string $message ): void {
	fwrite( STDERR, $message . "\n" );
	throw new RuntimeException( $message );
};

$make_order = static function ( string $suffix ) use ( &$created_orders, $fail ): WC_Order {
	$order = wc_create_order();
	if ( is_wp_error( $order ) || ! $order instanceof WC_Order ) {
		$fail( 'Could not create synthetic WooCommerce order.' );
	}

	$product_ids = wc_get_products(
		array(
			'status' => 'publish',
			'limit'  => 1,
			'return' => 'ids',
		)
	);
	if ( empty( $product_ids ) ) {
		$fail( 'Notification smoke requires at least one published product.' );
	}

	$product = wc_get_product( (int) $product_ids[0] );
	if ( ! $product instanceof WC_Product ) {
		$fail( 'Could not load smoke product.' );
	}

	$order->add_product( $product, 2 );
	$order->set_billing_first_name( 'Notification' );
	$order->set_billing_last_name( 'Smoke-' . $suffix );
	$order->set_billing_phone( '+79990000000' );
	$order->set_billing_email( 'notification-smoke@example.com' );
	$order->set_shipping_first_name( 'Notification' );
	$order->set_shipping_last_name( 'Smoke-' . $suffix );
	$order->set_shipping_address_1( 'QA Secret Address 123' );
	$order->set_shipping_city( 'QA City' );
	$order->set_customer_note( 'QA customer comment' );
	$order->calculate_totals();
	$order->save();
	$created_orders[] = $order->get_id();

	return $order;
};

add_filter( 'rollsbar_telegram_bot_token', $telegram_token_filter );
add_filter( 'rollsbar_telegram_chat_id', $telegram_chat_filter );
add_filter( 'woocommerce_email_recipient_new_order', $new_order_recipient_filter );
add_filter( 'pre_wp_mail', $mail_interceptor, 10, 2 );
add_filter( 'pre_http_request', $telegram_success_interceptor, 10, 3 );

try {
	$order = $make_order( 'success' );
	$order_id = $order->get_id();
	$order->update_status( 'processing', 'Rolls Bar notification runtime smoke.', true );
	$order = wc_get_order( $order_id );

	if ( ! $order instanceof WC_Order ) {
		$fail( 'Could not reload synthetic order.' );
	}

	if ( 'queued' !== (string) $order->get_meta( '_rollsbar_telegram_status', true ) ) {
		$fail( 'Actionable order was not queued for Telegram.' );
	}

	if ( 0 !== (int) $order->get_meta( '_rollsbar_telegram_attempts', true ) ) {
		$fail( 'Queued Telegram order has an unexpected attempt count.' );
	}

	if ( function_exists( 'as_has_scheduled_action' ) && ! as_has_scheduled_action( 'rollsbar_send_order_notifications', array( 'order_id' => $order_id ), 'rollsbar' ) ) {
		$fail( 'Action Scheduler does not contain the queued Telegram action.' );
	}

	$new_order_mail_seen = false;
	foreach ( $captured_mail as $mail ) {
		$to = $mail['to'] ?? '';
		$to = is_array( $to ) ? implode( ',', $to ) : (string) $to;
		if ( false !== strpos( $to, 'rollsbar-notification-qa@example.com' ) ) {
			$new_order_mail_seen = true;
			if ( empty( $mail['subject'] ) || empty( $mail['message'] ) ) {
				$fail( 'WooCommerce new-order email reached wp_mail with an empty subject/body.' );
			}
			break;
		}
	}
	if ( ! $new_order_mail_seen ) {
		$fail( 'WooCommerce new-order email did not reach the intercepted wp_mail pipeline.' );
	}

	RollsBar_Notifications::send_async( $order_id );
	$order = wc_get_order( $order_id );
	if ( ! $order instanceof WC_Order ) {
		$fail( 'Could not reload order after Telegram send.' );
	}

	if ( 'sent' !== (string) $order->get_meta( '_rollsbar_telegram_status', true ) ) {
		$fail( 'Successful Telegram response did not mark the order sent.' );
	}
	if ( 1 !== (int) $order->get_meta( '_rollsbar_telegram_attempts', true ) ) {
		$fail( 'Successful Telegram send did not record exactly one attempt.' );
	}
	if ( 1 !== $telegram_calls ) {
		$fail( 'Telegram sender made an unexpected number of HTTP calls.' );
	}
	if ( '-1001234567890' !== (string) ( $telegram_body['chat_id'] ?? '' ) ) {
		$fail( 'Telegram request used the wrong chat ID.' );
	}

	$message = (string) ( $telegram_body['text'] ?? '' );
	if ( '' === $message || false === strpos( $message, 'Новый заказ Rolls Bar #' . $order->get_order_number() ) ) {
		$fail( 'Telegram message does not identify the order.' );
	}

	$first_item = current( $order->get_items() );
	$expected_item_name = $first_item instanceof WC_Order_Item_Product ? trim( wp_strip_all_tags( $first_item->get_name() ) ) : '';
	$required_values = array(
		'Notification Smoke-success',
		'+79990000000',
		'QA Secret Address 123',
		'QA customer comment',
		'Состав заказа:',
	);
	if ( $expected_item_name ) {
		$required_values[] = $expected_item_name;
	}
	foreach ( $required_values as $required_value ) {
		if ( false === strpos( $message, $required_value ) ) {
			$fail( 'Telegram message is missing approved operator order data: ' . $required_value );
		}
	}

	if ( false !== strpos( $message, '123456:ROLLSBAR_QA_TOKEN' ) ) {
		$fail( 'Telegram message exposed the bot token.' );
	}

	RollsBar_Notifications::send_async( $order_id );
	$order = wc_get_order( $order_id );
	if ( 1 !== $telegram_calls || 1 !== (int) $order->get_meta( '_rollsbar_telegram_attempts', true ) ) {
		$fail( 'Telegram sender is not idempotent after a successful send.' );
	}

	remove_filter( 'pre_http_request', $telegram_success_interceptor, 10 );
	add_filter( 'pre_http_request', $telegram_failure_interceptor, 10, 3 );

	$retry_order = $make_order( 'retry' );
	$retry_order_id = $retry_order->get_id();
	$retry_order->update_meta_data( '_rollsbar_telegram_status', 'queued' );
	$retry_order->update_meta_data( '_rollsbar_telegram_attempts', 0 );
	$retry_order->save();

	RollsBar_Notifications::send_async( $retry_order_id );
	$retry_order = wc_get_order( $retry_order_id );
	if ( ! $retry_order instanceof WC_Order ) {
		$fail( 'Could not reload retry order.' );
	}
	if ( 'queued' !== (string) $retry_order->get_meta( '_rollsbar_telegram_status', true ) ) {
		$fail( 'Failed first Telegram attempt was not re-queued.' );
	}
	if ( 1 !== (int) $retry_order->get_meta( '_rollsbar_telegram_attempts', true ) ) {
		$fail( 'Failed Telegram attempt count is incorrect.' );
	}
	if ( 'Telegram HTTP 500' !== (string) $retry_order->get_meta( '_rollsbar_telegram_last_error', true ) ) {
		$fail( 'Telegram failure reason was not recorded.' );
	}
	if ( function_exists( 'as_has_scheduled_action' ) && ! as_has_scheduled_action( 'rollsbar_send_order_notifications', array( 'order_id' => $retry_order_id ), 'rollsbar' ) ) {
		$fail( 'Telegram retry was not scheduled.' );
	}

	echo "ORDER NOTIFICATIONS RUNTIME PASS\n";
	echo "woocommerce_new_order_email_pipeline=intercepted_pass\n";
	echo "telegram_action_scheduler=queued\n";
	echo "telegram_success_status=sent attempts=1\n";
	echo "telegram_duplicate_send=idempotent\n";
	echo "telegram_operator_payload=pii_and_order_contents_approved_pass\n";
	echo "telegram_failure_retry=queued error=HTTP_500\n";
} catch ( Throwable $error ) {
	fwrite( STDERR, 'Notification runtime smoke failed: ' . $error->getMessage() . "\n" );
	exit( 1 );
} finally {
	remove_filter( 'rollsbar_telegram_bot_token', $telegram_token_filter );
	remove_filter( 'rollsbar_telegram_chat_id', $telegram_chat_filter );
	remove_filter( 'woocommerce_email_recipient_new_order', $new_order_recipient_filter );
	remove_filter( 'pre_wp_mail', $mail_interceptor, 10 );
	remove_filter( 'pre_http_request', $telegram_success_interceptor, 10 );
	remove_filter( 'pre_http_request', $telegram_failure_interceptor, 10 );

	foreach ( $created_orders as $created_order_id ) {
		if ( function_exists( 'as_unschedule_all_actions' ) ) {
			as_unschedule_all_actions( 'rollsbar_send_order_notifications', array( 'order_id' => $created_order_id ), 'rollsbar' );
		}
		$created_order = wc_get_order( $created_order_id );
		if ( $created_order instanceof WC_Order ) {
			$created_order->delete( true );
		}
	}
}

<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Non-blocking order notifications.
 *
 * WooCommerce remains the owner of transactional email. Telegram is a
 * supplemental operator notification and is disabled until credentials are
 * provided outside Git.
 */
final class RollsBar_Notifications {

	private const ACTION_HOOK = 'rollsbar_send_order_notifications';
	private const ACTION_GROUP = 'rollsbar';
	private const MAX_ATTEMPTS = 3;

	public static function init(): void {
		add_action(
			'woocommerce_store_api_checkout_order_processed',
			array( __CLASS__, 'queue_from_store_api' ),
			30,
			1
		);

		// Defensive fallback if the store temporarily uses classic checkout.
		add_action(
			'woocommerce_checkout_order_processed',
			array( __CLASS__, 'queue_from_classic_checkout' ),
			30,
			3
		);

		add_action(
			self::ACTION_HOOK,
			array( __CLASS__, 'send_async' ),
			10,
			1
		);
	}

	public static function queue_from_store_api( WC_Order $order ): void {
		self::queue_order( $order );
	}

	public static function queue_from_classic_checkout( int $order_id, array $posted_data, WC_Order $order ): void {
		unset( $posted_data );
		self::queue_order( $order ?: wc_get_order( $order_id ) );
	}

	private static function queue_order( $order ): void {
		if ( ! $order instanceof WC_Order ) {
			return;
		}

		if ( ! self::telegram_is_configured() ) {
			$order->update_meta_data( '_rollsbar_telegram_status', 'not_configured' );
			$order->save();
			return;
		}

		$status = (string) $order->get_meta( '_rollsbar_telegram_status', true );

		if ( in_array( $status, array( 'queued', 'sent' ), true ) ) {
			return;
		}

		$order->update_meta_data( '_rollsbar_telegram_status', 'queued' );
		$order->update_meta_data( '_rollsbar_telegram_attempts', 0 );
		$order->save();

		self::schedule( $order->get_id(), true );
	}

	private static function schedule( int $order_id, bool $async ): void {
		if ( function_exists( 'as_enqueue_async_action' ) && function_exists( 'as_schedule_single_action' ) ) {
			if ( $async ) {
				as_enqueue_async_action(
					self::ACTION_HOOK,
					array( 'order_id' => $order_id ),
					self::ACTION_GROUP,
					true
				);
			} else {
				as_schedule_single_action(
					time() + 300,
					self::ACTION_HOOK,
					array( 'order_id' => $order_id ),
					self::ACTION_GROUP,
					true
				);
			}
			return;
		}

		$timestamp = time() + ( $async ? 5 : 300 );

		if ( ! wp_next_scheduled( self::ACTION_HOOK, array( $order_id ) ) ) {
			wp_schedule_single_event( $timestamp, self::ACTION_HOOK, array( $order_id ) );
		}
	}

	public static function send_async( int $order_id ): void {
		$order = wc_get_order( $order_id );

		if ( ! $order instanceof WC_Order ) {
			return;
		}

		if ( 'sent' === (string) $order->get_meta( '_rollsbar_telegram_status', true ) ) {
			return;
		}

		if ( ! self::telegram_is_configured() ) {
			$order->update_meta_data( '_rollsbar_telegram_status', 'not_configured' );
			$order->save();
			return;
		}

		$attempts = (int) $order->get_meta( '_rollsbar_telegram_attempts', true );
		++$attempts;

		$order->update_meta_data( '_rollsbar_telegram_attempts', $attempts );
		$order->save();

		$result = self::send_telegram( $order );

		if ( true === $result ) {
			$order->update_meta_data( '_rollsbar_telegram_status', 'sent' );
			$order->update_meta_data( '_rollsbar_telegram_sent_at', gmdate( 'c' ) );
			$order->save();
			return;
		}

		$order->update_meta_data( '_rollsbar_telegram_status', 'failed' );
		$order->update_meta_data( '_rollsbar_telegram_last_error', sanitize_text_field( $result ) );
		$order->save();

		self::log_error( $order_id, $attempts, $result );

		if ( $attempts < self::MAX_ATTEMPTS ) {
			$order->update_meta_data( '_rollsbar_telegram_status', 'queued' );
			$order->save();
			self::schedule( $order_id, false );
		}
	}

	private static function send_telegram( WC_Order $order ) {
		$token   = self::telegram_token();
		$chat_id = self::telegram_chat_id();

		if ( ! $token || ! $chat_id ) {
			return 'Telegram credentials are not configured.';
		}

		$message = self::build_telegram_message( $order );
		$url     = 'https://api.telegram.org/bot' . rawurlencode( $token ) . '/sendMessage';

		$response = wp_remote_post(
			$url,
			array(
				'timeout' => 8,
				'body'    => array(
					'chat_id'                  => $chat_id,
					'text'                     => $message,
					'disable_web_page_preview' => 'true',
				),
			)
		);

		if ( is_wp_error( $response ) ) {
			return $response->get_error_message();
		}

		$code = (int) wp_remote_retrieve_response_code( $response );

		if ( $code < 200 || $code >= 300 ) {
			return 'Telegram HTTP ' . $code;
		}

		$body = json_decode( (string) wp_remote_retrieve_body( $response ), true );

		if ( ! is_array( $body ) || empty( $body['ok'] ) ) {
			return 'Telegram returned an invalid response.';
		}

		return true;
	}

	private static function build_telegram_message( WC_Order $order ): string {
		$items_count = 0;

		foreach ( $order->get_items() as $item ) {
			$items_count += (int) $item->get_quantity();
		}

		$total = wp_specialchars_decode(
			wp_strip_all_tags( $order->get_formatted_order_total() ),
			ENT_QUOTES
		);

		$lines = array(
			'Новый заказ Rolls Bar #' . $order->get_order_number(),
			'Сумма: ' . $total,
			'Позиций: ' . $items_count,
			'Получение: ' . RollsBar_Order_Details::fulfillment_label( $order ),
			'Статус: ' . wc_get_order_status_name( $order->get_status() ),
			'Открыть в админке: ' . $order->get_edit_order_url(),
		);

		$include_personal_data = (bool) apply_filters(
			'rollsbar_telegram_include_personal_data',
			false,
			$order
		);

		if ( $include_personal_data ) {
			$name = trim( $order->get_formatted_billing_full_name() );
			$phone = trim( (string) $order->get_billing_phone() );
			$address = trim( wp_strip_all_tags( $order->get_formatted_shipping_address() ) );

			if ( $name ) {
				$lines[] = 'Клиент: ' . $name;
			}

			if ( $phone ) {
				$lines[] = 'Телефон: ' . $phone;
			}

			if ( $address ) {
				$lines[] = 'Адрес: ' . preg_replace( '/\s+/', ' ', $address );
			}

			foreach ( RollsBar_Order_Details::additional_fields( $order ) as $label => $value ) {
				$lines[] = $label . ': ' . $value;
			}
		}

		return implode( "\n", $lines );
	}

	public static function telegram_is_configured(): bool {
		return '' !== self::telegram_token() && '' !== self::telegram_chat_id();
	}

	public static function configuration_status(): array {
		return array(
			'telegram' => self::telegram_is_configured(),
			'email'    => true,
		);
	}

	private static function telegram_token(): string {
		$value = '';

		if ( defined( 'ROLLSBAR_TELEGRAM_BOT_TOKEN' ) ) {
			$value = (string) constant( 'ROLLSBAR_TELEGRAM_BOT_TOKEN' );
		} elseif ( getenv( 'ROLLSBAR_TELEGRAM_BOT_TOKEN' ) ) {
			$value = (string) getenv( 'ROLLSBAR_TELEGRAM_BOT_TOKEN' );
		}

		return trim(
			(string) apply_filters( 'rollsbar_telegram_bot_token', $value )
		);
	}

	private static function telegram_chat_id(): string {
		$value = '';

		if ( defined( 'ROLLSBAR_TELEGRAM_CHAT_ID' ) ) {
			$value = (string) constant( 'ROLLSBAR_TELEGRAM_CHAT_ID' );
		} elseif ( getenv( 'ROLLSBAR_TELEGRAM_CHAT_ID' ) ) {
			$value = (string) getenv( 'ROLLSBAR_TELEGRAM_CHAT_ID' );
		}

		return trim(
			(string) apply_filters( 'rollsbar_telegram_chat_id', $value )
		);
	}

	private static function log_error( int $order_id, int $attempt, string $error ): void {
		if ( ! function_exists( 'wc_get_logger' ) ) {
			return;
		}

		wc_get_logger()->error(
			'Rolls Bar Telegram notification failed.',
			array(
				'source'   => 'rollsbar-core',
				'order_id' => $order_id,
				'attempt'  => $attempt,
				'error'    => $error,
			)
		);
	}
}

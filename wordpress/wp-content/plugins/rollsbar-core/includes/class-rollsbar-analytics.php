<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Consent-gated Yandex Metrica integration.
 *
 * The project can prepare stable goal wiring before the client supplies a
 * counter ID. When the ID is absent, neither the analytics JavaScript nor any
 * Yandex request is rendered. When configured, Metrica still loads only after
 * an explicit analytics-consent choice in the browser.
 */
final class RollsBar_Analytics {

	private const CONSENT_STORAGE_KEY = 'rollsbar_analytics_consent_v1';

	private const GOALS = array(
		'add_to_cart'            => 'add_to_cart',
		'open_cart'              => 'open_cart',
		'begin_checkout'         => 'begin_checkout',
		'submit_order'           => 'submit_order',
		'purchase'               => 'purchase',
		'phone_click'            => 'phone_click',
		'shipping_method_select' => 'shipping_method_select',
	);

	public static function init(): void {
		add_action( 'wp_enqueue_scripts', array( __CLASS__, 'enqueue_assets' ), 40 );
		add_action( 'wp_footer', array( __CLASS__, 'render_consent_banner' ), 50 );
	}

	public static function counter_id(): string {
		$value = trim( RollsBar_Settings::get( 'metrika_counter_id' ) );

		return preg_match( '/^[1-9][0-9]{3,19}$/', $value ) ? $value : '';
	}

	public static function is_enabled(): bool {
		return '' !== self::counter_id();
	}

	public static function goals(): array {
		return self::GOALS;
	}

	public static function consent_storage_key(): string {
		return self::CONSENT_STORAGE_KEY;
	}

	public static function enqueue_assets(): void {
		if ( is_admin() || ! self::is_enabled() ) {
			return;
		}

		wp_enqueue_style(
			'rollsbar-analytics-consent',
			plugins_url( 'assets/css/analytics-consent.css', ROLLSBAR_CORE_FILE ),
			array(),
			ROLLSBAR_CORE_VERSION
		);

		wp_enqueue_script(
			'rollsbar-analytics',
			plugins_url( 'assets/js/analytics.js', ROLLSBAR_CORE_FILE ),
			array( 'jquery' ),
			ROLLSBAR_CORE_VERSION,
			true
		);

		$config = array(
			'counterId'  => self::counter_id(),
			'consentKey' => self::CONSENT_STORAGE_KEY,
			'goals'      => self::GOALS,
			'context'    => self::page_context(),
			'init'       => array(
				'clickmap'            => false,
				'trackLinks'          => false,
				'accurateTrackBounce' => true,
				'webvisor'            => false,
				'sendTitle'           => false,
			),
		);

		wp_add_inline_script(
			'rollsbar-analytics',
			'window.rollsBarAnalyticsConfig=' . wp_json_encode( $config, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . ';',
			'before'
		);
	}

	private static function page_context(): array {
		$context = array(
			'isCart'          => function_exists( 'is_cart' ) && is_cart(),
			'isCheckout'      => function_exists( 'is_checkout' ) && is_checkout(),
			'isOrderReceived' => function_exists( 'is_order_received_page' ) && is_order_received_page(),
			'purchase'        => null,
		);

		if ( ! $context['isOrderReceived'] || ! function_exists( 'wc_get_order' ) ) {
			return $context;
		}

		$order_id = absint( get_query_var( 'order-received' ) );
		if ( ! $order_id ) {
			return $context;
		}

		$order = wc_get_order( $order_id );
		if ( ! $order instanceof WC_Order ) {
			return $context;
		}

		$context['purchase'] = array(
			'order_price' => (float) $order->get_total(),
			'currency'    => (string) $order->get_currency(),
		);

		return $context;
	}

	public static function render_consent_banner(): void {
		if ( is_admin() || ! self::is_enabled() ) {
			return;
		}
		?>
		<div class="rollsbar-cookie-consent" data-rollsbar-cookie-consent hidden role="region" aria-label="Настройки cookies">
			<div class="rollsbar-cookie-consent__copy">
				<strong>Cookies и статистика</strong>
				<span>Необходимые cookies используются для корзины и оформления заказа. С вашего согласия мы также можем включить Яндекс Метрику для статистики использования сайта.</span>
				<a href="<?php echo esc_url( home_url( '/cookies/' ) ); ?>">Подробнее</a>
			</div>
			<div class="rollsbar-cookie-consent__actions">
				<button type="button" data-rollsbar-analytics-deny>Только необходимые</button>
				<button type="button" class="is-primary" data-rollsbar-analytics-allow>Разрешить аналитику</button>
			</div>
		</div>
		<?php
	}
}

<?php
/**
 * Runtime verification for the approved launch payment mode.
 *
 * Current Rolls Bar scope: payment at receipt. Online card acquiring is a
 * separate later phase and must stay unavailable until an actual provider,
 * contract and tested gateway are configured.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit( 1 );
}

$fail = static function ( string $message ): void {
	fwrite( STDERR, $message . "\n" );
	exit( 1 );
};

if ( ! function_exists( 'WC' ) || ! WC()->payment_gateways() ) {
	$fail( 'WooCommerce payment gateway manager is unavailable.' );
}

$gateways = WC()->payment_gateways()->payment_gateways();
if ( empty( $gateways['cod'] ) ) {
	$fail( 'WooCommerce cash-on-delivery gateway is unavailable.' );
}

$cod = $gateways['cod'];
if ( 'yes' !== (string) $cod->enabled ) {
	$fail( 'Launch payment-at-receipt gateway is not enabled.' );
}
if ( 'Оплата при получении' !== trim( (string) $cod->title ) ) {
	$fail( 'Launch payment gateway title is not the approved provider-neutral title.' );
}

$enabled = array();
foreach ( $gateways as $gateway_id => $gateway ) {
	if ( 'yes' === (string) $gateway->enabled ) {
		$enabled[] = (string) $gateway_id;
	}
}

$unexpected = array_values( array_diff( $enabled, array( 'cod' ) ) );
if ( $unexpected ) {
	$fail( 'Unexpected payment gateway(s) enabled before acquiring activation: ' . implode( ',', $unexpected ) );
}

foreach ( array( 'bacs', 'cheque' ) as $offline_id ) {
	if ( isset( $gateways[ $offline_id ] ) && 'yes' === (string) $gateways[ $offline_id ]->enabled ) {
		$fail( "Unapproved offline payment gateway is enabled: {$offline_id}" );
	}
}

$payment_page = get_page_by_path( 'oplata-i-vozvrat', OBJECT, 'page' );
if ( ! $payment_page instanceof WP_Post || 'publish' !== $payment_page->post_status ) {
	$fail( 'Payment/refund legal page is missing.' );
}
$payment_text = wp_strip_all_tags( (string) $payment_page->post_content );

// Verify the meaning of the immutable approved baseline rather than tying the
// test to one editorial sentence. Before acquiring is connected the site says
// payment is at receipt; online card payment becomes available only after an
// actual payment gateway is connected.
if ( false === strpos( $payment_text, 'До активации интернет-эквайринга заказ оплачивается при получении.' ) ) {
	$fail( 'Payment/refund page no longer states the approved payment-at-receipt launch mode.' );
}
if (
	false === strpos( $payment_text, 'Онлайн-оплата банковской картой становится доступной только после подключения платёжного шлюза' )
) {
	$fail( 'Payment/refund page no longer keeps online card payment conditional on gateway activation.' );
}

$security_page = get_page_by_path( 'bezopasnost-onlajn-oplaty', OBJECT, 'page' );
if ( ! $security_page instanceof WP_Post || 'publish' !== $security_page->post_status ) {
	$fail( 'Payment-security page is missing.' );
}
$security_text = wp_strip_all_tags( (string) $security_page->post_content );
$card_storage_safe = false !== stripos( $security_text, 'не должны хранить' )
	|| false !== stripos( $security_text, 'не сохраня' );
if ( ! $card_storage_safe ) {
	$fail( 'Payment-security page no longer states that full card data is not stored by Rolls Bar/WooCommerce.' );
}
if ( false !== stripos( $security_text, 'Сбербанк' ) || false !== stripos( $security_text, 'СберБанк' ) ) {
	$fail( 'Payment-security page still claims an unverified acquiring provider.' );
}
if ( false === stripos( $security_text, 'защищённой платёжной форме банка' ) ) {
	$fail( 'Payment-security page no longer states that card entry belongs on the bank payment form.' );
}

update_option( 'rollsbar_online_payment_state', 'reserved_disabled', false );

echo "PAYMENT LAUNCH MODE RUNTIME PASS\n";
echo "payment_at_receipt=enabled\n";
echo "cod_title=Оплата при получении\n";
echo "enabled_gateway_ids=" . implode( ',', $enabled ) . "\n";
echo "online_payment_state=reserved_disabled\n";
echo "online_card_gateway_visible=no\n";
echo "provider_specific_gateway=not_assumed\n";

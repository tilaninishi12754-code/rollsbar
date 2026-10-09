<?php
/**
 * Runtime verification for legal/payment-readiness wiring.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit( 1 );
}

$fail = static function ( string $message ): void {
	fwrite( STDERR, $message . "\n" );
	exit( 1 );
};

$expected_pages = array(
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

$page_ids = array();
foreach ( $expected_pages as $slug ) {
	$page = get_page_by_path( $slug, OBJECT, 'page' );
	if ( ! $page instanceof WP_Post ) {
		$fail( "Legal page is missing: {$slug}" );
	}
	if ( 'publish' !== $page->post_status ) {
		$fail( "Legal page is not published: {$slug}" );
	}
	if ( '' === trim( (string) $page->post_content ) ) {
		$fail( "Legal page has empty content: {$slug}" );
	}
	$page_ids[ $slug ] = (int) $page->ID;

	$content = (string) $page->post_content;
	if ( preg_match( '/href=["\'][^"\']+\.html(?:[?#][^"\']*)?["\']/i', $content ) ) {
		$fail( "Static .html link leaked into WordPress legal page: {$slug}" );
	}
	if ( false !== stripos( $content, 'Сбербанк' ) || false !== stripos( $content, 'СберБанк' ) ) {
		$fail( "Unverified acquiring provider leaked into legal page: {$slug}" );
	}
}

$terms_page_id = absint( get_option( 'woocommerce_terms_page_id', 0 ) );
if ( $terms_page_id !== $page_ids['publichnaya-oferta'] ) {
	$fail( 'WooCommerce terms page is not wired to the public offer.' );
}

$privacy_page_id = absint( get_option( 'wp_page_for_privacy_policy', 0 ) );
if ( $privacy_page_id !== $page_ids['politika-konfidencialnosti'] ) {
	$fail( 'WordPress privacy policy page is not wired to the Rolls Bar policy.' );
}

$requisites = get_post( $page_ids['rekvizity-prodavca'] );
$requisites_text = $requisites instanceof WP_Post ? wp_strip_all_tags( $requisites->post_content ) : '';
foreach ( array( 'ИП Гридина Надежда Викторовна', '910504301819', '325911200130902' ) as $required_requisite ) {
	if ( false === strpos( $requisites_text, $required_requisite ) ) {
		$fail( 'Seller requisites are incomplete.' );
	}
}

$delivery = get_post( $page_ids['dostavka-i-oplata'] );
$delivery_text = $delivery instanceof WP_Post ? wp_strip_all_tags( $delivery->post_content ) : '';
if ( false === strpos( $delivery_text, 'Автоматическое применение этих правил на сайте будет включено только после утверждения точных границ зон.' ) ) {
	$fail( 'Delivery page does not disclose deferred polygon enforcement.' );
}
if ( false === strpos( $delivery_text, 'самовывоз' ) && false === strpos( $delivery_text, 'Самовывоз' ) ) {
	$fail( 'Delivery page does not preserve pickup information.' );
}

if ( ! class_exists( 'RollsBar_Checkout' ) ) {
	$fail( 'RollsBar checkout module is not loaded.' );
}

$container = \Automattic\WooCommerce\Blocks\Package::container();
$service   = 'Automattic\\WooCommerce\\Blocks\\Domain\\Services\\CheckoutFields';
$fields    = $container->get( $service )->get_additional_fields();
$consent   = $fields['rollsbar/privacy-consent'] ?? null;
if ( ! is_array( $consent ) ) {
	$fail( 'Required checkout privacy-consent field is not registered.' );
}
if ( 'checkbox' !== (string) ( $consent['type'] ?? '' ) || empty( $consent['required'] ) ) {
	$fail( 'Checkout privacy-consent field must be a required checkbox.' );
}

if ( ! class_exists( 'RollsBar_Reviews' ) ) {
	$fail( 'RollsBar reviews module is not loaded.' );
}
if ( RollsBar_Reviews::consent_is_valid( '' ) || RollsBar_Reviews::consent_is_valid( '0' ) ) {
	$fail( 'Review consent validation accepts a missing/negative value.' );
}
if ( ! RollsBar_Reviews::consent_is_valid( '1' ) ) {
	$fail( 'Review consent validation rejects affirmative consent.' );
}

$review_template = get_template_directory() . '/page-otzyvy.php';
if ( ! is_readable( $review_template ) ) {
	$fail( 'Review page template is missing.' );
}
$review_template_source = (string) file_get_contents( $review_template );
if ( false === strpos( $review_template_source, 'name="privacy_consent"' ) || false === strpos( $review_template_source, 'rbReviewPrivacyConsent' ) ) {
	$fail( 'Review form does not render the explicit privacy-consent checkbox.' );
}

$footer_source = (string) file_get_contents( get_template_directory() . '/footer.php' );
foreach ( array( '/publichnaya-oferta/', '/oplata-i-vozvrat/', '/politika-konfidencialnosti/', '/rekvizity-prodavca/', '/pravovaya-informaciya/' ) as $footer_link ) {
	if ( false === strpos( $footer_source, $footer_link ) ) {
		$fail( "Footer is missing legal link: {$footer_link}" );
	}
}

echo "LEGAL / PAYMENT READINESS RUNTIME PASS\n";
echo 'legal_pages_published=' . count( $page_ids ) . "\n";
echo "woocommerce_terms_page=publichnaya-oferta\n";
echo "wordpress_privacy_page=politika-konfidencialnosti\n";
echo "checkout_privacy_consent=required_checkbox\n";
echo "review_privacy_consent=required_server_and_form\n";
echo "acquiring_provider_claim=neutral_until_connected\n";
echo "delivery_polygon_enforcement=disclosed_as_deferred\n";

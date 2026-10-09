<?php
/**
 * Provision editable WordPress legal/payment-readiness pages from the frozen
 * approved static baseline. Existing pages are never overwritten, so later
 * client/admin edits survive routine deployments.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit( 1 );
}

$project_root = rtrim( (string) getenv( 'PROJECT_ROOT' ), '/\\' );
if ( '' === $project_root || ! is_dir( $project_root ) ) {
	fwrite( STDERR, "PROJECT_ROOT is required to provision legal pages.\n" );
	exit( 1 );
}

$pages = array(
	'legal.html'            => 'pravovaya-informaciya',
	'requisites.html'       => 'rekvizity-prodavca',
	'offer.html'            => 'publichnaya-oferta',
	'delivery-payment.html' => 'dostavka-i-oplata',
	'payment-refund.html'   => 'oplata-i-vozvrat',
	'privacy.html'          => 'politika-konfidencialnosti',
	'consent.html'          => 'soglasie-na-obrabotku-personalnyh-dannyh',
	'cookies.html'          => 'cookies',
	'payment-security.html' => 'bezopasnost-onlajn-oplaty',
);

$link_map = array();
foreach ( $pages as $filename => $slug ) {
	$link_map[ 'href="' . $filename . '"' ] = 'href="' . esc_url( home_url( '/' . $slug . '/' ) ) . '"';
}
$link_map['href="demo.html"'] = 'href="' . esc_url( home_url( '/' ) ) . '"';

$page_ids = array();

foreach ( $pages as $filename => $slug ) {
	$source_path = $project_root . '/' . $filename;
	if ( ! is_readable( $source_path ) ) {
		fwrite( STDERR, "Missing approved legal source: {$filename}\n" );
		exit( 1 );
	}

	$existing = get_page_by_path( $slug, OBJECT, 'page' );
	if ( $existing instanceof WP_Post && 'trash' !== $existing->post_status ) {
		$page_ids[ $slug ] = (int) $existing->ID;
		continue;
	}

	$source = (string) file_get_contents( $source_path );
	if ( ! preg_match( '/<main[^>]*>(.*)<\/main>/is', $source, $main_match ) ) {
		fwrite( STDERR, "Approved legal source has no <main>: {$filename}\n" );
		exit( 1 );
	}

	$content = trim( (string) $main_match[1] );
	$title   = '';
	if ( preg_match( '/<h1[^>]*>(.*?)<\/h1>/is', $content, $title_match ) ) {
		$title = trim( wp_strip_all_tags( $title_match[1] ) );
	}
	if ( '' === $title ) {
		fwrite( STDERR, "Approved legal source has no H1 title: {$filename}\n" );
		exit( 1 );
	}

	$content = strtr( $content, $link_map );

	// The frozen baseline predated the final acquiring-provider decision.
	// Published WordPress legal pages stay provider-neutral until a real bank
	// gateway is connected and tested; no unverified bank brand is claimed.
	$content = str_replace( array( 'СберБанка', 'Сбербанк' ), 'банка-эквайера', $content );

	// The approved static demo was authored when delivery-zone automation was
	// expected to be completed before launch. The owner has since explicitly
	// deferred exact polygons without allowing us to invent them. Keep the
	// migrated customer copy truthful: rules and thresholds exist, but automated
	// courier enforcement stays off until exact geometry is approved and tested.
	if ( 'delivery-payment.html' === $filename ) {
		$content = str_replace(
			'Rolls Bar выполняет доставку по Симферополю и ближайшим территориям в пределах утверждённых зон. Минимальная сумма, стоимость доставки и порог бесплатной доставки зависят от зоны и отображаются при оформлении заказа.',
			'Для курьерской доставки подготовлены правила по Симферополю и ближайшим территориям. Минимальная сумма и порог бесплатной доставки зависят от зоны. Автоматическое применение этих правил на сайте будет включено только после утверждения точных границ зон.',
			$content
		);
		$content = str_replace(
			'<li>Адрес указывается при оформлении заказа и автоматически сопоставляется с утверждённой зоной.</li>',
			'<li>Адрес указывается при оформлении заказа. После утверждения точных границ сайт сможет автоматически сопоставлять адрес с зоной.</li>',
			$content
		);
		$content = str_replace(
			'<li>Если сумма ниже минимальной для применимой зоны, сайт не завершает оформление и показывает, сколько нужно добрать.</li>',
			'<li>После включения курьерских зон сайт будет применять подтверждённый минимум для найденной зоны и показывать, сколько нужно добрать при необходимости.</li>',
			$content
		);
		$content = str_replace(
			'<li>Если адрес находится за пределами утверждённых зон, курьерская доставка недоступна — можно выбрать самовывоз.</li>',
			'<li>До завершения проверки точных границ автоматическое ограничение курьерской доставки по зоне не считается включённым. Самовывоз остаётся доступен.</li>',
			$content
		);
	}

	$content = str_replace(
		'демонстрационные значения зон на текущем макете должны быть заменены на окончательные суммы и границы, подтверждённые владельцем бизнеса.',
		'точные границы курьерских зон ещё не утверждены. До их утверждения автоматическое определение зоны и курьерские ограничения не включаются; самовывоз остаётся доступен.',
		$content
	);
	$content = str_replace(
		'структура подготовлена для переноса в WordPress / WooCommerce и последующего подключения интернет-эквайринга.',
		'структура перенесена в WordPress / WooCommerce для последующего подключения интернет-эквайринга.',
		$content
	);

	$page_id = wp_insert_post(
		array(
			'post_type'      => 'page',
			'post_status'    => 'publish',
			'post_title'     => $title,
			'post_name'      => $slug,
			'post_content'   => wp_kses_post( $content ),
			'comment_status' => 'closed',
			'ping_status'    => 'closed',
		),
		true
	);

	if ( is_wp_error( $page_id ) ) {
		fwrite( STDERR, "Could not create legal page {$slug}: " . $page_id->get_error_message() . "\n" );
		exit( 1 );
	}

	$page_ids[ $slug ] = (int) $page_id;
	update_post_meta( (int) $page_id, '_rollsbar_legal_source', $filename );
	update_post_meta( (int) $page_id, '_rollsbar_legal_baseline_commit', 'a5e524392abcf89ffd5ace2a18218a6b59ed3b61' );
}

if ( empty( $page_ids['publichnaya-oferta'] ) || empty( $page_ids['politika-konfidencialnosti'] ) ) {
	fwrite( STDERR, "Required legal page IDs could not be resolved.\n" );
	exit( 1 );
}

// WooCommerce renders its own terms acceptance flow; WordPress uses the
// canonical privacy-policy option. The separate personal-data consent checkbox
// is registered by RollsBar_Checkout and intentionally remains a separate act.
update_option( 'woocommerce_terms_page_id', (int) $page_ids['publichnaya-oferta'] );
update_option( 'wp_page_for_privacy_policy', (int) $page_ids['politika-konfidencialnosti'] );

echo 'LEGAL PAGES PROVISIONED ' . count( $page_ids ) . "\n";
echo 'terms_page_id=' . (int) $page_ids['publichnaya-oferta'] . "\n";
echo 'privacy_page_id=' . (int) $page_ids['politika-konfidencialnosti'] . "\n";

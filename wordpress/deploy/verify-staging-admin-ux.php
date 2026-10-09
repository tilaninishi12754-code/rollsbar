<?php
/**
 * Read-only runtime verification for the Rolls Bar client-facing admin dashboard.
 *
 * The script renders the dashboard as the staging administrator and asserts that
 * the owner-facing shortcuts/status copy match the current launch decisions.
 */

if ( ! defined( 'ABSPATH' ) ) {
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

RollsBar_Settings::register_settings();

ob_start();
RollsBar_Settings::render_page();
$html = (string) ob_get_clean();

$required = array(
	'Rolls Bar — управление сайтом',
	'Ежедневная работа',
	'Заказы',
	'Товары и цены',
	'Отзывы',
	'Акции и промо',
	'Вакансии',
	'Доставка',
	'Контакты и checkout',
	'admin.php?page=wc-orders',
	'edit.php?post_type=product',
	'edit.php?post_type=rb_review',
	'edit.php?post_type=rb_promo',
	'edit.php?post_type=rb_vacancy',
	'admin.php?page=rollsbar-delivery',
	'Что приходит в Telegram',
	'имя, телефон, адрес',
	'Не требуется для текущего запуска',
	'Можно подключить позже отдельной работой.',
);

foreach ( $required as $needle ) {
	if ( false === strpos( $html, $needle ) ) {
		fwrite( STDERR, 'admin UX missing: ' . $needle . "\n" );
		exit( 1 );
	}
}

$forbidden = array(
	'ФИО, телефон и адрес клиента туда не отправляются',
	'Секреты задаются вне Git через',
	'финальные цели с теми же ID создаются в кабинете Метрики после получения счётчика',
);

foreach ( $forbidden as $needle ) {
	if ( false !== strpos( $html, $needle ) ) {
		fwrite( STDERR, 'stale admin UX exposed: ' . $needle . "\n" );
		exit( 1 );
	}
}

$product_counts = wp_count_posts( 'product' );
$products       = is_object( $product_counts ) && isset( $product_counts->publish ) ? (int) $product_counts->publish : 0;
if ( 118 !== $products ) {
	fwrite( STDERR, 'unexpected published product count in admin UX verification: ' . $products . "\n" );
	exit( 1 );
}

if ( false === strpos( $html, 'Ждём рабочую почту клиента' ) && false === strpos( $html, 'Адрес указан — нужна контрольная доставка' ) ) {
	fwrite( STDERR, "email readiness status missing\n" );
	exit( 1 );
}

if ( false === strpos( $html, 'Ждём данные Telegram от клиента' ) && false === strpos( $html, 'Подключён — нужна контрольная доставка' ) ) {
	fwrite( STDERR, "telegram readiness status missing\n" );
	exit( 1 );
}

echo "ADMIN UX RUNTIME PASS\n";
echo "dashboard=client_operational\n";
echo "published_products=118\n";
echo "telegram_payload_copy=pii_approved\n";
echo "metrika=current_launch_not_required\n";
echo "production_touched=no\n";

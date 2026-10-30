<?php
/** Homepage header, ported from approved a5e5243. */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}
$phone_display = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'phone_display', '+7 978 688-22-88' ) : '+7 978 688-22-88';
$phone_href    = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'phone_href', '+79786882288' ) : '+79786882288';
$logo_id       = (int) get_theme_mod( 'custom_logo' );
$logo_url      = $logo_id ? wp_get_attachment_image_url( $logo_id, 'full' ) : false;
$logo_url      = $logo_url ?: get_template_directory_uri() . '/assets/images/header-logo.png';
?>
<header class="rollsbar-header rollsbar-header--approved" id="top">
	<div class="rollsbar-shell rollsbar-header__inner">
		<a class="rollsbar-brand" href="<?php echo esc_url( home_url( '/' ) ); ?>" aria-label="Rolls Bar">
			<img class="rollsbar-brand__mascot" src="<?php echo esc_url( get_template_directory_uri() . '/assets/images/header-mascot.webp' ); ?>" alt="Ниндзя Rolls Bar" width="44" height="56">
			<img class="rollsbar-brand__logo" src="<?php echo esc_url( $logo_url ); ?>" alt="Rolls Bar" width="160" height="52">
		</a>
		<div class="rollsbar-header__actions">
			<a class="rollsbar-phone" href="tel:<?php echo esc_attr( $phone_href ); ?>"><?php echo esc_html( $phone_display ); ?></a>
			<?php if ( function_exists( 'wc_get_cart_url' ) ) : ?>
				<a class="rollsbar-cart-link" href="<?php echo esc_url( wc_get_cart_url() ); ?>" aria-label="Открыть корзину">
					<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h2l1.5 9h9.8l1.7-6H7.1M10 19a1.2 1.2 0 1 1-2.4 0A1.2 1.2 0 0 1 10 19Zm8 0a1.2 1.2 0 1 1-2.4 0A1.2 1.2 0 0 1 18 19Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
					<span>Корзина</span><?php echo rollsbar_cart_badge_markup(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
					<?php echo rollsbar_header_cart_total_markup(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
				</a>
			<?php endif; ?>
			<button class="rollsbar-search-toggle" type="button" aria-label="Поиск по меню" aria-controls="rollsbarProductSearch" aria-expanded="false" data-rollsbar-search-open>
				<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="m16 16 4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
			</button>
			<button class="rollsbar-menu-toggle" type="button" aria-label="Открыть меню" aria-controls="rollsbarSiteMenu" aria-expanded="false" data-rollsbar-menu-open><span></span><span></span><span></span></button>
		</div>
	</div>
</header>

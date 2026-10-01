<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}
?>
<!doctype html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>">
	<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
	<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<a class="screen-reader-text" href="#content">Перейти к содержимому</a>

<header class="rollsbar-header" id="top">
	<div class="rollsbar-shell rollsbar-header__inner">
		<a class="rollsbar-brand" href="<?php echo esc_url( home_url( '/' ) ); ?>" aria-label="Rolls Bar">
			<?php if ( has_custom_logo() ) : ?>
				<?php the_custom_logo(); ?>
			<?php else : ?>
				<span class="rollsbar-brand__text">ROLLS <b>BAR</b></span>
			<?php endif; ?>
		</a>

		<div class="rollsbar-header__actions">
			<a class="rollsbar-phone" href="tel:+79786882288">+7 978 688-22-88</a>

			<button class="rollsbar-search-toggle" type="button" aria-controls="rollsbarProductSearch" aria-expanded="false" data-rollsbar-search-open>
				<span aria-hidden="true">⌕</span>
				<span class="screen-reader-text">Поиск</span>
			</button>

			<?php if ( function_exists( 'wc_get_cart_url' ) ) : ?>
				<a class="rollsbar-cart-link" href="<?php echo esc_url( wc_get_cart_url() ); ?>">
					<span>Корзина</span>
					<?php echo rollsbar_cart_badge_markup(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
				</a>
			<?php endif; ?>
		</div>
	</div>
</header>

<div class="rollsbar-search" id="rollsbarProductSearch" aria-hidden="true">
	<button class="rollsbar-search__backdrop" type="button" data-rollsbar-search-close aria-label="Закрыть поиск"></button>
	<div class="rollsbar-search__panel">
		<form role="search" method="get" action="<?php echo esc_url( home_url( '/' ) ); ?>">
			<label class="screen-reader-text" for="rollsbarSearchInput">Поиск по меню</label>
			<input id="rollsbarSearchInput" type="search" name="s" placeholder="Например: Филадельфия, пицца, Том Ям" autocomplete="off">
			<input type="hidden" name="post_type" value="product">
			<button type="submit">Найти</button>
		</form>
		<button class="rollsbar-search__close" type="button" data-rollsbar-search-close aria-label="Закрыть">×</button>
	</div>
</div>

<main id="content" class="rollsbar-main">

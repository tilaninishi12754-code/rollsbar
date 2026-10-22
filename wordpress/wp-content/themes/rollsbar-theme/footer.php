<?php
// Business values have one owner: the existing client-editable core settings.
$footer_phone_display = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'phone_display' ) : '';
$footer_phone_href = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'phone_href' ) : '';
$footer_city = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'city' ) : '';
$footer_address = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'address' ) : '';
$footer_vk = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'vk_url' ) : '';
$footer_telegram = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'telegram_url' ) : '';
$footer_logo_id = (int) get_theme_mod( 'custom_logo' );
$footer_logo = $footer_logo_id ? wp_get_attachment_image_url( $footer_logo_id, 'full' ) : false;
$footer_logo = $footer_logo ?: get_template_directory_uri() . '/assets/images/header-logo.png';
// Approved seller presentation uses the same editable phone, with parentheses.
$footer_seller_phone = preg_replace( '/^\+7 (\d{3}) /u', '+7 ($1) ', $footer_phone_display );
// Keep the approved local grammatical form without retaining a stale city after editing.
$footer_delivery_location = 'Симферополь' === $footer_city ? 'по ' . preg_replace( '/ь$/u', 'ю', $footer_city ) : 'в городе ' . $footer_city;
?>
<?php if ( is_front_page() ) : ?>
<section class="rollsbar-contacts rollsbar-shell" id="contacts" aria-labelledby="rollsbarContactsTitle">
	<div class="rollsbar-contacts__heading"><h2 id="rollsbarContactsTitle">Контакты</h2></div>
	<div class="rollsbar-contacts__grid">
		<article><h3>Rolls Bar</h3><p><?php echo esc_html( $footer_city . ', ' . rtrim( $footer_address, '.' ) . '.' ); ?></p></article>
		<article><h3>Телефон</h3><p><a href="tel:<?php echo esc_attr( $footer_phone_href ); ?>"><?php echo esc_html( $footer_phone_display ); ?></a><br><a href="tel:+79786990399">+7 978 699-03-99</a></p></article>
		<article><h3>Соцсети</h3><p><?php if ( $footer_vk ) : ?><a href="<?php echo esc_url( $footer_vk ); ?>" target="_blank" rel="noreferrer">VK Rolls Bar</a><?php endif; ?><?php if ( $footer_vk && $footer_telegram ) : ?><br><?php endif; ?><?php if ( $footer_telegram ) : ?><a href="<?php echo esc_url( $footer_telegram ); ?>" target="_blank" rel="noreferrer">Telegram</a><?php endif; ?></p></article>
	</div>
</section>
<?php endif; ?>
</main>

<footer class="rollsbar-footer">
	<div class="rollsbar-shell rollsbar-footer__grid">
		<div class="rollsbar-footer__brand">
			<a class="rollsbar-footer__logo" href="<?php echo esc_url( is_front_page() ? '#top' : home_url( '/#top' ) ); ?>" aria-label="Rolls Bar"><img src="<?php echo esc_url( $footer_logo ); ?>" alt="Rolls Bar"></a>
			<p>Доставка роллов, сетов, пиццы и WOK <?php echo esc_html( $footer_delivery_location ); ?>. Заказ оформляется без регистрации, детали подтверждает оператор.</p>
			<p class="rollsbar-footer__seller">ИП Гридина Надежда Викторовна · ИНН 910504301819 · ОГРНИП 325911200130902 · <?php echo esc_html( $footer_seller_phone ); ?></p>
		</div>
		<nav class="rollsbar-footer__links" aria-label="Навигация в подвале">
			<a href="<?php echo esc_url( is_front_page() ? '#sets' : home_url( '/#sets' ) ); ?>">Меню</a>
			<?php
			$footer_links = array(
				array( 'dostavka-i-oplata', 'Доставка и оплата' ),
				array( 'rekvizity-prodavca', 'Реквизиты' ),
				array( 'publichnaya-oferta', 'Оферта' ),
				array( 'oplata-i-vozvrat', 'Оплата и возврат' ),
				array( 'politika-konfidencialnosti', 'Персональные данные' ),
				array( 'cookies', 'Cookies' ),
				array( 'bezopasnost-onlajn-oplaty', 'Безопасность оплаты' ),
				array( 'otzyvy', 'Отзывы' ),
				array( 'rabota-v-rolls-bar', 'Работа в Rolls Bar' ),
				array( 'otzyvy', 'Отзывы клиентов' ),
			);
			foreach ( $footer_links as [ $slug, $label ] ) :
				?><a href="<?php echo esc_url( home_url( '/' . $slug . '/' ) ); ?>" target="_top"><?php echo esc_html( $label ); ?></a><?php
			endforeach;
			?>
		</nav>
	</div>
</footer>
<?php if ( function_exists( 'wc_get_cart_url' ) ) : ?>
	<a class="rollsbar-mobile-cart" href="<?php echo esc_url( wc_get_cart_url() ); ?>" data-rollsbar-mobile-cart <?php echo rollsbar_cart_count() ? '' : 'hidden'; ?>>
		<svg class="rollsbar-mobile-cart__icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h2l1.5 9h9.8l1.7-6H7.1M10 19a1.2 1.2 0 1 1-2.4 0A1.2 1.2 0 0 1 10 19Zm8 0a1.2 1.2 0 1 1-2.4 0A1.2 1.2 0 0 1 18 19Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
		<span class="rollsbar-mobile-cart__inner">
			<span>Корзина</span>
			<?php echo rollsbar_cart_badge_markup(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
		</span>
	</a>
	<?php if ( is_front_page() ) : ?>
	<button type="button" class="rollsbar-order-bar" data-rollsbar-orderbar aria-label="Открыть корзину" hidden>
		<span class="rollsbar-order-bar__left"><span class="rollsbar-order-bar__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 8h14l-1 12H6L5 8Zm3 0V6a4 4 0 0 1 8 0v2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span class="rollsbar-order-bar__meta"><span class="rollsbar-order-bar__count" data-rollsbar-order-count>0 товаров</span><span class="rollsbar-order-bar__hint">Перейти в корзину</span></span></span><strong class="rollsbar-order-bar__total" data-rollsbar-order-total>0 ₽</strong>
	</button>
	<?php endif; ?>
<?php endif; ?>

<?php if ( is_front_page() && function_exists( 'wc_get_checkout_url' ) ) { get_template_part( 'template-parts/cart-drawer' ); } ?>
<?php wp_footer(); ?>
</body>
</html>

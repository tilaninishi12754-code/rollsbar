</main>

<footer class="rollsbar-footer">
	<div class="rollsbar-shell rollsbar-footer__grid">
		<div class="rollsbar-footer__brand">
			<?php
			$footer_phone_display = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'phone_display', '+7 978 688-22-88' ) : '+7 978 688-22-88';
			$footer_phone_href    = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'phone_href', '+79786882288' ) : '+79786882288';
			$footer_city          = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'city', 'Симферополь' ) : 'Симферополь';
			$footer_address       = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'address', 'Кечкеметская улица, 1' ) : 'Кечкеметская улица, 1';
			?>
			<a class="rollsbar-footer__logo" href="<?php echo esc_url( home_url( '/' ) ); ?>">
				<?php if ( has_custom_logo() ) : ?>
					<?php
					$custom_logo_id = (int) get_theme_mod( 'custom_logo' );
					echo wp_get_attachment_image( $custom_logo_id, 'medium', false, array( 'alt' => 'Rolls Bar' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
					?>
				<?php else : ?>
					<strong>Rolls Bar</strong>
				<?php endif; ?>
			</a>
			<p><?php echo esc_html( $footer_city . ', ' . $footer_address ); ?></p>
			<a href="tel:<?php echo esc_attr( $footer_phone_href ); ?>"><?php echo esc_html( $footer_phone_display ); ?></a>
		</div>
		<nav class="rollsbar-footer__links" aria-label="Документы">
			<a href="<?php echo esc_url( home_url( '/dostavka-i-oplata/' ) ); ?>">Доставка и оплата</a>
			<a href="<?php echo esc_url( home_url( '/publichnaya-oferta/' ) ); ?>">Публичная оферта</a>
			<a href="<?php echo esc_url( home_url( '/oplata-i-vozvrat/' ) ); ?>">Оплата и возврат</a>
			<a href="<?php echo esc_url( home_url( '/politika-konfidencialnosti/' ) ); ?>">Персональные данные</a>
			<a href="<?php echo esc_url( home_url( '/rekvizity-prodavca/' ) ); ?>">Реквизиты продавца</a>
			<a href="<?php echo esc_url( home_url( '/pravovaya-informaciya/' ) ); ?>">Правовая информация</a>
			<a href="<?php echo esc_url( home_url( '/rabota-v-rolls-bar/' ) ); ?>">Работа в Rolls Bar</a>
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

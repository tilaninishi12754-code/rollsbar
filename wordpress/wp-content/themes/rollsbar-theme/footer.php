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
		<span class="rollsbar-mobile-cart__inner">
			<span>Корзина</span>
			<?php echo rollsbar_cart_badge_markup(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
		</span>
	</a>
<?php endif; ?>

<?php wp_footer(); ?>
</body>
</html>

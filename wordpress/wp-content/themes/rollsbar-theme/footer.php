</main>

<footer class="rollsbar-footer">
	<div class="rollsbar-shell rollsbar-footer__grid">
		<div>
			<strong>Rolls Bar</strong>
			<p>Симферополь, Кечкеметская улица, 1</p>
			<a href="tel:+79786882288">+7 978 688-22-88</a>
		</div>
		<nav class="rollsbar-footer__links" aria-label="Документы">
			<a href="<?php echo esc_url( home_url( '/dostavka-i-oplata/' ) ); ?>">Доставка и оплата</a>
			<a href="<?php echo esc_url( home_url( '/publichnaya-oferta/' ) ); ?>">Публичная оферта</a>
			<a href="<?php echo esc_url( home_url( '/politika-konfidencialnosti/' ) ); ?>">Персональные данные</a>
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

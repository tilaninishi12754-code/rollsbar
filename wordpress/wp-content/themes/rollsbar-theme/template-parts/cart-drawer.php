<?php
/** Cart presentation only; native Woo state is supplied by rollsbar_cart. */
if ( ! defined( 'ABSPATH' ) ) { exit; }
?>
<div class="rollsbar-cart-drawer" id="rollsbarCartDrawer" hidden>
	<button class="rollsbar-cart-drawer__backdrop" type="button" data-rollsbar-cart-close aria-label="Закрыть корзину" tabindex="-1"></button>
	<section class="rollsbar-cart-drawer__panel" role="dialog" aria-modal="true" aria-labelledby="rollsbarCartTitle" tabindex="-1">
		<div class="rollsbar-drawer-head"><h2 id="rollsbarCartTitle">Корзина</h2><button class="rollsbar-drawer-close" type="button" data-rollsbar-cart-close aria-label="Закрыть корзину">×</button></div>
		<div class="rollsbar-drawer-body">
			<div class="rollsbar-cart-empty">Корзина пока пустая. Добавьте блюда из меню.</div>
			<div class="rollsbar-cart-list"></div>
			<section class="rollsbar-drawer-upsell"><h3>Добавить к заказу</h3><div class="rollsbar-upsell-grid"></div></section>
			<section class="rollsbar-cart-summary">
				<h3>Способ получения</h3>
				<div class="rollsbar-mode-switch"><button class="active" type="button" data-drawer-mode="delivery" aria-pressed="true">Доставка</button><button type="button" data-drawer-mode="pickup" aria-pressed="false">Самовывоз</button></div>
				<div class="rollsbar-cart-totals">
					<div class="rollsbar-cart-total-row"><span>Сумма товаров</span><span data-rollsbar-drawer-subtotal></span></div>
					<div class="rollsbar-cart-total-row"><span>Получение</span><span data-drawer-receiving>Доставка</span></div>
					<div class="rollsbar-cart-total-row"><span data-drawer-mode-label>Доставка</span><span data-drawer-mode-note>По зоне адреса</span></div>
					<div class="rollsbar-cart-total-row rollsbar-cart-total-row--main"><span>Итого на сайте</span><span data-rollsbar-drawer-subtotal></span></div>
				</div>
			</section>
			<div class="rollsbar-drawer-error" role="alert"></div>
		</div>
		<div class="rollsbar-drawer-foot"><a class="rollsbar-drawer-checkout" href="<?php echo esc_url( wc_get_checkout_url() ); ?>">Перейти к оформлению</a><div class="rollsbar-drawer-helper">При доставке зона и минимальная сумма определяются по адресу. Вне утверждённых зон доступен самовывоз.</div></div>
	</section>
</div>

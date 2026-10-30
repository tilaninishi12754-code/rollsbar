<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }
$phone_display = rollsbar_setting( 'phone_display', '+7 978 688-22-88' );
$phone_href = rollsbar_setting( 'phone_href', '+79786882288' );
?>
<div class="rollsbar-site-menu" id="rollsbarSiteMenu" aria-hidden="true">
	<button class="rollsbar-site-menu__backdrop" type="button" aria-label="Закрыть меню" data-rollsbar-menu-close></button>
	<aside class="rollsbar-site-menu__panel" role="dialog" aria-modal="true" aria-label="Меню сайта">
		<div class="rollsbar-site-menu__head"><strong>Rolls Bar</strong><button class="rollsbar-site-menu__close" type="button" aria-label="Закрыть меню" data-rollsbar-menu-close>×</button></div>
		<nav class="rollsbar-site-menu__links" aria-label="Разделы сайта">
			<a href="<?php echo esc_url( home_url( '/#rolls' ) ); ?>">Меню</a>
			<a href="<?php echo esc_url( home_url( '/#delivery' ) ); ?>">Доставка и оплата</a>
			<a href="<?php echo esc_url( home_url( '/#contacts' ) ); ?>" data-rollsbar-menu-contacts>Контакты</a>
			<a href="<?php echo esc_url( home_url( '/rabota-v-rolls-bar/' ) ); ?>">Работа в Rolls Bar</a>
			<a href="<?php echo esc_url( home_url( '/pravovaya-informaciya/' ) ); ?>">Документы и оплата</a>
			<a href="<?php echo esc_url( home_url( '/politika-konfidencialnosti/' ) ); ?>">Политика персональных данных</a>
			<a href="<?php echo esc_url( home_url( '/otzyvy/' ) ); ?>">Отзывы клиентов</a>
			<a href="https://vk.ru/rollsbar82" target="_blank" rel="noopener">VK Rolls Bar</a>
		</nav>
		<a class="rollsbar-site-menu__phone" href="tel:<?php echo esc_attr( $phone_href ); ?>"><?php echo esc_html( $phone_display ); ?></a>
	</aside>
</div>

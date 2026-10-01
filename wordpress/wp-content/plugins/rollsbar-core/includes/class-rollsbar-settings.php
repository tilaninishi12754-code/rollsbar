<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class RollsBar_Settings {

	private const OPTION = 'rollsbar_settings';

	public static function init(): void {
		add_action( 'admin_menu', array( __CLASS__, 'register_menu' ) );
		add_action( 'admin_init', array( __CLASS__, 'register_settings' ) );
		add_filter(
			'option_page_capability_rollsbar_options_group',
			static fn(): string => 'manage_woocommerce'
		);
	}

	public static function defaults(): array {
		return array(
			'phone_display' => '+7 978 688-22-88',
			'phone_href'    => '+79786882288',
			'city'          => 'Симферополь',
			'address'       => 'Кечкеметская улица, 1',
			'telegram_url'  => 'https://telegram.me/rollsbar82',
			'vk_url'        => 'https://vk.ru/rollsbar82',
		);
	}

	public static function all(): array {
		$value = get_option( self::OPTION, array() );

		return wp_parse_args(
			is_array( $value ) ? $value : array(),
			self::defaults()
		);
	}

	public static function get( string $key, string $fallback = '' ): string {
		$all = self::all();

		return isset( $all[ $key ] ) ? (string) $all[ $key ] : $fallback;
	}

	public static function sanitize( array $input ): array {
		$defaults = self::defaults();

		return array(
			'phone_display' => sanitize_text_field( $input['phone_display'] ?? $defaults['phone_display'] ),
			'phone_href'    => preg_replace( '/[^+0-9]/', '', (string) ( $input['phone_href'] ?? $defaults['phone_href'] ) ),
			'city'          => sanitize_text_field( $input['city'] ?? $defaults['city'] ),
			'address'       => sanitize_text_field( $input['address'] ?? $defaults['address'] ),
			'telegram_url'  => esc_url_raw( $input['telegram_url'] ?? $defaults['telegram_url'] ),
			'vk_url'        => esc_url_raw( $input['vk_url'] ?? $defaults['vk_url'] ),
		);
	}

	public static function register_settings(): void {
		register_setting(
			'rollsbar_options_group',
			self::OPTION,
			array(
				'type'              => 'array',
				'sanitize_callback' => array( __CLASS__, 'sanitize' ),
				'default'           => self::defaults(),
			)
		);

		add_settings_section(
			'rollsbar_business',
			'Основные данные',
			static function (): void {
				echo '<p>Эти значения используются на сайте в шапке, подвале, контактах и оформлении заказа.</p>';
			},
			'rollsbar-settings'
		);

		$fields = array(
			'phone_display' => array( 'Телефон для показа', 'text' ),
			'phone_href'    => array( 'Телефон для ссылки', 'text' ),
			'city'          => array( 'Город', 'text' ),
			'address'       => array( 'Адрес', 'text' ),
			'telegram_url'  => array( 'Telegram', 'url' ),
			'vk_url'        => array( 'VK', 'url' ),
		);

		foreach ( $fields as $key => $config ) {
			add_settings_field(
				$key,
				$config[0],
				static function () use ( $key, $config ): void {
					$value = RollsBar_Settings::get( $key );
					printf(
						'<input class="regular-text" type="%1$s" name="%2$s[%3$s]" value="%4$s">',
						esc_attr( $config[1] ),
						esc_attr( RollsBar_Settings::OPTION ),
						esc_attr( $key ),
						esc_attr( $value )
					);
				},
				'rollsbar-settings',
				'rollsbar_business'
			);
		}
	}

	public static function register_menu(): void {
		add_menu_page(
			'Rolls Bar',
			'Rolls Bar',
			'manage_woocommerce',
			'rollsbar-settings',
			array( __CLASS__, 'render_page' ),
			'dashicons-store',
			56
		);

		add_submenu_page(
			'rollsbar-settings',
			'Основные настройки',
			'Основное',
			'manage_woocommerce',
			'rollsbar-settings',
			array( __CLASS__, 'render_page' )
		);
	}

	public static function render_page(): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}

		?>
		<div class="wrap">
			<h1>Rolls Bar</h1>
			<p>Простая панель для ежедневного редактирования сайта без кода.</p>

			<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;max-width:980px;margin:18px 0 26px;">
				<a class="button button-hero" href="<?php echo esc_url( admin_url( 'edit.php?post_type=product' ) ); ?>">Товары и цены</a>
				<a class="button button-hero" href="<?php echo esc_url( admin_url( 'upload.php' ) ); ?>">Фото и файлы</a>
				<a class="button button-hero" href="<?php echo esc_url( admin_url( 'edit.php?post_type=rb_promo' ) ); ?>">Промо-карточки</a>
				<a class="button button-hero" href="<?php echo esc_url( admin_url( 'edit.php?post_type=rb_vacancy' ) ); ?>">Вакансии</a>
			</div>

			<form action="options.php" method="post">
				<?php
				settings_fields( 'rollsbar_options_group' );
				do_settings_sections( 'rollsbar-settings' );
				submit_button( 'Сохранить' );
				?>
			</form>

			<hr>
			<h2>Логотип</h2>
			<p>Логотип меняется штатно через Внешний вид → Настроить → Логотип сайта. Код для этого не нужен.</p>
		</div>
		<?php
	}
}

function rollsbar_setting( string $key, string $fallback = '' ): string {
	return RollsBar_Settings::get( $key, $fallback );
}

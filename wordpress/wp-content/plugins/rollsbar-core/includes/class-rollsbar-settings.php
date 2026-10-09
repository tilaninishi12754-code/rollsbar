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
			'phone_display'                => '+7 978 688-22-88',
			'phone_href'                   => '+79786882288',
			'city'                         => 'Симферополь',
			'address'                      => 'Кечкеметская улица, 1',
			'telegram_url'                 => 'https://telegram.me/rollsbar82',
			'vk_url'                       => 'https://vk.ru/rollsbar82',
			'metrika_counter_id'           => '',
			'checkout_entrance_required'   => '0',
			'checkout_door_code_required'  => '0',
			'checkout_floor_required'      => '0',
			'checkout_apartment_required'  => '0',
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

	public static function get_bool( string $key, bool $fallback = false ): bool {
		$value = self::get( $key, $fallback ? '1' : '0' );

		return in_array( $value, array( '1', 'yes', 'true', 'on' ), true );
	}

	public static function sanitize( array $input ): array {
		$defaults           = self::defaults();
		$metrika_counter_id = preg_replace( '/[^0-9]/', '', (string) ( $input['metrika_counter_id'] ?? $defaults['metrika_counter_id'] ) );
		if ( ! preg_match( '/^[1-9][0-9]{3,19}$/', $metrika_counter_id ) ) {
			$metrika_counter_id = '';
		}

		return array(
			'phone_display'               => sanitize_text_field( $input['phone_display'] ?? $defaults['phone_display'] ),
			'phone_href'                  => preg_replace( '/[^+0-9]/', '', (string) ( $input['phone_href'] ?? $defaults['phone_href'] ) ),
			'city'                        => sanitize_text_field( $input['city'] ?? $defaults['city'] ),
			'address'                     => sanitize_text_field( $input['address'] ?? $defaults['address'] ),
			'telegram_url'                => esc_url_raw( $input['telegram_url'] ?? $defaults['telegram_url'] ),
			'vk_url'                      => esc_url_raw( $input['vk_url'] ?? $defaults['vk_url'] ),
			'metrika_counter_id'          => $metrika_counter_id,
			'checkout_entrance_required'  => isset( $input['checkout_entrance_required'] ) ? '1' : '0',
			'checkout_door_code_required' => isset( $input['checkout_door_code_required'] ) ? '1' : '0',
			'checkout_floor_required'     => isset( $input['checkout_floor_required'] ) ? '1' : '0',
			'checkout_apartment_required' => isset( $input['checkout_apartment_required'] ) ? '1' : '0',
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
			'Контакты и адрес',
			static function (): void {
				echo '<p>Эти данные используются на сайте в шапке, подвале, контактах и оформлении заказа.</p>';
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

		add_settings_section(
			'rollsbar_checkout',
			'Оформление заказа',
			static function (): void {
				echo '<p>Дополнительные адресные поля всегда видны. Отметьте только те поля, которые должны быть обязательными для клиента.</p>';
			},
			'rollsbar-settings'
		);

		$checkout_flags = array(
			'checkout_entrance_required'  => 'Подъезд обязателен',
			'checkout_door_code_required' => 'Код двери / домофона обязателен',
			'checkout_floor_required'     => 'Этаж обязателен',
			'checkout_apartment_required' => 'Квартира / офис обязателен',
		);

		foreach ( $checkout_flags as $key => $label ) {
			add_settings_field(
				$key,
				$label,
				static function () use ( $key ): void {
					printf(
						'<label><input type="checkbox" name="%1$s[%2$s]" value="1" %3$s> Сделать поле обязательным</label>',
						esc_attr( RollsBar_Settings::OPTION ),
						esc_attr( $key ),
						checked( RollsBar_Settings::get_bool( $key ), true, false )
					);
				},
				'rollsbar-settings',
				'rollsbar_checkout'
			);
		}

		add_settings_section(
			'rollsbar_analytics',
			'Дополнительно: Яндекс Метрика',
			static function (): void {
				echo '<p><strong>Для текущего запуска Метрика не требуется.</strong> Интеграция уже подготовлена и может быть подключена позже как отдельная услуга. Пока счётчика нет, оставьте поле пустым.</p>';
			},
			'rollsbar-settings'
		);

		add_settings_field(
			'metrika_counter_id',
			'ID счётчика Яндекс Метрики',
			static function (): void {
				printf(
					'<input class="regular-text" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="20" name="%1$s[metrika_counter_id]" value="%2$s" placeholder="Например: 12345678"><p class="description">Дополнительная интеграция. ID не является секретом. Без ID Метрика не загружается.</p>',
					esc_attr( RollsBar_Settings::OPTION ),
					esc_attr( RollsBar_Settings::get( 'metrika_counter_id' ) )
				);
			},
			'rollsbar-settings',
			'rollsbar_analytics'
		);
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
			'Главная панели Rolls Bar',
			'Главная',
			'manage_woocommerce',
			'rollsbar-settings',
			array( __CLASS__, 'render_page' )
		);
	}

	private static function new_order_email_status(): array {
		$result = array(
			'enabled'           => false,
			'has_recipient'     => false,
			'is_staging_default'=> true,
		);

		if ( ! function_exists( 'WC' ) || ! WC() ) {
			return $result;
		}

		$mailer = WC()->mailer();
		if ( ! $mailer || ! method_exists( $mailer, 'get_emails' ) ) {
			return $result;
		}

		$emails    = $mailer->get_emails();
		$new_order = $emails['WC_Email_New_Order'] ?? null;
		if ( ! $new_order ) {
			return $result;
		}

		$recipient = trim( (string) $new_order->get_recipient() );

		return array(
			'enabled'            => (bool) $new_order->is_enabled(),
			'has_recipient'      => '' !== $recipient,
			'is_staging_default' => '' === $recipient || false !== strpos( strtolower( $recipient ), '@staging.rollsbar.ru' ),
		);
	}

	private static function count_status( string $post_type, string $status ): int {
		$counts = wp_count_posts( $post_type );
		return is_object( $counts ) && isset( $counts->{$status} ) ? (int) $counts->{$status} : 0;
	}

	private static function render_dashboard_card( string $title, string $description, string $url, string $icon, string $meta = '', bool $primary = false ): void {
		$border = $primary ? '#2271b1' : '#dcdcde';
		?>
		<a href="<?php echo esc_url( $url ); ?>" style="display:block;text-decoration:none;color:#1d2327;background:#fff;border:1px solid <?php echo esc_attr( $border ); ?>;border-radius:10px;padding:18px;min-height:118px;box-shadow:0 1px 2px rgba(0,0,0,.04);">
			<div style="display:flex;gap:12px;align-items:flex-start;">
				<span class="dashicons <?php echo esc_attr( $icon ); ?>" style="font-size:28px;width:28px;height:28px;color:<?php echo $primary ? '#2271b1' : '#50575e'; ?>;"></span>
				<div>
					<strong style="display:block;font-size:16px;margin-bottom:5px;"><?php echo esc_html( $title ); ?></strong>
					<span style="display:block;color:#50575e;line-height:1.45;"><?php echo esc_html( $description ); ?></span>
					<?php if ( '' !== $meta ) : ?>
						<span style="display:block;margin-top:8px;font-weight:600;color:#2271b1;"><?php echo esc_html( $meta ); ?></span>
					<?php endif; ?>
				</div>
			</div>
		</a>
		<?php
	}

	public static function render_page(): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}

		$product_count = self::count_status( 'product', 'publish' );
		$review_pending = self::count_status( 'rb_review', 'pending' );
		$promo_count = self::count_status( 'rb_promo', 'publish' );
		$vacancy_count = self::count_status( 'rb_vacancy', 'publish' );
		$delivery_rows = class_exists( 'RollsBar_Delivery_Rules' ) ? RollsBar_Delivery_Rules::all() : array();
		$delivery_shapes = count(
			array_filter(
				$delivery_rows,
				static fn( array $row ): bool => count( $row['polygon'] ?? array() ) >= 3
			)
		);
		$notification_status = class_exists( 'RollsBar_Notifications' )
			? RollsBar_Notifications::configuration_status()
			: array( 'telegram' => false, 'email' => true );
		$email_status = self::new_order_email_status();
		$metrika_enabled = class_exists( 'RollsBar_Analytics' ) && RollsBar_Analytics::is_enabled();
		?>
		<div class="wrap">
			<h1>Rolls Bar — управление сайтом</h1>
			<p style="font-size:14px;max-width:850px;">Основные действия собраны здесь. Для ежедневной работы обычно нужны только заказы, товары и отзывы.</p>

			<h2 style="margin-top:22px;">Ежедневная работа</h2>
			<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;max-width:1050px;margin:12px 0 24px;">
				<?php
				self::render_dashboard_card(
					'Заказы',
					'Новые заказы, телефон, адрес, состав и статус.',
					admin_url( 'admin.php?page=wc-orders' ),
					'dashicons-cart',
					'Открыть заказы',
					true
				);
				self::render_dashboard_card(
					'Товары и цены',
					'Названия, цены, состав, вес и карточки меню.',
					admin_url( 'edit.php?post_type=product' ),
					'dashicons-products',
					$product_count . ' опубликовано',
					true
				);
				self::render_dashboard_card(
					'Отзывы',
					'Проверить новые отзывы и опубликовать одобренные.',
					admin_url( 'edit.php?post_type=rb_review' ),
					'dashicons-star-filled',
					$review_pending > 0 ? $review_pending . ' ждут проверки' : 'Новых на проверку нет',
					true
				);
				?>
			</div>

			<h2>Контент и настройки</h2>
			<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;max-width:1050px;margin:12px 0 28px;">
				<?php
				self::render_dashboard_card( 'Акции и промо', 'Карточки акций и служебных промо-блоков.', admin_url( 'edit.php?post_type=rb_promo' ), 'dashicons-megaphone', $promo_count . ' опубликовано' );
				self::render_dashboard_card( 'Вакансии', 'Актуальные позиции на странице работы.', admin_url( 'edit.php?post_type=rb_vacancy' ), 'dashicons-businessperson', $vacancy_count . ' опубликовано' );
				self::render_dashboard_card( 'Доставка', 'Минимальные суммы и будущие границы зон.', admin_url( 'admin.php?page=rollsbar-delivery' ), 'dashicons-location-alt', $delivery_shapes . ' из ' . count( $delivery_rows ) . ' границ согласовано' );
				self::render_dashboard_card( 'Фото и файлы', 'Изображения товаров и контента сайта.', admin_url( 'upload.php' ), 'dashicons-format-image' );
				self::render_dashboard_card( 'Контакты и checkout', 'Телефон, адрес, соцсети и обязательные поля заказа.', '#rollsbar-main-settings', 'dashicons-admin-settings', 'Настроить ниже' );
				?>
			</div>

			<div id="rollsbar-main-settings" style="scroll-margin-top:40px;"></div>
			<h2>Состояние уведомлений</h2>
			<table class="widefat striped" style="max-width:1050px;margin:12px 0 26px;">
				<tbody>
					<tr>
						<td style="width:220px;"><strong>Email «Новый заказ»</strong></td>
						<td>
							<?php if ( ! $email_status['enabled'] ) : ?>
								<span style="color:#b32d2e;font-weight:700;">Выключен</span>
							<?php elseif ( $email_status['is_staging_default'] ) : ?>
								<span style="color:#a05a00;font-weight:700;">Ждём рабочую почту клиента</span>
							<?php else : ?>
								<span style="color:#2271b1;font-weight:700;">Адрес указан — нужна контрольная доставка</span>
							<?php endif; ?>
						</td>
						<td><a href="<?php echo esc_url( admin_url( 'admin.php?page=wc-settings&tab=email' ) ); ?>">Настройки email</a></td>
					</tr>
					<tr>
						<td><strong>Telegram оператора</strong></td>
						<td>
							<?php if ( ! empty( $notification_status['telegram'] ) ) : ?>
								<span style="color:#2271b1;font-weight:700;">Подключён — нужна контрольная доставка</span>
							<?php else : ?>
								<span style="color:#a05a00;font-weight:700;">Ждём данные Telegram от клиента</span>
							<?php endif; ?>
						</td>
						<td>Подключается разработчиком через защищённые настройки сервера.</td>
					</tr>
					<tr>
						<td><strong>Что приходит в Telegram</strong></td>
						<td colspan="2">Номер и сумма заказа, состав, способ получения, имя, телефон, адрес, дополнительные адресные поля и комментарий клиента.</td>
					</tr>
					<tr>
						<td><strong>Яндекс Метрика</strong></td>
						<td>
							<?php if ( $metrika_enabled ) : ?>
								<span style="color:#16803b;font-weight:700;">Подключена как дополнительная интеграция</span>
							<?php else : ?>
								<span style="color:#646970;font-weight:700;">Не требуется для текущего запуска</span>
							<?php endif; ?>
						</td>
						<td>Можно подключить позже отдельной работой.</td>
					</tr>
				</tbody>
			</table>

			<div style="max-width:1050px;background:#fff;border:1px solid #dcdcde;border-radius:10px;padding:18px 22px;margin-bottom:20px;">
				<h2 style="margin-top:0;">Основные настройки сайта</h2>
				<p>После изменения нажмите «Сохранить» внизу формы.</p>
				<form action="options.php" method="post">
					<?php
					settings_fields( 'rollsbar_options_group' );
					do_settings_sections( 'rollsbar-settings' );
					submit_button( 'Сохранить изменения' );
					?>
				</form>
			</div>

			<p class="description" style="max-width:900px;">Границы доставки, рабочая почта и реальные Telegram-данные подключаются только после получения подтверждённых данных клиента. До этого сайт не должен угадывать значения.</p>
		</div>
		<?php
	}
}

function rollsbar_setting( string $key, string $fallback = '' ): string {
	return RollsBar_Settings::get( $key, $fallback );
}

<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Editable delivery-area thresholds.
 *
 * These rows are informational/business data only. Exact address -> zone
 * matching remains disabled until approved map polygons are available.
 */
final class RollsBar_Delivery_Rules {

	private const OPTION = 'rollsbar_delivery_rules';

	public static function init(): void {
		add_action( 'admin_menu', array( __CLASS__, 'register_menu' ) );
		add_action( 'admin_init', array( __CLASS__, 'register_settings' ) );
		add_filter(
			'option_page_capability_rollsbar_delivery_rules_group',
			static fn(): string => 'manage_woocommerce'
		);
	}

	public static function defaults(): array {
		return array(
			array(
				'min_order' => 1200,
				'areas'     => array( 'Москольцо', 'Кечкеметская', 'Лермонтово', 'Гагарина', 'ж/д вокзал до Павленко' ),
			),
			array(
				'min_order' => 1500,
				'areas'     => array( 'Луговое', '51 Армии', 'Б. Куна', 'Бородина', 'Загородный', 'Белое 5', 'М. Жукова', 'Г. Сталинграда' ),
			),
			array(
				'min_order' => 2000,
				'areas'     => array( 'Живописное', 'Давыдовка', 'Свобода', 'Мирное', 'Дубки', 'от гостиницы Москва до Марьино', 'старый аэропорт', 'ГРЭС' ),
			),
			array(
				'min_order' => 2500,
				'areas'     => array( 'Строгановка', 'Молодежное', 'Аграрное', 'Белое 3', 'Марьино', 'всё, что от ул. Батурина' ),
			),
			array(
				'min_order' => 3000,
				'areas'     => array( 'Белое 4', 'Денисовка' ),
			),
			array(
				'min_order' => 3500,
				'areas'     => array( 'Урожайное', 'Долина от Лозового', 'Фонтаны' ),
			),
			array(
				'min_order' => 4000,
				'areas'     => array( 'Донское', 'Мазанка' ),
			),
		);
	}

	public static function all(): array {
		$value = get_option( self::OPTION, array() );

		if ( ! is_array( $value ) || ! $value ) {
			return self::defaults();
		}

		return self::normalize( $value );
	}

	private static function normalize( array $rows ): array {
		$result = array();

		foreach ( $rows as $row ) {
			if ( ! is_array( $row ) ) {
				continue;
			}

			$min_order = absint( $row['min_order'] ?? 0 );
			$areas     = $row['areas'] ?? array();

			if ( is_string( $areas ) ) {
				$areas = preg_split( '/\r\n|\r|\n/', $areas ) ?: array();
			}

			$areas = array_values(
				array_filter(
					array_map(
						static fn( $area ): string => sanitize_text_field( (string) $area ),
						is_array( $areas ) ? $areas : array()
					),
					static fn( string $area ): bool => '' !== trim( $area )
				)
			);

			if ( $min_order < 1 || ! $areas ) {
				continue;
			}

			$result[] = array(
				'min_order' => $min_order,
				'areas'     => $areas,
			);
		}

		usort(
			$result,
			static fn( array $a, array $b ): int => $a['min_order'] <=> $b['min_order']
		);

		return $result ?: self::defaults();
	}

	public static function sanitize( array $input ): array {
		return self::normalize( $input );
	}

	public static function register_settings(): void {
		register_setting(
			'rollsbar_delivery_rules_group',
			self::OPTION,
			array(
				'type'              => 'array',
				'sanitize_callback' => array( __CLASS__, 'sanitize' ),
				'default'           => self::defaults(),
			)
		);
	}

	public static function register_menu(): void {
		add_submenu_page(
			'rollsbar-settings',
			'Доставка',
			'Доставка',
			'manage_woocommerce',
			'rollsbar-delivery',
			array( __CLASS__, 'render_page' )
		);
	}

	public static function render_page(): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}

		$rows = self::all();
		?>
		<div class="wrap">
			<h1>Rolls Bar — доставка</h1>
			<p>Здесь хранятся подтверждённые пороги заказа для бесплатной доставки по территориям.</p>
			<div class="notice notice-warning inline" style="max-width:980px;">
				<p><strong>Автоопределение зоны по адресу пока не включено.</strong> Для него нужны точные границы полигонов. Эти данные не заменяют карту и не используются для угадывания зоны.</p>
			</div>

			<form action="options.php" method="post">
				<?php settings_fields( 'rollsbar_delivery_rules_group' ); ?>
				<table class="widefat striped" style="max-width:980px;margin-top:18px;">
					<thead>
						<tr>
							<th style="width:190px;">Бесплатная доставка от</th>
							<th>Территории</th>
						</tr>
					</thead>
					<tbody>
						<?php foreach ( $rows as $index => $row ) : ?>
							<tr>
								<td>
									<input
										type="number"
										min="1"
										step="50"
										name="<?php echo esc_attr( self::OPTION ); ?>[<?php echo esc_attr( (string) $index ); ?>][min_order]"
										value="<?php echo esc_attr( (string) $row['min_order'] ); ?>"
										style="width:120px;"
									> ₽
								</td>
								<td>
									<textarea
										name="<?php echo esc_attr( self::OPTION ); ?>[<?php echo esc_attr( (string) $index ); ?>][areas]"
										rows="4"
										class="large-text"
									><?php echo esc_textarea( implode( "\n", $row['areas'] ) ); ?></textarea>
									<p class="description">Одна территория на строку.</p>
								</td>
							</tr>
						<?php endforeach; ?>
					</tbody>
				</table>
				<?php submit_button( 'Сохранить зоны доставки' ); ?>
			</form>
		</div>
		<?php
	}
}

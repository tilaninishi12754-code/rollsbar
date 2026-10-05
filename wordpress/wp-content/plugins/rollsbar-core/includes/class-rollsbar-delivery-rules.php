<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Editable delivery thresholds + approved polygon geometry storage.
 *
 * Territory names and thresholds are business data. Polygon geometry is empty
 * until the client draws/accepts exact boundaries on staging. Address -> zone
 * enforcement remains disabled until those polygons exist and are accepted.
 */
final class RollsBar_Delivery_Rules {

	private const OPTION = 'rollsbar_delivery_rules';
	private const MAX_POLYGON_VERTICES = 150;

	public static function init(): void {
		add_action( 'admin_menu', array( __CLASS__, 'register_menu' ) );
		add_action( 'admin_init', array( __CLASS__, 'register_settings' ) );
		add_action( 'admin_enqueue_scripts', array( __CLASS__, 'enqueue_admin_assets' ) );
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
				'polygon'   => array(),
			),
			array(
				'min_order' => 1500,
				'areas'     => array( 'Луговое', '51 Армии', 'Б. Куна', 'Бородина', 'Загородный', 'Белое 5', 'М. Жукова', 'Г. Сталинграда' ),
				'polygon'   => array(),
			),
			array(
				'min_order' => 2000,
				'areas'     => array( 'Живописное', 'Давыдовка', 'Свобода', 'Мирное', 'Дубки', 'от гостиницы Москва до Марьино', 'старый аэропорт', 'ГРЭС' ),
				'polygon'   => array(),
			),
			array(
				'min_order' => 2500,
				'areas'     => array( 'Строгановка', 'Молодежное', 'Аграрное', 'Белое 3', 'Марьино', 'всё, что от ул. Батурина' ),
				'polygon'   => array(),
			),
			array(
				'min_order' => 3000,
				'areas'     => array( 'Белое 4', 'Денисовка' ),
				'polygon'   => array(),
			),
			array(
				'min_order' => 3500,
				'areas'     => array( 'Урожайное', 'Долина от Лозового', 'Фонтаны' ),
				'polygon'   => array(),
			),
			array(
				'min_order' => 4000,
				'areas'     => array( 'Донское', 'Мазанка' ),
				'polygon'   => array(),
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

	/**
	 * Normalize an open-ring polygon as [[lng, lat], ...].
	 * The closing coordinate is generated only for map/GeoJSON rendering.
	 */
	private static function normalize_polygon( $polygon ): array {
		if ( is_string( $polygon ) ) {
			$decoded = json_decode( wp_unslash( $polygon ), true );
			$polygon = is_array( $decoded ) ? $decoded : array();
		}

		if ( isset( $polygon['type'], $polygon['coordinates'] ) && 'Polygon' === $polygon['type'] ) {
			$polygon = is_array( $polygon['coordinates'] ) && isset( $polygon['coordinates'][0] )
				? $polygon['coordinates'][0]
				: array();
		}

		if ( ! is_array( $polygon ) ) {
			return array();
		}

		$points = array();
		foreach ( $polygon as $point ) {
			if ( ! is_array( $point ) || count( $point ) < 2 || ! is_numeric( $point[0] ) || ! is_numeric( $point[1] ) ) {
				continue;
			}

			$lng = (float) $point[0];
			$lat = (float) $point[1];
			if ( $lng < -180 || $lng > 180 || $lat < -90 || $lat > 90 ) {
				continue;
			}

			$points[] = array( round( $lng, 7 ), round( $lat, 7 ) );
			if ( count( $points ) >= self::MAX_POLYGON_VERTICES ) {
				break;
			}
		}

		// Store an open ring. Yandex/GeoJSON rendering closes it at runtime.
		if ( count( $points ) > 1 && $points[0] === $points[ count( $points ) - 1 ] ) {
			array_pop( $points );
		}

		return count( $points ) >= 3 ? $points : array();
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
				'polygon'   => self::normalize_polygon( $row['polygon'] ?? array() ),
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

	public static function yandex_api_key(): string {
		$key = defined( 'ROLLSBAR_YANDEX_MAPS_API_KEY' ) ? (string) ROLLSBAR_YANDEX_MAPS_API_KEY : '';
		return trim( (string) apply_filters( 'rollsbar_yandex_maps_api_key', $key ) );
	}

	public static function enqueue_admin_assets(): void {
		if ( ! is_admin() || 'rollsbar-delivery' !== (string) ( $_GET['page'] ?? '' ) ) { // phpcs:ignore WordPress.Security.NonceVerification.Recommended
			return;
		}

		$key = self::yandex_api_key();
		if ( '' === $key ) {
			return;
		}

		$maps_url = add_query_arg(
			array(
				'apikey' => $key,
				'lang'   => 'ru_RU',
			),
			'https://api-maps.yandex.ru/v3/'
		);

		wp_enqueue_script( 'rollsbar-yandex-maps', $maps_url, array(), null, false );
		wp_enqueue_script(
			'rollsbar-delivery-map-editor',
			plugins_url( 'assets/js/delivery-map-editor.js', ROLLSBAR_CORE_FILE ),
			array( 'rollsbar-yandex-maps' ),
			ROLLSBAR_CORE_VERSION,
			true
		);
		wp_localize_script(
			'rollsbar-delivery-map-editor',
			'RollsBarDeliveryMapConfig',
			array(
				'center'     => array( 34.1003, 44.9521 ),
				'zoom'       => 11,
				'maxVertices'=> self::MAX_POLYGON_VERTICES,
			)
		);
	}

	/**
	 * Resolve a coordinate against accepted/stored polygons.
	 * Returns null while polygons are absent. This helper is intentionally not
	 * wired to checkout enforcement until real client-approved geometry exists.
	 */
	public static function resolve_point( float $lng, float $lat ): ?array {
		foreach ( self::all() as $row ) {
			$polygon = $row['polygon'] ?? array();
			if ( count( $polygon ) < 3 ) {
				continue;
			}
			if ( self::point_in_polygon( $lng, $lat, $polygon ) ) {
				return $row;
			}
		}

		return null;
	}

	private static function point_in_polygon( float $lng, float $lat, array $polygon ): bool {
		$inside = false;
		$count  = count( $polygon );
		$j      = $count - 1;

		for ( $i = 0; $i < $count; $j = $i++ ) {
			$xi = (float) $polygon[ $i ][0];
			$yi = (float) $polygon[ $i ][1];
			$xj = (float) $polygon[ $j ][0];
			$yj = (float) $polygon[ $j ][1];

			if ( ( $yi > $lat ) !== ( $yj > $lat ) ) {
				$denominator = $yj - $yi;
				if ( abs( $denominator ) < 0.0000000001 ) {
					continue;
				}
				$crossing = ( $xj - $xi ) * ( $lat - $yi ) / $denominator + $xi;
				if ( $lng < $crossing ) {
					$inside = ! $inside;
				}
			}
		}

		return $inside;
	}

	public static function render_page(): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}

		$rows       = self::all();
		$key_ready  = '' !== self::yandex_api_key();
		$with_shape = count( array_filter( $rows, static fn( array $row ): bool => count( $row['polygon'] ?? array() ) >= 3 ) );
		?>
		<div class="wrap">
			<h1>Rolls Bar — доставка</h1>
			<p>Здесь хранятся подтверждённые пороги заказа для бесплатной доставки и точные границы зон после их согласования.</p>

			<?php if ( $with_shape < count( $rows ) ) : ?>
				<div class="notice notice-warning inline" style="max-width:1080px;">
					<p><strong>Автоопределение зоны по адресу пока не включено.</strong> Сохранено полигонов: <?php echo esc_html( (string) $with_shape ); ?> из <?php echo esc_html( (string) count( $rows ) ); ?>. Территории из таблицы не используются для угадывания геометрии.</p>
				</div>
			<?php endif; ?>

			<?php if ( ! $key_ready ) : ?>
				<div class="notice notice-info inline" style="max-width:1080px;">
					<p><strong>Редактор карты подготовлен, но Yandex Maps API key ещё не подключён.</strong> Нужен JS API 3.0 key с HTTP Referer restriction для <code>staging.rollsbar.ru</code>. Ключ хранится вне Git в <code>ROLLSBAR_YANDEX_MAPS_API_KEY</code>.</p>
				</div>
			<?php endif; ?>

			<form action="options.php" method="post" id="rollsbar-delivery-form">
				<?php settings_fields( 'rollsbar_delivery_rules_group' ); ?>
				<table class="widefat striped" style="max-width:1080px;margin-top:18px;">
					<thead>
						<tr>
							<th style="width:190px;">Бесплатная доставка от</th>
							<th>Территории</th>
							<th style="width:170px;">Граница</th>
						</tr>
					</thead>
					<tbody>
						<?php foreach ( $rows as $index => $row ) : ?>
							<?php $polygon = $row['polygon'] ?? array(); ?>
							<tr data-rollsbar-zone-row="<?php echo esc_attr( (string) $index ); ?>">
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
								<td>
									<textarea
										class="rollsbar-polygon-field"
										data-zone-index="<?php echo esc_attr( (string) $index ); ?>"
										name="<?php echo esc_attr( self::OPTION ); ?>[<?php echo esc_attr( (string) $index ); ?>][polygon]"
										style="display:none;"
									><?php echo esc_textarea( wp_json_encode( $polygon, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ); ?></textarea>
									<strong class="rollsbar-polygon-status" data-zone-index="<?php echo esc_attr( (string) $index ); ?>">
										<?php echo $polygon ? esc_html( count( $polygon ) . ' точек' ) : 'Не задана'; ?>
									</strong>
								</td>
							</tr>
						<?php endforeach; ?>
					</tbody>
				</table>

				<?php if ( $key_ready ) : ?>
					<div id="rollsbar-delivery-map-editor" style="max-width:1080px;margin:22px 0;padding:18px;background:#fff;border:1px solid #dcdcde;border-radius:4px;">
						<h2 style="margin-top:0;">Редактор границ</h2>
						<p>Выберите тариф, включите редактирование и кликайте по карте для добавления точек. Точки можно перетаскивать; двойной клик удаляет точку. Граница сохранится только после кнопки «Сохранить зоны доставки» ниже.</p>
						<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px;">
							<label><strong>Зона:</strong>
								<select id="rollsbar-map-zone-select">
									<?php foreach ( $rows as $index => $row ) : ?>
										<option value="<?php echo esc_attr( (string) $index ); ?>"><?php echo esc_html( number_format_i18n( (int) $row['min_order'], 0 ) . ' ₽' ); ?></option>
									<?php endforeach; ?>
								</select>
							</label>
							<button type="button" class="button button-primary" id="rollsbar-map-edit-toggle">Редактировать границу</button>
							<button type="button" class="button" id="rollsbar-map-undo">Удалить последнюю точку</button>
							<button type="button" class="button" id="rollsbar-map-clear">Очистить границу</button>
							<span id="rollsbar-map-editor-status" style="font-weight:600;"></span>
						</div>
						<div id="rollsbar-yandex-map" style="height:560px;width:100%;background:#f0f0f1;border:1px solid #c3c4c7;"></div>
					</div>
				<?php endif; ?>

				<?php submit_button( 'Сохранить зоны доставки' ); ?>
			</form>

			<style>
				.rollsbar-map-vertex { width:14px;height:14px;border:2px solid #1d4ed8;border-radius:50%;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.25);transform:translate(-50%,-50%);cursor:grab; }
				.rollsbar-map-vertex:hover { background:#1d4ed8; }
			</style>
		</div>
		<?php
	}
}

<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

get_header();

$categories = array(
	'rolls'    => 'Роллы',
	'pizza'    => 'Пицца',
	'hits'     => 'Хит-меню',
	'combo'    => 'Комбо',
	'sets'     => 'Сеты',
	'baked'    => 'Запечённые',
	'tempura'  => 'Темпура',
	'desserts' => 'Десерты',
	'drinks'   => 'Напитки',
	'snacks'   => 'Закуски',
	'wok'      => 'WOK и рис',
	'soups'    => 'Супы',
);
?>

<nav class="rollsbar-category-nav" aria-label="Категории меню">
	<div class="rollsbar-shell rollsbar-category-nav__scroll">
		<?php foreach ( $categories as $slug => $label ) : ?>
			<a<?php echo 'rolls' === $slug ? ' class="active"' : ''; ?> href="#<?php echo esc_attr( $slug ); ?>"><?php echo esc_html( $label ); ?></a>
		<?php endforeach; ?>
		<button class="rollsbar-category-more__toggle" type="button" aria-expanded="false" aria-controls="rollsbarCategoryMore" data-rollsbar-category-more>
			Ещё
			<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
		</button>
	</div>
	<div class="rollsbar-category-more-popover" id="rollsbarCategoryMore" aria-hidden="true">
		<a href="#delivery">Доставка и оплата</a>
		<a href="<?php echo esc_url( home_url( '/otzyvy/' ) ); ?>">Отзывы клиентов</a>
		<a href="#contacts" data-rollsbar-category-contacts>Контакты</a>
	</div>
</nav>

<?php
$utility_cards = array(
	'promo' => array(
		'eyebrow' => 'Rolls Bar',
		'title'   => 'Акции',
		'text'    => 'Скидки, комбо и специальные предложения',
		'url'     => '#hits',
		'image'   => '',
	),
	'work' => array(
		'eyebrow' => 'Команда',
		'title'   => 'Работа в Rolls Bar',
		'text'    => 'Вакансии и анкета кандидата',
		'url'     => home_url( '/rabota-v-rolls-bar/' ),
		'image'   => '',
	),
	'delivery' => array(
		'eyebrow' => 'Симферополь',
		'title'   => 'Доставка',
		'text'    => 'Зоны, самовывоз и оплата',
		'url'     => '#delivery',
		'image'   => '',
	),
	'reviews' => array(
		'eyebrow' => 'Гости',
		'title'   => 'Отзывы',
		'text'    => 'Что говорят о Rolls Bar',
		'url'     => home_url( '/otzyvy/' ),
		'image'   => '',
	),
);

$promo_posts = get_posts(
	array(
		'post_type'      => 'rb_promo',
		'post_status'    => 'publish',
		'posts_per_page' => 20,
		'orderby'        => array( 'menu_order' => 'ASC', 'date' => 'ASC' ),
	)
);

foreach ( $promo_posts as $promo_post ) {
	$variant = (string) get_post_meta( $promo_post->ID, '_rollsbar_promo_variant', true );

	if ( ! isset( $utility_cards[ $variant ] ) ) {
		continue;
	}

	$eyebrow = trim( (string) get_post_meta( $promo_post->ID, '_rollsbar_promo_eyebrow', true ) );
	$url     = trim( (string) get_post_meta( $promo_post->ID, '_rollsbar_promo_url', true ) );
	$image   = get_the_post_thumbnail_url( $promo_post->ID, 'large' );

	$utility_cards[ $variant ] = array(
		'eyebrow' => $eyebrow ?: $utility_cards[ $variant ]['eyebrow'],
		'title'   => get_the_title( $promo_post ) ?: $utility_cards[ $variant ]['title'],
		'text'    => has_excerpt( $promo_post ) ? get_the_excerpt( $promo_post ) : $utility_cards[ $variant ]['text'],
		'url'     => $url ?: $utility_cards[ $variant ]['url'],
		'image'   => $image ?: '',
	);
}
?>

<section class="rollsbar-utilities">
	<div class="rollsbar-shell rollsbar-utilities__track" aria-label="Полезные разделы Rolls Bar">
		<?php foreach ( $utility_cards as $variant => $card ) : ?>
			<a class="rollsbar-utility rollsbar-utility--<?php echo esc_attr( $variant ); ?>" href="<?php echo esc_url( $card['url'] ); ?>">
				<?php if ( $card['image'] ) : ?>
					<span class="rollsbar-utility__image" style="background-image:url('<?php echo esc_url( $card['image'] ); ?>')" aria-hidden="true"></span>
				<?php elseif ( 'promo' === $variant ) : ?>
					<span class="rollsbar-utility__art" aria-hidden="true"></span>
				<?php elseif ( 'work' === $variant ) : ?>
					<img class="rollsbar-utility__ninja" src="<?php echo esc_url( get_template_directory_uri() . '/assets/images/header-mascot.webp' ); ?>" alt="" aria-hidden="true">
				<?php elseif ( 'delivery' === $variant ) : ?>
					<span class="rollsbar-utility__pin" aria-hidden="true"></span>
				<?php elseif ( 'reviews' === $variant ) : ?>
					<span class="rollsbar-utility__stars" aria-hidden="true">★★★★★</span>
				<?php endif; ?>
				<span class="rollsbar-utility__copy">
					<span class="rollsbar-utility__eyebrow"><?php echo esc_html( $card['eyebrow'] ); ?></span>
					<h3 class="rollsbar-utility__title"><?php echo esc_html( $card['title'] ); ?></h3>
					<p class="rollsbar-utility__text"><?php echo esc_html( $card['text'] ); ?><span class="rollsbar-utility__arrow">→</span></p>
				</span>
			</a>
		<?php endforeach; ?>
	</div>
</section>

<?php if ( ! class_exists( 'WooCommerce' ) ) : ?>
	<section class="rollsbar-shell rollsbar-empty">
		<h1>Rolls Bar</h1>
		<p>WooCommerce ещё не активирован на этом окружении.</p>
	</section>
<?php else : ?>
	<?php
	$source_products = array();
	if ( class_exists( 'RollsBar_Catalog_Importer' ) ) {
		try {
			// Read the packaged source only; never import or update Woo products.
			$source_products = RollsBar_Catalog_Importer::load_catalog()['products'];
		} catch ( RuntimeException $exception ) {
			// Keep the existing catalog available if the source file is unavailable.
		}
	}
	$source_order       = array_flip( array_column( $source_products, 'id' ) );
	$accent_colors     = array(
		'pizza-pepperoni' => 'blue',
		'sets-hit-set'    => 'red',
		'soups-tom-yam'   => 'warm',
	);
	$category_products  = array();
	$products_by_source = array();
	foreach ( $categories as $slug => $label ) {
		$category_products[ $slug ] = wc_get_products(
			array(
				'status'   => 'publish',
				'limit'    => -1,
				'category' => array( $slug ),
				'orderby'  => 'menu_order',
				'order'    => 'ASC',
			)
		);
		foreach ( $category_products[ $slug ] as $product ) {
			$source_id = (string) $product->get_meta( '_rollsbar_source_id', true );
			$products_by_source[ $source_id ] = $product;
		}
		usort(
			$category_products[ $slug ],
			static function ( $a, $b ) use ( $source_order ) {
				return ( $source_order[ $a->get_meta( '_rollsbar_source_id', true ) ] ?? PHP_INT_MAX )
					<=> ( $source_order[ $b->get_meta( '_rollsbar_source_id', true ) ] ?? PHP_INT_MAX );
			}
		);
	}
	if ( $source_products ) {
		$hit_sources = array_slice(
			array_column( array_filter( $source_products, static fn( $row ) => ! empty( $row['hit'] ) ), 'id' ),
			0,
			8
		);
		$category_products['hits'] = array();
		foreach ( $hit_sources as $source_id ) {
			if ( isset( $products_by_source[ $source_id ] ) ) {
				$category_products['hits'][] = $products_by_source[ $source_id ];
			}
		}
	}
	?>
	<?php foreach ( $categories as $slug => $label ) : ?>
		<?php
		$products = $category_products[ $slug ];

		if ( ! $products ) {
			continue;
		}
		?>
		<section class="rollsbar-catalog-section rollsbar-shell" id="<?php echo esc_attr( $slug ); ?>">
			<div class="rollsbar-section-heading">
				<h2><?php echo esc_html( $label ); ?></h2>
			</div>

			<div class="rollsbar-product-grid">
				<?php foreach ( $products as $product ) : ?>
					<?php
					if ( ! $product instanceof WC_Product ) {
						continue;
					}

					$is_variable = $product->is_type( 'variable' );
					$accent = $accent_colors[ $product->get_meta( '_rollsbar_source_id', true ) ] ?? '';
					?>
					<article class="rollsbar-product-card<?php echo $accent ? ' rollsbar-product-card--accent rollsbar-product-card--' . esc_attr( $accent ) : ''; ?>">
						<a class="rollsbar-product-card__media rollsbar-product-media" href="<?php echo esc_url( $product->get_permalink() ); ?>">
							<?php echo rollsbar_product_image_markup( $product ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
						</a>

						<div class="rollsbar-product-card__body">
							<h3><a href="<?php echo esc_url( $product->get_permalink() ); ?>"><?php echo esc_html( $product->get_name() ); ?></a></h3>
							<p><?php echo wp_kses_post( $product->get_short_description() ); ?></p>

							<div class="rollsbar-product-card__footer<?php echo $is_variable ? ' rollsbar-product-card__footer--variable' : ''; ?>">
								<span class="rollsbar-price"><?php echo wp_kses_post( rollsbar_catalog_price_html( $product ) ); ?></span>

								<?php if ( $is_variable ) : ?>
									<a class="rollsbar-product-action rollsbar-product-action--variable" href="<?php echo esc_url( $product->get_permalink() ); ?>" aria-label="<?php echo esc_attr( 'Выбрать вариант: ' . $product->get_name() ); ?>">Выбрать</a>
								<?php else : ?>
									<a
										class="rollsbar-product-action add_to_cart_button ajax_add_to_cart"
										href="<?php echo esc_url( $product->add_to_cart_url() ); ?>"
										data-product_id="<?php echo esc_attr( $product->get_id() ); ?>"
										data-quantity="1"
										rel="nofollow"
									>Добавить</a>
								<?php endif; ?>
							</div>
						</div>
					</article>
				<?php endforeach; ?>
			</div>
		</section>
	<?php endforeach; ?>
<?php endif; ?>

<?php
$delivery_rules = class_exists( 'RollsBar_Delivery_Rules' )
	? RollsBar_Delivery_Rules::all()
	: array();
?>
<section class="rollsbar-delivery rollsbar-shell" id="delivery">
	<div class="rollsbar-delivery__copy">
		<span class="rollsbar-kicker">Доставка</span>
		<h2>Бесплатная доставка от суммы по району</h2>
		<p>Минимальная сумма заказа зависит от территории. Если сумма заказа ниже порога, нужно добрать товары до указанной суммы.</p>
	</div>

	<?php if ( $delivery_rules ) : ?>
		<div class="rollsbar-delivery-rules" aria-label="Минимальные суммы бесплатной доставки">
			<?php foreach ( $delivery_rules as $rule ) : ?>
				<article class="rollsbar-delivery-rule">
					<div class="rollsbar-delivery-rule__amount">
						<span>Бесплатно от</span>
						<strong><?php echo esc_html( number_format_i18n( (int) $rule['min_order'], 0 ) ); ?> ₽</strong>
					</div>
					<p><?php echo esc_html( implode( ' · ', $rule['areas'] ) ); ?></p>
				</article>
			<?php endforeach; ?>
		</div>
	<?php endif; ?>

	<div class="rollsbar-delivery__pending">
		<strong>Автоопределение по адресу</strong>
		<span>Подключим после утверждения точных границ зон на карте. Ручного выбора зоны клиентом не будет.</span>
	</div>
</section>

<?php
get_footer();

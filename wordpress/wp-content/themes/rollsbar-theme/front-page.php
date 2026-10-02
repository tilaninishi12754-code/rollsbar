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
	<div class="rollsbar-shell rollsbar-utilities__track">
		<?php foreach ( $utility_cards as $variant => $card ) : ?>
			<a class="rollsbar-utility rollsbar-utility--<?php echo esc_attr( $variant ); ?>" href="<?php echo esc_url( $card['url'] ); ?>">
				<?php if ( $card['image'] ) : ?>
					<span class="rollsbar-utility__image" style="background-image:url('<?php echo esc_url( $card['image'] ); ?>')" aria-hidden="true"></span>
				<?php endif; ?>
				<span class="rollsbar-utility__eyebrow"><?php echo esc_html( $card['eyebrow'] ); ?></span>
				<strong><?php echo esc_html( $card['title'] ); ?></strong>
				<span><?php echo esc_html( $card['text'] ); ?> →</span>
			</a>
		<?php endforeach; ?>
	</div>
</section>

<nav class="rollsbar-category-nav" aria-label="Категории меню">
	<div class="rollsbar-shell rollsbar-category-nav__scroll">
		<?php foreach ( $categories as $slug => $label ) : ?>
			<a href="#<?php echo esc_attr( $slug ); ?>"><?php echo esc_html( $label ); ?></a>
		<?php endforeach; ?>
	</div>
</nav>

<?php if ( ! class_exists( 'WooCommerce' ) ) : ?>
	<section class="rollsbar-shell rollsbar-empty">
		<h1>Rolls Bar</h1>
		<p>WooCommerce ещё не активирован на этом окружении.</p>
	</section>
<?php else : ?>
	<?php foreach ( $categories as $slug => $label ) : ?>
		<?php
		$products = wc_get_products(
			array(
				'status'   => 'publish',
				'limit'    => -1,
				'category' => array( $slug ),
				'orderby'  => 'menu_order',
				'order'    => 'ASC',
			)
		);

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

					$image_url = rollsbar_product_image_url( $product );
					$is_variable = $product->is_type( 'variable' );
					?>
					<article class="rollsbar-product-card">
						<a class="rollsbar-product-card__media" href="<?php echo esc_url( $product->get_permalink() ); ?>">
							<img src="<?php echo esc_url( $image_url ); ?>" alt="<?php echo esc_attr( $product->get_name() ); ?>" loading="lazy">
						</a>

						<div class="rollsbar-product-card__body">
							<h3><a href="<?php echo esc_url( $product->get_permalink() ); ?>"><?php echo esc_html( $product->get_name() ); ?></a></h3>
							<?php if ( $product->get_short_description() ) : ?>
								<p><?php echo wp_kses_post( wp_trim_words( $product->get_short_description(), 22 ) ); ?></p>
							<?php endif; ?>

							<div class="rollsbar-product-card__footer">
								<span class="rollsbar-price"><?php echo wp_kses_post( $product->get_price_html() ); ?></span>

								<?php if ( $is_variable ) : ?>
									<a class="rollsbar-product-action" href="<?php echo esc_url( $product->get_permalink() ); ?>">Выбрать</a>
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

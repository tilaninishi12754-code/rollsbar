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

<section class="rollsbar-utilities">
	<div class="rollsbar-shell rollsbar-utilities__track">
		<a class="rollsbar-utility rollsbar-utility--promo" href="#hits">
			<span class="rollsbar-utility__eyebrow">Rolls Bar</span>
			<strong>Акции</strong>
			<span>Скидки, комбо и специальные предложения →</span>
		</a>
		<a class="rollsbar-utility rollsbar-utility--work" href="<?php echo esc_url( home_url( '/rabota-v-rolls-bar/' ) ); ?>">
			<span class="rollsbar-utility__eyebrow">Команда</span>
			<strong>Работа в Rolls Bar</strong>
			<span>Вакансии и анкета кандидата →</span>
		</a>
		<a class="rollsbar-utility rollsbar-utility--delivery" href="#delivery">
			<span class="rollsbar-utility__eyebrow">Симферополь</span>
			<strong>Доставка</strong>
			<span>Зоны, самовывоз и оплата →</span>
		</a>
		<a class="rollsbar-utility rollsbar-utility--reviews" href="<?php echo esc_url( home_url( '/otzyvy/' ) ); ?>">
			<span class="rollsbar-utility__eyebrow">Гости</span>
			<strong>Отзывы</strong>
			<span>Что говорят о Rolls Bar →</span>
		</a>
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

<section class="rollsbar-delivery rollsbar-shell" id="delivery">
	<div class="rollsbar-delivery__copy">
		<span class="rollsbar-kicker">Доставка</span>
		<h2>Зона будет определяться по адресу</h2>
		<p>В WordPress переносится утверждённая логика: ручного выбора зоны нет. Реальные полигоны и минимальные суммы подключаются после получения данных заказчика.</p>
	</div>
	<div class="rollsbar-delivery__pending">
		<strong>Pending input</strong>
		<span>Границы зон · минималки · стоимость доставки · обязательность адресных полей</span>
	</div>
</section>

<?php
get_footer();

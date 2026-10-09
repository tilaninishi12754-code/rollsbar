<?php
/**
 * Template for /rabota-v-rolls-bar/.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

get_header();

$vacancies = get_posts(
	array(
		'post_type'      => 'rb_vacancy',
		'post_status'    => 'publish',
		'posts_per_page' => -1,
		'orderby'        => array( 'menu_order' => 'ASC', 'date' => 'DESC' ),
	)
);

$phone_display = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'phone_display', '+7 978 688-22-88' ) : '+7 978 688-22-88';
$phone_href    = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'phone_href', '+79786882288' ) : '+79786882288';
$telegram_url  = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'telegram_url', 'https://telegram.me/rollsbar82' ) : 'https://telegram.me/rollsbar82';
$vk_url        = function_exists( 'rollsbar_setting' ) ? rollsbar_setting( 'vk_url', 'https://vk.ru/rollsbar82' ) : 'https://vk.ru/rollsbar82';
?>

<section class="rb-career-hero">
	<div class="rollsbar-shell rb-career-hero__inner">
		<h1>Присоединяйся<br>к команде Rolls Bar</h1>
		<p>Актуальные вакансии управляются через админку WordPress: заказчик может добавлять и убирать позиции, не меняя дизайн страницы.</p>

		<div class="rb-career-art" aria-hidden="true">
			<div class="rb-career-arc">и всё закрутится</div>
			<div class="rb-career-circle"><span>ROLLS BAR</span></div>
		</div>
	</div>

	<div class="rb-career-tabs" data-rb-vacancy-tabs>
		<button class="active" type="button" data-area="all">Все</button>
		<button type="button" data-area="kitchen">Кухня и касса</button>
		<button type="button" data-area="delivery">Доставка</button>
	</div>
</section>

<section class="rollsbar-shell rb-career-section" id="vacancies">
	<h2>Актуальные вакансии</h2>

	<div class="rb-vacancy-list">
		<?php if ( $vacancies ) : ?>
			<?php foreach ( $vacancies as $vacancy ) : ?>
				<?php
				$area = (string) get_post_meta( $vacancy->ID, '_rollsbar_vacancy_area', true );
				if ( ! in_array( $area, array( 'kitchen', 'delivery', 'other' ), true ) ) {
					$area = 'other';
				}
				$summary = has_excerpt( $vacancy )
					? get_the_excerpt( $vacancy )
					: wp_trim_words( wp_strip_all_tags( $vacancy->post_content ), 28 );
				?>
				<article class="rb-vacancy-card" data-vacancy-area="<?php echo esc_attr( $area ); ?>">
					<h3><?php echo esc_html( get_the_title( $vacancy ) ); ?></h3>
					<?php if ( $summary ) : ?>
						<p><?php echo esc_html( $summary ); ?></p>
					<?php endif; ?>
					<?php if ( trim( (string) $vacancy->post_content ) ) : ?>
						<details>
							<summary>Подробнее</summary>
							<div class="rb-vacancy-card__details"><?php echo wp_kses_post( wpautop( $vacancy->post_content ) ); ?></div>
						</details>
					<?php endif; ?>
				</article>
			<?php endforeach; ?>
		<?php else : ?>
			<article class="rb-vacancy-card rb-vacancy-card--empty">
				<h3>Сейчас активных вакансий нет</h3>
				<p>Когда заказчик опубликует вакансию в разделе Rolls Bar → Вакансии, она появится здесь автоматически.</p>
			</article>
		<?php endif; ?>
	</div>
</section>

<?php
/*
 * Final questionnaire wording and receiving channel are a documented pending
 * client input. Fail closed: do not expose a technical placeholder, invented
 * questions or a dead application CTA on the public site. Existing approved
 * contact routes remain available below. The real questionnaire can be added
 * later without changing the vacancy content model or page layout contract.
 */
?>

<nav class="rb-career-actions rb-career-actions--contacts-only" aria-label="Связаться по вакансии">
	<button class="rb-career-actions__round" type="button" data-rb-career-chat aria-label="Написать">💬</button>
	<a class="rb-career-actions__round" href="tel:<?php echo esc_attr( $phone_href ); ?>" aria-label="Позвонить">☎</a>
</nav>

<div class="rb-career-chat" data-rb-career-chat-modal aria-hidden="true">
	<button class="rb-career-chat__backdrop" type="button" data-rb-career-chat-close aria-label="Закрыть"></button>
	<section class="rb-career-chat__panel" role="dialog" aria-modal="true" aria-label="Связаться с Rolls Bar">
		<h3>Связаться с Rolls Bar</h3>
		<p>Пока один приоритетный канал по вакансиям не утверждён, показываем уже используемые контакты.</p>
		<div class="rb-career-chat__links">
			<?php if ( $telegram_url ) : ?><a href="<?php echo esc_url( $telegram_url ); ?>" target="_blank" rel="noopener">Telegram</a><?php endif; ?>
			<?php if ( $vk_url ) : ?><a href="<?php echo esc_url( $vk_url ); ?>" target="_blank" rel="noopener">VK</a><?php endif; ?>
			<a href="tel:<?php echo esc_attr( $phone_href ); ?>"><?php echo esc_html( $phone_display ); ?></a>
		</div>
		<button type="button" class="rb-career-chat__close" data-rb-career-chat-close>Закрыть</button>
	</section>
</div>

<?php
get_footer();

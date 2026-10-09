<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

get_header();

$reviews = get_posts(
	array(
		'post_type'      => 'rb_review',
		'post_status'    => 'publish',
		'posts_per_page' => 50,
		'orderby'        => 'date',
		'order'          => 'DESC',
	)
);

$rating_sum = 0;
$rating_count = 0;
foreach ( $reviews as $review ) {
	$rating = absint( get_post_meta( $review->ID, '_rollsbar_review_rating', true ) );
	if ( $rating >= 1 && $rating <= 5 ) {
		$rating_sum += $rating;
		++$rating_count;
	}
}
$average_rating = $rating_count ? round( $rating_sum / $rating_count, 1 ) : 0;
$submission_status = isset( $_GET['review'] ) ? sanitize_key( wp_unslash( $_GET['review'] ) ) : '';
?>

<style>
.rb-reviews-page{padding:34px 0 72px}.rb-reviews-hero{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;align-items:stretch}.rb-review-hero-card,.rb-review-sources,.rb-review-form,.rb-review-feed{border:1px solid var(--rb-line);border-radius:26px;background:#fff;box-shadow:0 14px 36px rgba(0,0,0,.055)}.rb-review-hero-card{padding:28px;background:linear-gradient(135deg,#fff 0%,#fff3f1 100%)}.rb-review-eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--rb-red);font-weight:900}.rb-review-hero-card h1{font-size:42px;line-height:.98;letter-spacing:-.055em;margin:9px 0 14px}.rb-review-hero-card p{margin:0;color:var(--rb-muted);font-size:14px;line-height:1.55;max-width:620px}.rb-review-rating-box{display:flex;align-items:end;gap:12px;margin-top:24px}.rb-review-rating-number{font-size:48px;line-height:.9;font-weight:950;letter-spacing:-.06em}.rb-review-stars{color:#ffb21a;letter-spacing:2px;font-size:18px}.rb-review-rating-note{font-size:11px;color:var(--rb-muted);margin-top:5px}.rb-review-sources{padding:22px}.rb-review-sources h2,.rb-review-feed h2,.rb-review-form h2{font-size:23px;letter-spacing:-.04em;margin:0 0 14px}.rb-review-source-link{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px;border:1px solid var(--rb-line);border-radius:15px;text-decoration:none;margin-top:9px}.rb-review-source-link div{display:grid;gap:3px}.rb-review-source-link b{font-size:14px}.rb-review-source-link span{font-size:12px;color:var(--rb-muted)}.rb-review-source-link em{font-style:normal;color:var(--rb-red);font-weight:900}.rb-reviews-layout{display:grid;grid-template-columns:1fr 400px;gap:18px;margin-top:18px}.rb-review-feed{padding:24px}.rb-review-empty{padding:38px 18px;text-align:center;border-radius:18px;background:var(--rb-soft);color:var(--rb-muted);font-size:13px;line-height:1.5}.rb-review-list{display:grid;gap:12px}.rb-review-card{border:1px solid var(--rb-line);border-radius:18px;padding:18px}.rb-review-card__top{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.rb-review-card h3{margin:0;font-size:16px}.rb-review-card__stars{color:#ffb21a;letter-spacing:1px;white-space:nowrap}.rb-review-card__date{font-size:10px;color:var(--rb-muted);margin-top:4px}.rb-review-card__text{margin:12px 0 0;color:#3f3f3f;line-height:1.55;font-size:14px;white-space:pre-line}.rb-review-card__photo{margin-top:14px;border-radius:14px;overflow:hidden;max-height:360px}.rb-review-card__photo img{width:100%;height:100%;object-fit:cover}.rb-review-form{padding:24px;align-self:start}.rb-review-field{margin-top:12px}.rb-review-field label{display:block;font-size:11px;font-weight:850;color:#666;margin:0 0 6px}.rb-review-field input,.rb-review-field textarea,.rb-review-field select{width:100%;border:1px solid var(--rb-line);border-radius:13px;padding:12px 13px;outline:none;background:#fff;font:inherit}.rb-review-field textarea{min-height:120px;resize:vertical}.rb-review-submit{width:100%;border:0;border-radius:14px;background:var(--rb-red);color:#fff;font-weight:900;padding:14px;margin-top:14px;cursor:pointer}.rb-review-message{margin-bottom:14px;border-radius:13px;padding:12px;font-size:12px;line-height:1.45}.rb-review-message--success{background:#eef9f2;color:#28533a}.rb-review-message--error{background:#fff1f1;color:#7c2d2d}.rb-review-moderation{margin-top:10px;color:var(--rb-muted);font-size:10px;line-height:1.4}.rb-review-honeypot{position:absolute!important;left:-10000px!important;width:1px!important;height:1px!important;overflow:hidden!important}.rb-review-back{display:inline-flex;margin-bottom:16px;text-decoration:none;font-size:13px;font-weight:850;padding:10px 13px;border-radius:12px;background:var(--rb-soft)}
@media(max-width:780px){.rb-reviews-hero,.rb-reviews-layout{grid-template-columns:1fr}.rb-review-hero-card h1{font-size:34px}.rb-review-hero-card,.rb-review-sources,.rb-review-feed,.rb-review-form{border-radius:20px}.rb-review-rating-number{font-size:42px}}
</style>

<section class="rb-reviews-page rollsbar-shell">
	<a class="rb-review-back" href="<?php echo esc_url( home_url( '/' ) ); ?>">← Вернуться в меню</a>

	<div class="rb-reviews-hero">
		<article class="rb-review-hero-card">
			<div class="rb-review-eyebrow">Отзывы клиентов</div>
			<h1>Нам важно, что вы думаете о заказе</h1>
			<p>Здесь можно посмотреть опубликованные отзывы гостей и оставить отзыв непосредственно на сайте. Новый отзыв появится публично только после проверки администратором.</p>

			<div class="rb-review-rating-box">
				<?php if ( $rating_count ) : ?>
					<div>
						<div class="rb-review-rating-number"><?php echo esc_html( number_format_i18n( $average_rating, 1 ) ); ?></div>
						<div class="rb-review-rating-note">из 5 · опубликовано отзывов: <?php echo esc_html( (string) $rating_count ); ?></div>
					</div>
					<div>
						<div class="rb-review-stars" aria-label="Средняя оценка <?php echo esc_attr( (string) $average_rating ); ?> из 5">★★★★★</div>
						<div class="rb-review-rating-note">Оценка рассчитана только по опубликованным отзывам с сайта</div>
					</div>
				<?php else : ?>
					<div>
						<div class="rb-review-rating-number">—</div>
						<div class="rb-review-rating-note">Пока нет опубликованных отзывов с сайта</div>
					</div>
				<?php endif; ?>
			</div>
		</article>

		<aside class="rb-review-sources">
			<h2>Отзывы в сервисах</h2>
			<a class="rb-review-source-link" href="https://yandex.ru/profile/229692973623?lang=ru" target="_blank" rel="noopener noreferrer">
				<div><b>Яндекс Карты</b><span>Открыть карточку Rolls Bar</span></div><em>↗</em>
			</a>
			<a class="rb-review-source-link" href="https://2gis.ru/simferopol/search/Rolls%20bar" target="_blank" rel="noopener noreferrer">
				<div><b>2ГИС</b><span>Посмотреть оценки и отзывы</span></div><em>↗</em>
			</a>
		</aside>
	</div>

	<div class="rb-reviews-layout">
		<article class="rb-review-feed">
			<h2>Отзывы с сайта</h2>
			<?php if ( ! $reviews ) : ?>
				<div class="rb-review-empty">Здесь будут опубликованы отзывы, прошедшие модерацию. Мы не добавляем вымышленные отзывы клиентов.</div>
			<?php else : ?>
				<div class="rb-review-list">
					<?php foreach ( $reviews as $review ) : ?>
						<?php
						$rating = max( 1, min( 5, absint( get_post_meta( $review->ID, '_rollsbar_review_rating', true ) ) ) );
						$stars = str_repeat( '★', $rating ) . str_repeat( '☆', 5 - $rating );
						$image = get_the_post_thumbnail_url( $review->ID, 'large' );
						?>
						<section class="rb-review-card">
							<div class="rb-review-card__top">
								<div>
									<h3><?php echo esc_html( get_the_title( $review ) ); ?></h3>
									<div class="rb-review-card__date"><?php echo esc_html( get_the_date( 'd.m.Y', $review ) ); ?></div>
								</div>
								<div class="rb-review-card__stars" aria-label="Оценка <?php echo esc_attr( (string) $rating ); ?> из 5"><?php echo esc_html( $stars ); ?></div>
							</div>
							<div class="rb-review-card__text"><?php echo esc_html( $review->post_content ); ?></div>
							<?php if ( $image ) : ?>
								<div class="rb-review-card__photo"><img src="<?php echo esc_url( $image ); ?>" alt="Фото к отзыву <?php echo esc_attr( get_the_title( $review ) ); ?>" loading="lazy"></div>
							<?php endif; ?>
						</section>
					<?php endforeach; ?>
				</div>
			<?php endif; ?>
		</article>

		<aside class="rb-review-form">
			<h2>Оставить отзыв</h2>

			<?php if ( 'received' === $submission_status ) : ?>
				<div class="rb-review-message rb-review-message--success" role="status">Спасибо! Отзыв сохранён со статусом «На модерации». После проверки администратором он сможет быть опубликован.</div>
			<?php elseif ( in_array( $submission_status, array( 'invalid', 'error' ), true ) ) : ?>
				<div class="rb-review-message rb-review-message--error" role="alert">Не удалось сохранить отзыв. Проверьте имя, оценку и текст и попробуйте ещё раз.</div>
			<?php endif; ?>

			<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" enctype="multipart/form-data">
				<input type="hidden" name="action" value="rollsbar_submit_review">
				<?php wp_nonce_field( 'rollsbar_submit_review', 'rollsbar_review_nonce' ); ?>
				<div class="rb-review-honeypot" aria-hidden="true">
					<label for="rbReviewWebsite">Сайт</label><input id="rbReviewWebsite" name="website" type="text" tabindex="-1" autocomplete="off">
				</div>
				<div class="rb-review-field"><label for="rbReviewName">Имя</label><input id="rbReviewName" name="name" required maxlength="80" autocomplete="name" placeholder="Ваше имя"></div>
				<div class="rb-review-field"><label for="rbReviewRating">Оценка</label><select id="rbReviewRating" name="rating" required><option value="5">5 — отлично</option><option value="4">4 — хорошо</option><option value="3">3 — нормально</option><option value="2">2 — есть замечания</option><option value="1">1 — плохо</option></select></div>
				<div class="rb-review-field"><label for="rbReviewText">Текст отзыва</label><textarea id="rbReviewText" name="text" required maxlength="4000" placeholder="Расскажите о заказе"></textarea></div>
				<div class="rb-review-field"><label for="rbReviewPhoto">Фото заказа <span aria-hidden="true">·</span> до 5 МБ</label><input id="rbReviewPhoto" name="photo" type="file" accept="image/jpeg,image/png,image/webp,image/gif"></div>
				<button class="rb-review-submit" type="submit">Отправить на модерацию</button>
				<div class="rb-review-moderation">Публикация — только после подтверждения администратором Rolls Bar. До модерации отзыв не виден другим посетителям.</div>
			</form>
		</aside>
	</div>
</section>

<?php
get_footer();

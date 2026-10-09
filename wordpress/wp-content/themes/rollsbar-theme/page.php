<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

get_header();
?>

<section class="rollsbar-legal-page">
	<div class="rollsbar-shell">
		<a class="rollsbar-legal-page__back" href="<?php echo esc_url( home_url( '/' ) ); ?>">← Вернуться в меню</a>
		<?php while ( have_posts() ) : ?>
			<?php the_post(); ?>
			<article class="rollsbar-legal-page__content">
				<?php the_content(); ?>
			</article>
		<?php endwhile; ?>
	</div>
</section>

<?php
get_footer();

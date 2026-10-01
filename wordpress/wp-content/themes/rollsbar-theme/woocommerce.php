<?php
/**
 * WooCommerce wrapper template.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

get_header();
?>
<section class="rollsbar-shell rollsbar-woocommerce">
	<?php woocommerce_content(); ?>
</section>
<?php
get_footer();

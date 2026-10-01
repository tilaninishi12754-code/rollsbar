<?php
/**
 * Plugin Name: Rolls Bar Core
 * Description: Business logic for Rolls Bar: delivery zones, checkout fields, minimum order rules, catalog behavior and integrations.
 * Version: 0.1.0
 * Author: Rolls Bar project
 * Requires at least: 6.6
 * Requires PHP: 8.1
 * WC requires at least: 9.0
 * Text Domain: rollsbar-core
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'ROLLSBAR_CORE_VERSION', '0.1.0' );
define( 'ROLLSBAR_CORE_FILE', __FILE__ );
define( 'ROLLSBAR_CORE_DIR', plugin_dir_path( __FILE__ ) );

require_once ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-core.php';
require_once ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-catalog-importer.php';
require_once ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-settings.php';
require_once ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-content-types.php';
require_once ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-product-fields.php';
require_once ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-seo.php';
require_once ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-checkout.php';
require_once ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-order-details.php';
require_once ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-notifications.php';

RollsBar_Settings::init();
RollsBar_Content_Types::init();
RollsBar_Product_Fields::init();
RollsBar_SEO::init();
RollsBar_Checkout::init();
RollsBar_Order_Details::init();
RollsBar_Notifications::init();

RollsBar_Catalog_Importer::register_cli();

add_action(
	'plugins_loaded',
	static function () {
		if ( ! class_exists( 'WooCommerce' ) ) {
			return;
		}

		RollsBar_Core::instance();
	}
);

<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class RollsBar_Core {

	private static ?RollsBar_Core $instance = null;

	/** Preserve staging behavior and enable the accepted checkout on its live site. */
	public static function checkout_runtime_enabled(): bool {
		$environment = wp_get_environment_type();
		if ( 'staging' === $environment ) {
			return true;
		}
		return 'production' === $environment
			&& 'rollsbar.ru' === strtolower( (string) wp_parse_url( home_url( '/' ), PHP_URL_HOST ) );
	}

	public static function instance(): RollsBar_Core {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}

		return self::$instance;
	}

	private function __construct() {
		$this->register_hooks();
	}

	private function register_hooks(): void {
		// Intentionally minimal.
		// Delivery zones, checkout fields, minimum-order logic and integrations
		// will be added as separately testable modules instead of being mixed
		// into the theme.
	}
}

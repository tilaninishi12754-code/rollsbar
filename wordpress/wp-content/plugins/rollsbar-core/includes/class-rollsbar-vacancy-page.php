<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Ensure the canonical public vacancy page exists.
 *
 * Final questionnaire wording/channel remain a documented client input and are
 * intentionally not created here. This class only provisions the approved
 * WordPress page shell required by page-rabota-v-rolls-bar.php.
 */
final class RollsBar_Vacancy_Page {

	private const PAGE_OPTION = 'rollsbar_vacancy_page_id';
	private const PAGE_SLUG   = 'rabota-v-rolls-bar';

	public static function init(): void {
		add_action( 'init', array( __CLASS__, 'maybe_provision_page' ), 35 );
	}

	public static function maybe_provision_page(): void {
		if ( wp_installing() ) {
			return;
		}

		$known_id = absint( get_option( self::PAGE_OPTION, 0 ) );
		if ( $known_id && 'page' === get_post_type( $known_id ) && 'trash' !== get_post_status( $known_id ) ) {
			return;
		}

		$existing = get_page_by_path( self::PAGE_SLUG, OBJECT, 'page' );
		if ( $existing instanceof WP_Post && 'trash' !== $existing->post_status ) {
			update_option( self::PAGE_OPTION, $existing->ID, false );
			return;
		}

		$page_id = wp_insert_post(
			array(
				'post_type'      => 'page',
				'post_status'    => 'publish',
				'post_title'     => 'Работа в Rolls Bar',
				'post_name'      => self::PAGE_SLUG,
				'post_content'   => '',
				'comment_status' => 'closed',
				'ping_status'    => 'closed',
			),
			true
		);

		if ( ! is_wp_error( $page_id ) ) {
			update_option( self::PAGE_OPTION, (int) $page_id, false );
		}
	}
}

<?php
/** Manual WP-CLI eval-file entrypoint. No bootstrap/workflow registration. */
if ( ! defined( 'ABSPATH' ) || ! defined( 'WP_CLI' ) || ! WP_CLI ) { exit( 1 ); }
require_once __DIR__ . '/shrimp-options-repair.php';
try {
	global $wpdb;
	if ( ! is_object( $wpdb ) || ! is_callable( array( $wpdb, 'prepare' ) ) || ! is_callable( array( $wpdb, 'get_results' ) ) || ! is_callable( array( $wpdb, 'query' ) ) ) { throw new RuntimeException( 'REFUSE: usable WordPress database handle required.' ); }
	$mode = (string) getenv( 'ROLLSBAR_SHRIMP_REPAIR_MODE' );
	if ( ! in_array( $mode, array( '', 'dry-run', 'apply' ), true ) ) { throw new RuntimeException( 'REFUSE: mode must be dry-run or apply.' ); }
	$result = ( new RollsBar_Shrimp_Options_Repair( $wpdb ) )->run( 'apply' === $mode, array(
		'environment' => wp_get_environment_type(),
		'home' => (string) get_option( 'home' ),
		'siteurl' => (string) get_option( 'siteurl' ),
		'blog_public' => get_option( 'blog_public' ),
		'confirmation' => (string) getenv( 'ROLLSBAR_CONFIRM_SHRIMP_OPTIONS' ),
		'backup_verified' => (string) getenv( 'ROLLSBAR_FRESH_BACKUP_VERIFIED' ),
		'backup_snapshot' => (string) getenv( 'ROLLSBAR_FRESH_BACKUP_SNAPSHOT' ),
	) );
	echo json_encode( $result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR ) . "\n";
} catch ( Throwable $error ) {
	fwrite( STDERR, $error->getMessage() . "\n" );
	exit( 1 );
}

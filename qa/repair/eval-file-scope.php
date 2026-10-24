<?php
/** Local-only function-scope entrypoint execution; no WordPress installation/DB. */
define( 'ROLLSBAR_SCOPE_FIXTURE', true );
require __DIR__ . '/shrimp-contract.php';
define( 'ABSPATH', __DIR__ );
define( 'WP_CLI', true );
function add_action( ...$args ) {}
function add_filter( ...$args ) {}
function has_term( ...$args ) { return false; }
require dirname( __DIR__, 2 ) . '/wordpress/wp-content/themes/rollsbar-theme/functions.php';

// Keep real repair SQL, with strict verifier identity-query dispatch as well.
final class ScopeDatabase {
	public $postmeta = 'wp_postmeta';
	public RepairDatabase $inner;
	public array $lookups = array(), $prepared = array();
	public function __construct( $state ) { $this->inner = new RepairDatabase( $state ); }
	public function __get( $key ) { return $this->inner->$key; }
	public function prepare( $sql, ...$args ) {
		$token = $this->inner->prepare( $sql, ...$args );
		$this->prepared[$token] = array( $sql, $args );
		return $token;
	}
	public function get_results( $sql, $format ) { return $this->inner->get_results( $sql, $format ); }
	public function query( $sql ) { return $this->inner->query( $sql ); }
	public function get_col( $token ) {
		[ $sql, $args ] = $this->prepared[$token];
		expect_repair( 'SELECT post_id FROM wp_postmeta WHERE meta_key=%s AND BINARY meta_value=BINARY %s' === $sql, 'Exact verifier SQL' );
		expect_repair( '_rollsbar_source_id' === $args[0], 'Verifier source identity key' );
		$this->lookups[] = $args[1];
		return array_column( array_values( array_filter( $this->inner->store['meta'], static fn( $m ) => $m['meta_key'] === $args[0] && $m['meta_value'] === $args[1] ) ), 'post_id' );
	}
}
class WC_Product {
	public function __construct( public int $id, public array $row, public array $meta ) {}
	public function get_id() { return $this->id; }
	public function get_name() { return $this->row['name']; }
	public function get_meta( $key, ...$args ) { return $this->meta[$key] ?? ''; }
	public function get_catalog_visibility() { return 'visible'; }
	public function is_type( $type ) { return $type === ( isset( $this->row['variants'] ) ? 'variable' : 'simple' ); }
	public function get_children() { return array_keys( $this->row['variants'] ?? array() ); }
}
function wc_get_products( $args ) {
	expect_repair( array( 'status' => 'publish', 'visibility' => 'visible', 'limit' => -1 ) === $args, 'Real verifier catalog request' );
	return $GLOBALS['scope_products'];
}
function wc_get_product( $id ) {
	foreach ( $GLOBALS['scope_products'] as $product ) { if ( $product->get_id() === $id ) { return $product; } }
	return false;
}

$entrypoint = $argv[1];
$is_repair = 'repair-staging-shrimp-options.php' === basename( $entrypoint );
foreach ( array( 'ROLLSBAR_SHRIMP_REPAIR_MODE', 'ROLLSBAR_CONFIRM_SHRIMP_OPTIONS', 'ROLLSBAR_FRESH_BACKUP_VERIFIED', 'ROLLSBAR_FRESH_BACKUP_SNAPSHOT' ) as $key ) { putenv( $key ); }
$GLOBALS['wpdb'] = new ScopeDatabase( $is_repair ? 'pending' : 'canonical' );
$baseline = $GLOBALS['wpdb']->inner->store;
$scope_products = array();
$catalog = json_decode( file_get_contents( dirname( __DIR__, 2 ) . '/wordpress/data/catalog.json' ), true )['products'];
foreach ( $GLOBALS['wpdb']->inner->store['posts'] as $id => $post ) {
	$meta = array_column( array_values( array_filter( $baseline['meta'], static fn( $m ) => (int) $m['post_id'] === $id ) ), 'meta_value', 'meta_key' );
	$row = array_values( array_filter( $catalog, static fn( $r ) => $r['id'] === $meta['_rollsbar_source_id'] ) )[0];
	$scope_products[] = new WC_Product( $id, $row, $meta );
}
if ( 'missing' === ( $argv[2] ?? '' ) ) { unset( $GLOBALS['wpdb'] ); }
if ( 'invalid' === ( $argv[2] ?? '' ) ) { $GLOBALS['wpdb'] = new stdClass(); }

// The entrypoint receives a filename ONLY. No capture, extract(), global import,
// or local $wpdb injection. An include inherits this function's local scope,
// just as eval-file's function-scoped eval does; __DIR__ stays the real path.
( static function ( string $entrypoint ): void {
	expect_repair( ! array_key_exists( 'wpdb', get_defined_vars() ), 'No local DB injection' );
	expect_repair( isset( $GLOBALS['wpdb'] ) || 'missing' === ( $GLOBALS['argv'][2] ?? '' ), 'Global DB available before entrypoint' );
	require $entrypoint;
} )( $entrypoint );

expect_repair( $baseline === $GLOBALS['wpdb']->inner->store && 0 === $GLOBALS['wpdb']->inner->writes, 'Scope proof must never mutate fixture data' );
if ( $is_repair ) {
	expect_repair( count( $GLOBALS['wpdb']->inner->statements ) > 5, 'Actual repair object executed SQL' );
	expect_repair( 'ROLLBACK' === end( $GLOBALS['wpdb']->inner->statements ), 'Default dry-run rolls back' );
} else {
	expect_repair( array( 'shrimp-tempura', 'upsell-soy-sauce', 'upsell-ginger', 'upsell-wasabi' ) === $GLOBALS['wpdb']->lookups, 'All four verifier DB identity queries executed' );
}
echo "FUNCTION_SCOPE_PASS writes=0\n";

<?php
/** Deterministic full-store adapter. Unknown SQL fails; never connects to a DB. */
define( 'ARRAY_A', 'ARRAY_A' );
require dirname( __DIR__, 2 ) . '/wordpress/deploy/shrimp-options-repair.php';
$checks = 0;
function expect_repair( $ok, string $message ): void { global $checks; if ( ! $ok ) { throw new RuntimeException( $message ); } ++$checks; }
class WC_Data {
	public static function generate_meta_cache_key( $id, $group ) { expect_repair( 1 === $id && 'products' === $group, 'Woo cache key scope' ); return 'fixture-woo-meta-' . $id; }
}
function wp_cache_delete( $id, $group ) { expect_repair( ( 1 === $id && 'post_meta' === $group ) || ( 'fixture-woo-meta-1' === $id && 'products' === $group ), 'Cache invalidation scope' ); }
final class RepairDatabase {
	public $posts = 'wp_posts', $postmeta = 'wp_postmeta', $term_relationships = 'wp_term_relationships', $last_error = '';
	public array $store, $statements = array();
	public int $writes = 0;
	public string $fault = '';
	private array $prepared = array(), $saved = array();
	public function __construct( string $state ) {
		$catalog = json_decode( file_get_contents( dirname( __DIR__, 2 ) . '/wordpress/data/catalog.json' ), true );
		$rows = $catalog['products'];
		usort( $rows, static fn( $a, $b ) => ( 'shrimp-tempura' === $a['id'] ? -1 : ( 'shrimp-tempura' === $b['id'] ? 1 : strcmp( $a['id'], $b['id'] ) ) ) );
		$this->store = array( 'posts' => array(), 'meta' => array(), 'terms' => array(), 'children' => array() );
		foreach ( $rows as $i => $row ) {
			$id = $i + 1;
			$this->store['posts'][$id] = array( 'ID' => (string) $id, 'post_type' => 'product', 'post_status' => 'publish', 'post_title' => 'Client ' . $row['name'], 'post_name' => 'client-' . $row['id'], 'post_content' => 'Client description', 'post_excerpt' => 'Client excerpt', 'post_modified' => 'unchanged' );
			$meta = array( '_rollsbar_source_id' => $row['id'], '_price' => '913', '_regular_price' => '999', '_sale_price' => '913', '_stock' => '7', '_stock_status' => 'outofstock', '_sku' => 'client-' . $id, '_thumbnail_id' => '55', '_product_image_gallery' => '56,57', '_product_attributes' => 'serialized client attributes', '_manage_stock' => 'yes', '_visibility' => 'hidden', 'client_custom' => 'preserve\\"value' );
			if ( isset( $row['options'] ) ) { $meta['_rollsbar_options_json'] = json_encode( $row['options'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ); }
			foreach ( $meta as $key => $value ) { $this->add_meta( $id, $key, $value ); }
			$this->store['terms'][$id] = array( array( 'object_id' => (string) $id, 'term_taxonomy_id' => (string) ( 500 + $id ), 'term_order' => '0' ) );
			foreach ( $row['variants'] ?? array() as $variant ) { $this->store['children'][] = array( 'parent' => $id, 'variation' => $variant, 'client_meta' => array( '_price' => '777', '_stock' => '2' ) ); }
		}
		foreach ( array( 'upsell-soy-sauce', 'upsell-ginger', 'upsell-wasabi' ) as $hidden ) { $this->store['hidden_upsells'][$hidden] = array( 'price' => '20', 'visibility' => 'hidden', 'stock' => 'client' ); }
		$this->store['meta'] = array_values( array_filter( $this->store['meta'], static fn( $m ) => ! ( '1' === $m['post_id'] && '_rollsbar_options_json' === $m['meta_key'] ) ) );
		$values = array( 'empty' => '', 'pending' => '[{"label":"Соус","choices":[],"pending":true}]', 'canonical' => json_encode( RollsBar_Shrimp_Options_Repair::canonical(), JSON_UNESCAPED_UNICODE ), 'custom' => '[{"label":"Соус","choices":["клиентский"]}]', 'malformed' => '{broken', 'almost-pending' => '[{"label":"Соус","choices":[],"pending":true,"client":1}]' );
		if ( isset( $values[$state] ) ) { $this->add_meta( 1, '_rollsbar_options_json', $values[$state] ); }
		if ( 'duplicate' === $state ) { $this->add_meta( 2, '_rollsbar_source_id', 'shrimp-tempura' ); }
		if ( 'missing-product' === $state ) { $this->store['meta'] = array_values( array_filter( $this->store['meta'], static fn( $m ) => ! ( '1' === $m['post_id'] && '_rollsbar_source_id' === $m['meta_key'] ) ) ); }
	}
	public function add_meta( $id, $key, $value ): void {
		$max = $this->store['meta'] ? max( array_column( $this->store['meta'], 'meta_id' ) ) : 0;
		$this->store['meta'][] = array( 'meta_id' => (string) ( $max + 1 ), 'post_id' => (string) $id, 'meta_key' => $key, 'meta_value' => $value );
	}
	public function prepare( $sql, ...$args ) { $token = 'prepared:' . count( $this->prepared ); $this->prepared[$token] = array( $sql, $args ); return $token; }
	public function get_results( $token, $format ) {
		[ $sql, $args ] = $this->prepared[$token];
		$this->statements[] = $sql;
		if ( 'SELECT * FROM wp_posts WHERE post_type IN (%s, %s) ORDER BY ID FOR UPDATE' === $sql ) { return array_merge( array_values( $this->store['posts'] ), $this->store['children'], array_values( $this->store['hidden_upsells'] ) ); }
		if ( str_starts_with( $sql, 'SELECT m.* FROM wp_postmeta m INNER JOIN wp_posts' ) ) { return $this->store['meta']; }
		if ( str_starts_with( $sql, 'SELECT t.* FROM wp_term_relationships t INNER JOIN wp_posts' ) ) { return array_merge( ...array_values( $this->store['terms'] ) ); }
		if ( str_starts_with( $sql, 'SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES' ) ) {
			expect_repair( $args === array( $this->posts, $this->postmeta, $this->term_relationships ), 'Engine table scope' );
			return array_map( fn( $name ) => array( 'TABLE_NAME' => $name, 'ENGINE' => 'engine' === $this->fault ? 'MyISAM' : 'InnoDB' ), $args );
		}
		if ( 'SELECT post_id, meta_id FROM wp_postmeta WHERE meta_key = %s AND BINARY meta_value = BINARY %s FOR UPDATE' === $sql ) {
			expect_repair( $args === array( '_rollsbar_source_id', 'shrimp-tempura' ), 'Exact identity query' );
			return array_values( array_map( static fn( $m ) => array_intersect_key( $m, array_flip( array( 'post_id', 'meta_id' ) ) ), array_filter( $this->store['meta'], static fn( $m ) => $args[0] === $m['meta_key'] && $args[1] === $m['meta_value'] ) ) );
		}
		if ( 'SELECT * FROM wp_posts WHERE ID = %d FOR UPDATE' === $sql ) { return isset( $this->store['posts'][$args[0]] ) ? array( $this->store['posts'][$args[0]] ) : array(); }
		if ( 'SELECT * FROM wp_postmeta WHERE post_id = %d ORDER BY meta_id FOR UPDATE' === $sql ) { return array_values( array_filter( $this->store['meta'], static fn( $m ) => (string) $args[0] === $m['post_id'] ) ); }
		if ( 'SELECT * FROM wp_term_relationships WHERE object_id = %d ORDER BY term_taxonomy_id FOR UPDATE' === $sql ) { return $this->store['terms'][$args[0]] ?? array(); }
		throw new RuntimeException( 'Unknown read SQL: ' . $sql );
	}
	public function query( $token ) {
		[ $sql, $args ] = $this->prepared[$token] ?? array( $token, array() );
		$this->statements[] = $sql;
		if ( 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE' === $sql ) { return 0; }
		if ( 'START TRANSACTION' === $sql ) { $this->saved = $this->store; return 0; }
		if ( 'ROLLBACK' === $sql ) { $this->store = $this->saved; return 0; }
		if ( 'COMMIT' === $sql ) { return 'commit' === $this->fault ? false : 0; }
		if ( 'write-failure' === $this->fault ) { return false; }
		if ( 'cas' === $this->fault ) { return 0; }
		if ( 'UPDATE wp_postmeta SET meta_value = %s WHERE meta_id = %d AND post_id = %d AND meta_key = %s AND BINARY meta_value = BINARY %s' === $sql ) {
			[ $value, $mid, $pid, $key, $old ] = $args;
			expect_repair( 1 === $pid && '_rollsbar_options_json' === $key, 'Only target/key write' );
			$n = 0;
			foreach ( $this->store['meta'] as &$m ) { if ( (int) $m['meta_id'] === $mid && (int) $m['post_id'] === $pid && $m['meta_key'] === $key && $m['meta_value'] === $old ) { $m['meta_value'] = $value; ++$n; } } unset( $m );
		} elseif ( 'INSERT INTO wp_postmeta (post_id, meta_key, meta_value) VALUES (%d, %s, %s)' === $sql ) {
			expect_repair( 1 === $args[0] && '_rollsbar_options_json' === $args[1], 'Only target/key insert' );
			$this->add_meta( ...$args ); $n = 1;
		} else { throw new RuntimeException( 'Unknown mutation SQL: ' . $sql ); }
		$this->writes += $n;
		if ( 'unexpected-delta' === $this->fault ) { $this->store['posts'][1]['post_title'] = 'corrupted'; }
		if ( 'other-product-delta' === $this->fault ) { $this->store['posts'][2]['post_title'] = 'corrupted'; }
		if ( 'variation-delta' === $this->fault ) { $this->store['children'][0]['client_meta']['_price'] = '1'; }
		return $n;
	}
}
function context_repair(): array { return array( 'environment' => 'staging', 'home' => 'https://staging.rollsbar.ru', 'siteurl' => 'https://staging.rollsbar.ru', 'blog_public' => '0', 'confirmation' => 'staging:shrimp-tempura:options-only', 'backup_verified' => 'YES', 'backup_snapshot' => gmdate( 'Ymd\THis\Z' ) ); }
function protected_store( array $store ): array {
	$store['meta'] = array_values( array_filter( $store['meta'], static fn( $m ) => ! ( '1' === $m['post_id'] && '_rollsbar_options_json' === $m['meta_key'] ) ) );
	return $store;
}
function refuses_repair( RepairDatabase $db, array $context, bool $apply = true, string $reason = 'REFUSE:' ): void {
	$before = $db->store;
	try { ( new RollsBar_Shrimp_Options_Repair( $db ) )->run( $apply, $context ); }
	catch ( RuntimeException $e ) { expect_repair( str_contains( $e->getMessage(), $reason ), 'Expected refusal reason: ' . $e->getMessage() ); expect_repair( $before === $db->store, 'Refusal must preserve full store' ); return; }
	throw new RuntimeException( 'Unsafe case accepted' );
}
$cases = array();
foreach ( array( 'missing', 'empty', 'pending', 'canonical' ) as $state ) {
	$db = new RepairDatabase( $state ); $before = $db->store;
	expect_repair( 118 === count( $before['posts'] ) && 26 === count( $before['children'] ) && 3 === count( $before['hidden_upsells'] ), 'Full catalog fixture cardinalities' );
	$repair = new RollsBar_Shrimp_Options_Repair( $db ); $result = $repair->run( false, context_repair() );
	expect_repair( $before === $db->store && 0 === $db->writes && 0 === $result['writes'], 'Dry-run unchanged: ' . $state );
	expect_repair( RollsBar_Shrimp_Options_Repair::canonical() === $result['after_options'], 'Exact dry-run choices' );
	$cases[$state] = $result;
	$result = $repair->run( true, context_repair() );
	expect_repair( protected_store( $before ) === protected_store( $db->store ), 'Full catalog/product/metadata snapshot protected' );
	expect_repair( $db->writes === ( 'canonical' === $state ? 0 : 1 ), 'Single write or canonical no-op' );
	$after = $db->store; $writes = $db->writes;
	expect_repair( 'ALREADY CORRECT' === $repair->run( true, context_repair() )['status'], 'Idempotence status' );
	expect_repair( $after === $db->store && $writes === $db->writes, 'Idempotence no further write' );
}
foreach ( array( 'custom', 'malformed', 'almost-pending', 'duplicate', 'missing-product' ) as $state ) {
	foreach ( array( false, true ) as $apply ) { $db = new RepairDatabase( $state ); refuses_repair( $db, context_repair(), $apply ); expect_repair( 0 === $db->writes, 'Refusal before write' ); }
	$cases[$state] = 'REFUSE';
}
foreach ( array( 'engine', 'cas', 'write-failure', 'unexpected-delta', 'other-product-delta', 'variation-delta', 'commit' ) as $fault ) { $db = new RepairDatabase( 'pending' ); $db->fault = $fault; refuses_repair( $db, context_repair() ); }
foreach ( array( array( 'environment', 'production' ), array( 'home', 'https://rollsbar.ru' ), array( 'siteurl', 'https://rollsbar.ru' ), array( 'blog_public', '1' ), array( 'confirmation', '' ), array( 'backup_verified', '' ), array( 'backup_snapshot', '20261023T215945Z' ), array( 'backup_snapshot', gmdate( 'Ymd\THis\Z', time() - 7201 ) ), array( 'backup_snapshot', gmdate( 'Ymd\THis\Z', time() + 60 ) ) ) as [ $key, $bad ] ) {
	$db = new RepairDatabase( 'pending' ); $context = context_repair(); $context[$key] = $bad; refuses_repair( $db, $context ); expect_repair( ! $db->statements, 'Guard before DB access' );
}
$db = new RepairDatabase( 'pending' ); $db->add_meta( 1, '_rollsbar_options_json', '' ); refuses_repair( $db, context_repair() );
$db = new RepairDatabase( 'pending' ); $db->add_meta( 1, '_rollsbar_source_id', 'client-other' ); refuses_repair( $db, context_repair() );
foreach ( array( 'post_type' => 'product_variation', 'post_status' => 'trash' ) as $key => $bad ) { $db = new RepairDatabase( 'pending' ); $db->store['posts'][1][$key] = $bad; refuses_repair( $db, context_repair() ); }
// Exercise the actual entrypoint's unset-mode default in the same isolated store.
define( 'ABSPATH', __DIR__ ); define( 'WP_CLI', true );
function wp_get_environment_type() { return 'staging'; }
function get_option( $key ) { return context_repair()[$key]; }
foreach ( array( 'ROLLSBAR_SHRIMP_REPAIR_MODE', 'ROLLSBAR_CONFIRM_SHRIMP_OPTIONS', 'ROLLSBAR_FRESH_BACKUP_VERIFIED', 'ROLLSBAR_FRESH_BACKUP_SNAPSHOT' ) as $key ) { putenv( $key ); }
$wpdb = new RepairDatabase( 'pending' ); $before = $wpdb->store;
ob_start(); require dirname( __DIR__, 2 ) . '/wordpress/deploy/repair-staging-shrimp-options.php'; $entry = json_decode( ob_get_clean(), true );
expect_repair( 0 === $entry['writes'] && $before === $wpdb->store, 'Entrypoint defaults to dry-run without confirmation' );
echo json_encode( array( 'pass' => true, 'assertions' => $checks, 'dry_run_cases' => $cases, 'full_store_protection' => true, 'live_database' => false ), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE ) . "\n";

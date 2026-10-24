<?php
/** S1-R1: single-purpose, transaction-protected metadata repair. Never auto-loaded. */
final class RollsBar_Shrimp_Options_Repair {
	private const SOURCE = 'shrimp-tempura';
	private const KEY = '_rollsbar_options_json';
	private $db;

	public function __construct( $db ) { $this->db = $db; }

	public static function canonical(): array {
		$catalog = json_decode( (string) file_get_contents( __DIR__ . '/../data/catalog.json' ), true, 512, JSON_THROW_ON_ERROR );
		$rows = array_values( array_filter( $catalog['products'], static fn( $row ) => self::SOURCE === ( $row['id'] ?? null ) ) );
		$expected = array( array( 'label' => 'Соус', 'choices' => array( 'чесночный', 'сырный', 'томатный' ) ) );
		if ( 1 !== count( $rows ) || $expected !== ( $rows[0]['options'] ?? null ) ) {
			throw new RuntimeException( 'REFUSE: canonical shrimp source has changed; reconcile first.' );
		}
		return $rows[0]['options'];
	}

	public static function guard( array $context, bool $apply ): void {
		if ( 'staging' !== $context['environment'] || 'https://staging.rollsbar.ru' !== rtrim( $context['home'], '/' ) || 'https://staging.rollsbar.ru' !== rtrim( $context['siteurl'], '/' ) || '0' !== (string) $context['blog_public'] ) {
			throw new RuntimeException( 'REFUSE: exact noindex staging environment required.' );
		}
		if ( ! $apply ) { return; }
		if ( 'staging:shrimp-tempura:options-only' !== $context['confirmation'] || 'YES' !== $context['backup_verified'] ) {
			throw new RuntimeException( 'REFUSE: explicit shrimp confirmation and fresh backup PASS acknowledgement required.' );
		}
		$stamp = DateTimeImmutable::createFromFormat( '!Ymd\THis\Z', $context['backup_snapshot'], new DateTimeZone( 'UTC' ) );
		if ( ! $stamp || $stamp->format( 'Ymd\THis\Z' ) !== $context['backup_snapshot'] || $stamp->getTimestamp() > time() || time() - $stamp->getTimestamp() > 7200 || '20261023T215945Z' === $context['backup_snapshot'] ) {
			throw new RuntimeException( 'REFUSE: acknowledge a NEW verified backup from the last two hours, never the S1 snapshot.' );
		}
	}

	private function rows( string $sql ): array {
		$rows = $this->db->get_results( $sql, ARRAY_A );
		if ( ! is_array( $rows ) || $this->db->last_error ) { throw new RuntimeException( 'REFUSE: database read failed.' ); }
		return $rows;
	}

	private function command( string $sql ): int {
		$result = $this->db->query( $sql );
		if ( false === $result ) { throw new RuntimeException( 'REFUSE: database command failed.' ); }
		return (int) $result;
	}

	private function snapshot( int $id ): array {
		return array(
			'post' => $this->rows( $this->db->prepare( "SELECT * FROM {$this->db->posts} WHERE ID = %d FOR UPDATE", $id ) ),
			'meta' => $this->rows( $this->db->prepare( "SELECT * FROM {$this->db->postmeta} WHERE post_id = %d ORDER BY meta_id FOR UPDATE", $id ) ),
			'terms' => $this->rows( $this->db->prepare( "SELECT * FROM {$this->db->term_relationships} WHERE object_id = %d ORDER BY term_taxonomy_id FOR UPDATE", $id ) ),
		);
	}

	private static function protected_snapshot( array $snapshot ): array {
		$snapshot['meta'] = array_values( array_filter( $snapshot['meta'], static fn( $row ) => self::KEY !== $row['meta_key'] ) );
		return $snapshot;
	}

	private function catalog_snapshot( int $id ): array {
		// Include variations and hidden support products. Keep locks until the
		// options-only transaction commits, so unexpected global deltas roll back.
		$posts = $this->rows( $this->db->prepare( "SELECT * FROM {$this->db->posts} WHERE post_type IN (%s, %s) ORDER BY ID FOR UPDATE", 'product', 'product_variation' ) );
		$meta = $this->rows( $this->db->prepare( "SELECT m.* FROM {$this->db->postmeta} m INNER JOIN {$this->db->posts} p ON p.ID = m.post_id WHERE p.post_type IN (%s, %s) ORDER BY m.meta_id FOR UPDATE", 'product', 'product_variation' ) );
		$terms = $this->rows( $this->db->prepare( "SELECT t.* FROM {$this->db->term_relationships} t INNER JOIN {$this->db->posts} p ON p.ID = t.object_id WHERE p.post_type IN (%s, %s) ORDER BY t.object_id, t.term_taxonomy_id FOR UPDATE", 'product', 'product_variation' ) );
		$meta = array_values( array_filter( $meta, static fn( $row ) => ! ( $id === (int) $row['post_id'] && self::KEY === $row['meta_key'] ) ) );
		return array( 'posts' => $posts, 'meta' => $meta, 'terms' => $terms );
	}

	public function run( bool $apply, array $context ): array {
		self::guard( $context, $apply );
		if ( ! is_callable( array( 'WC_Data', 'generate_meta_cache_key' ) ) ) {
			throw new RuntimeException( 'REFUSE: native Woo metadata cache API required.' );
		}
		$canonical = self::canonical();
		$json = json_encode( $canonical, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR );
		// Direct, prepared metadata SQL avoids WC_Product::save(), importers and
		// arbitrary metadata hooks. Require rollback-capable tables, and serialize
		// identity/range reads so concurrent edits cannot be overwritten after read.
		$engines = $this->rows( $this->db->prepare(
			'SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (%s, %s, %s)',
			$this->db->posts, $this->db->postmeta, $this->db->term_relationships
		) );
		if ( 3 !== count( $engines ) || array_filter( $engines, static fn( $row ) => 'InnoDB' !== $row['ENGINE'] ) ) {
			throw new RuntimeException( 'REFUSE: transactional InnoDB tables required.' );
		}
		$this->command( 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE' );
		$this->command( 'START TRANSACTION' );
		try {
			// Include all post types/statuses: a draft, trashed duplicate or variation
			// sharing this identity is an ambiguity, not permission to choose one.
			$identities = $this->rows( $this->db->prepare(
				"SELECT post_id, meta_id FROM {$this->db->postmeta} WHERE meta_key = %s AND BINARY meta_value = BINARY %s FOR UPDATE",
				'_rollsbar_source_id', self::SOURCE
			) );
			if ( 1 !== count( $identities ) ) { throw new RuntimeException( 'REFUSE: missing or duplicate shrimp source identity.' ); }
			$id = (int) $identities[0]['post_id'];
			$before = $this->snapshot( $id );
			$catalog_before = $this->catalog_snapshot( $id );
			if ( 1 !== count( $before['post'] ) || 'product' !== $before['post'][0]['post_type'] || 'trash' === $before['post'][0]['post_status'] ) {
				throw new RuntimeException( 'REFUSE: source identity is not an active product.' );
			}
			$source_rows = array_values( array_filter( $before['meta'], static fn( $row ) => '_rollsbar_source_id' === $row['meta_key'] ) );
			if ( 1 !== count( $source_rows ) || self::SOURCE !== $source_rows[0]['meta_value'] ) { throw new RuntimeException( 'REFUSE: ambiguous source metadata.' ); }
			$options = array_values( array_filter( $before['meta'], static fn( $row ) => self::KEY === $row['meta_key'] ) );
			if ( count( $options ) > 1 ) { throw new RuntimeException( 'REFUSE: duplicate options metadata.' ); }
			$raw = $options[0]['meta_value'] ?? '';
			$decoded = json_decode( $raw, true );
			$pending = array( array( 'label' => 'Соус', 'choices' => array(), 'pending' => true ) );
			$state = ! $options ? 'missing' : ( '' === $raw ? 'empty' : ( $decoded === $canonical ? 'canonical' : ( $decoded === $pending ? 'pending' : 'conflict' ) ) );
			if ( 'conflict' === $state ) { throw new RuntimeException( 'REFUSE: custom/noncanonical options; reconcile client edits. value_sha256=' . hash( 'sha256', $raw ) ); }
			$report = array( 'source_id' => self::SOURCE, 'product_id' => $id, 'key' => self::KEY, 'before_state' => $state, 'before_sha256' => hash( 'sha256', $raw ), 'after_options' => $canonical, 'writes' => 0 );
			$report['protected_catalog_before_sha256'] = hash( 'sha256', serialize( $catalog_before ) );
			$report['protected_product_before_sha256'] = hash( 'sha256', serialize( self::protected_snapshot( $before ) ) );
			$report['product_and_variation_rows'] = count( $catalog_before['posts'] );
			if ( 'canonical' === $state || ! $apply ) {
				$this->command( 'ROLLBACK' );
				return $report + array( 'status' => 'canonical' === $state ? 'ALREADY CORRECT' : 'DRY RUN: would set canonical options' );
			}
			if ( $options ) {
				$changed = $this->command( $this->db->prepare(
					"UPDATE {$this->db->postmeta} SET meta_value = %s WHERE meta_id = %d AND post_id = %d AND meta_key = %s AND BINARY meta_value = BINARY %s",
					$json, (int) $options[0]['meta_id'], $id, self::KEY, $raw
				) );
			} else {
				$changed = $this->command( $this->db->prepare( "INSERT INTO {$this->db->postmeta} (post_id, meta_key, meta_value) VALUES (%d, %s, %s)", $id, self::KEY, $json ) );
			}
			if ( 1 !== $changed ) { throw new RuntimeException( 'REFUSE: expected exactly one metadata row change.' ); }
			$after = $this->snapshot( $id );
			$catalog_after = $this->catalog_snapshot( $id );
			$after_options = array_values( array_filter( $after['meta'], static fn( $row ) => self::KEY === $row['meta_key'] ) );
			if ( $catalog_before !== $catalog_after || self::protected_snapshot( $before ) !== self::protected_snapshot( $after ) || 1 !== count( $after_options ) || $json !== $after_options[0]['meta_value'] ) {
				throw new RuntimeException( 'REFUSE: unexpected product delta; transaction rolled back.' );
			}
			$this->command( 'COMMIT' );
		} catch ( Throwable $error ) {
			$this->db->query( 'ROLLBACK' );
			throw $error;
		}
		// Both WP and Woo cache metadata. Invalidate this product only; do not
		// save a WC_Product or flush other products/site caches.
		wp_cache_delete( $id, 'post_meta' );
		wp_cache_delete( WC_Data::generate_meta_cache_key( $id, 'products' ), 'products' );
		$report['writes'] = 1;
		$report['protected_catalog_after_sha256'] = hash( 'sha256', serialize( $catalog_after ) );
		$report['protected_product_after_sha256'] = hash( 'sha256', serialize( self::protected_snapshot( $after ) ) );
		return $report + array( 'status' => 'REPAIRED', 'after_sha256' => hash( 'sha256', $json ), 'protected_snapshot' => 'UNCHANGED' );
	}
}

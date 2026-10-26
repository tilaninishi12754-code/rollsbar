<?php
/** Customer media canon. Runtime identities are explicit source IDs, never titles. */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class RollsBar_Client_Media {

	public const VERSION = 'client-media-2026-10-21';
	public const COUNTS = array( 'assets' => 36, 'preserved_rows' => 61, 'resolved_rows' => 57, 'resolved_source_ids' => 45, 'deferred_rows' => 4, 'deferred_products' => 2 );

	public static function root(): string {
		return dirname( RollsBar_Catalog_Importer::catalog_path() ) . '/product-media/client-2026-10-21';
	}

	private static function demand( bool $condition, string $reason ): void {
		if ( ! $condition ) { throw new RuntimeException( 'Client media preflight: ' . $reason ); }
	}

	/** Entire manifest, all binaries and all product identities validate before writes. */
	public static function validate( ?array $manifest = null, ?string $root = null ): array {
		$root = $root ?? self::root();
		if ( null === $manifest ) {
			self::demand( is_readable( $root . '/manifest.json' ), 'missing manifest' );
			$manifest = json_decode( (string) file_get_contents( $root . '/manifest.json' ), true, 512, JSON_THROW_ON_ERROR );
		}
		self::demand( ( $manifest['schema_version'] ?? null ) === 1 && ( $manifest['canon_version'] ?? '' ) === self::VERSION, 'unsupported manifest schema/version' );
		self::demand( ( $manifest['counts'] ?? null ) === self::COUNTS, 'manifest count mismatch' );
		$source_hashes = array( '19-10-2026_09-24-58.zip' => '9ce332520d715225a527bde90b439aa9a306579415ed3d18ab18212e1889b531', '21-10-2026_10-48-20.zip' => '336150f653fc2247e92612fe3388a996449222b3bc17e2b351c97d804d5d00ef' );
		self::demand( count( $manifest['sources'] ?? array() ) === 2, 'missing source provenance' );
		foreach ( $manifest['sources'] as $source ) {
			self::demand( isset( $source_hashes[ $source['filename'] ?? '' ] ) && $source['sha256'] === $source_hashes[ $source['filename'] ], 'source archive provenance checksum' );
			unset( $source_hashes[ $source['filename'] ] );
		}
		self::demand( is_array( $manifest['assets'] ?? null ) && is_array( $manifest['assignments'] ?? null ), 'missing assets/assignments' );
		self::demand( count( $manifest['assets'] ) === 36 && count( $manifest['assignments'] ) === 61, 'asset/row count mismatch' );
		$catalog = array_column( RollsBar_Catalog_Importer::load_catalog()['products'], null, 'id' );
		$assets = array(); $hashes = array(); $files = array();
		foreach ( $manifest['assets'] as $asset ) {
			$key = $asset['media_key'] ?? '';
			$file = $asset['file'] ?? '';
			self::demand( is_string( $key ) && 1 === preg_match( '/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $key ) && ! isset( $assets[ $key ] ), 'duplicate/invalid media key' );
			self::demand( 1 === preg_match( '/^images\/[a-z0-9-]+\.(png|webp)$/D', $file ) && ! isset( $files[ $file ] ), 'invalid/duplicate asset path' );
			$path = realpath( $root . '/' . $file );
			self::demand( false !== $path && is_file( $path ) && dirname( $path ) === realpath( $root . '/images' ), 'missing/unsafe canonical asset: ' . $key );
			$hash = hash_file( 'sha256', $path );
			self::demand( $hash === ( $asset['source_sha256'] ?? '' ) && $hash === ( $asset['derived_sha256'] ?? '' ) && ! isset( $hashes[ $hash ] ), 'asset hash mismatch/duplicate binary: ' . $key );
			$info = getimagesize( $path );
			self::demand( is_array( $info ) && array( $info[0], $info[1] ) === array( 1254, 1254 ) && ( $asset['dimensions'] ?? null ) === array( 1254, 1254 ), 'asset dimensions: ' . $key );
			$mime = $info['mime'];
			self::demand( in_array( $mime, array( 'image/png', 'image/webp' ), true ) && $mime === ( $asset['source_mime'] ?? '' ) && $mime === ( $asset['derived_mime'] ?? '' ) && str_ends_with( $file, 'image/png' === $mime ? '.png' : '.webp' ), 'asset MIME: ' . $key );
			self::demand( ( $asset['canon_version'] ?? '' ) === self::VERSION && ! empty( $asset['provenance'] ), 'missing asset provenance' );
			$asset['path'] = $path;
			$assets[ $key ] = $asset; $hashes[ $hash ] = true; $files[ $file ] = true;
		}
		$products = array(); $seen_rows = array(); $asset_rows = array(); $asset_sources = array(); $deferred_names = array(); $resolved = 0; $deferred = 0;
		foreach ( $manifest['assignments'] as $row ) {
			$rn = $row['table_row'] ?? 0; $key = $row['media_key'] ?? ''; $source = $row['source_id'] ?? null;
			self::demand( is_int( $rn ) && $rn > 3 && ! isset( $seen_rows[ $rn ] ), 'duplicate/invalid table row' );
			self::demand( isset( $assets[ $key ] ) && ( $row['photo_name'] ?? '' ) === $assets[ $key ]['original_photo_name'], 'unknown photo name/media key' );
			$seen_rows[ $rn ] = true; $asset_rows[ $key ][] = $rn;
			if ( 'deferred_new_product_identity' === ( $row['status'] ?? '' ) ) {
				$expected = in_array( $rn, array( 83, 84 ), true ) ? 'Охотничья' : ( in_array( $rn, array( 85, 86 ), true ) ? 'Салями' : '' );
				self::demand( null === $source && '' !== $expected && $row['product_name'] === $expected && in_array( $row['variant'], array( '30 см', '50 см' ), true ) && ! empty( $row['reason'] ), 'unexpected deferred identity' );
				++$deferred; $deferred_names[ $expected ] = true; continue;
			}
			self::demand( 'resolved' === ( $row['status'] ?? '' ) && is_string( $source ) && isset( $catalog[ $source ] ), 'wrong resolved source ID' );
			$p = $catalog[ $source ];
			self::demand( $p['name'] === ( $row['catalog_name'] ?? '' ) && $p['cat'] === ( $row['catalog_category'] ?? '' ), 'source ID identity fingerprint conflict' );
			$variants = array_column( $p['variants'] ?? array(), 'label' );
			self::demand( $variants ? in_array( $row['variant'], $variants, true ) : null === $row['variant'], 'wrong source variant' );
			self::demand( ! isset( $products[ $source ] ) || $products[ $source ] === $key, 'conflicting photos for one variable parent/product' );
			$products[ $source ] = $key; $asset_sources[ $key ][ $source ] = true; ++$resolved;
		}
		self::demand( $resolved === 57 && count( $products ) === 45 && $deferred === 4 && count( $deferred_names ) === 2, 'assignment count mismatch' );
		foreach ( $assets as $key => $asset ) {
			$ids = array_keys( $asset_sources[ $key ] ?? array() ); sort( $ids );
			self::demand( $ids === $asset['source_ids'] && ( $asset_rows[ $key ] ?? array() ) === $asset['assignment_rows'], 'asset/assignment index mismatch' );
		}
		return array( 'assets' => $assets, 'products' => $products, 'counts' => self::COUNTS );
	}

	/** Hash and metadata both matter: a same-named file is never an identity. */
	private static function existing_attachment( array $asset ): int {
		$ids = get_posts( array( 'post_type' => 'attachment', 'post_status' => array_values( get_post_stati( array(), 'names' ) ), 'numberposts' => -1, 'fields' => 'ids',
			'meta_query' => array( 'relation' => 'OR',
				array( 'key' => '_rollsbar_client_media_key', 'value' => $asset['media_key'] ),
				array( 'key' => '_rollsbar_client_media_sha256', 'value' => $asset['derived_sha256'] ) ) ) );
		self::demand( count( $ids ) <= 1, 'duplicate attachment identity: ' . $asset['media_key'] );
		if ( ! $ids ) { return 0; }
		$id = (int) $ids[0]; $file = get_attached_file( $id );
		self::demand( get_post_meta( $id, '_rollsbar_client_media_sha256', true ) === $asset['derived_sha256'] &&
			get_post_meta( $id, '_rollsbar_client_media_key', true ) === $asset['media_key'] &&
			get_post_meta( $id, '_rollsbar_client_media_canon', true ) === self::VERSION &&
			is_string( $file ) && is_file( $file ) && hash_file( 'sha256', $file ) === $asset['derived_sha256'] &&
			get_post_mime_type( $id ) === $asset['derived_mime'] && get_post_status( $id ) !== 'trash', 'wrong existing attachment hash/identity: ' . $asset['media_key'] );
		return $id;
	}

	public static function plan(): array {
		$plan = self::validate(); $plan['attachments'] = array(); $plan['woo_products'] = array();
		$catalog = array_column( RollsBar_Catalog_Importer::load_catalog()['products'], null, 'id' );
		foreach ( $plan['assets'] as $key => $asset ) { $plan['attachments'][ $key ] = self::existing_attachment( $asset ); }
		foreach ( $plan['products'] as $source => $key ) {
			$ids = get_posts( array( 'post_type' => 'product', 'post_status' => array_values( get_post_stati( array(), 'names' ) ), 'numberposts' => -1, 'fields' => 'ids', 'meta_key' => '_rollsbar_source_id', 'meta_value' => $source ) );
			$id = (int) wc_get_product_id_by_sku( RollsBar_Catalog_Importer::sku_for( $source ) );
			$product = $id ? wc_get_product( $id ) : false;
			self::demand( count( $ids ) === 1 && (int) $ids[0] === $id && $product && $product->get_meta( '_rollsbar_source_id', true ) === $source &&
				$product->get_type() === ( empty( $catalog[ $source ]['variants'] ) ? 'simple' : 'variable' ) && $product->get_status() === 'publish', 'missing/ambiguous Woo source ID/SKU: ' . $source );
			$plan['woo_products'][ $source ] = $product;
		}
		return $plan;
	}

	private static function guard( bool $confirm ): void {
		$env = wp_get_environment_type();
		self::demand( in_array( $env, array( 'local', 'development', 'staging' ), true ), 'production media mutation forbidden' );
		if ( 'staging' === $env ) {
			self::demand( $confirm && defined( 'WP_CLI' ) && WP_CLI && strtolower( (string) wp_parse_url( home_url( '/' ), PHP_URL_HOST ) ) === 'staging.rollsbar.ru', 'requires exact staging host and --confirm-staging' );
		}
	}

	public static function sync( bool $dry_run = false, bool $confirm = false ): array {
		self::guard( $confirm );
		if ( ! $dry_run ) { self::demand( add_option( 'rollsbar_client_media_sync_lock', gmdate( 'c' ), '', false ), 'sync already running; inspect lock before recovery' ); }
		try {
			$plan = self::plan();
			$result = array_merge( $plan['counts'], array( 'canon_version' => self::VERSION, 'dry_run' => $dry_run, 'created' => 0, 'reused' => 0, 'assigned' => 0, 'unchanged' => 0 ) );
			foreach ( $plan['assets'] as $key => $asset ) {
				$id = $plan['attachments'][ $key ];
				if ( $id ) { ++$result['reused']; } else {
					++$result['created'];
					if ( ! $dry_run ) {
						$upload = wp_upload_bits( basename( $asset['file'] ), null, file_get_contents( $asset['path'] ) );
						if ( ! empty( $upload['error'] ) ) { throw new RuntimeException( 'Client media upload ' . $key . ': ' . $upload['error'] ); }
						$id = wp_insert_attachment( array( 'post_title' => $asset['original_photo_name'], 'post_status' => 'inherit', 'post_mime_type' => $asset['derived_mime'],
							'meta_input' => array( '_rollsbar_client_media_key' => $key, '_rollsbar_client_media_sha256' => $asset['derived_sha256'],
								'_rollsbar_client_media_canon' => self::VERSION, '_rollsbar_client_media_source' => wp_json_encode( $asset['provenance'], JSON_UNESCAPED_UNICODE ) ) ), $upload['file'], 0, true );
						if ( is_wp_error( $id ) ) { throw new RuntimeException( 'Client media attachment ' . $key . ': ' . $id->get_error_message() ); }
						update_post_meta( $id, '_wp_attachment_image_alt', $asset['original_photo_name'] );
					}
				}
				if ( ! $dry_run && ! wp_get_attachment_metadata( $id ) ) {
					require_once ABSPATH . 'wp-admin/includes/image.php';
					$metadata = wp_generate_attachment_metadata( $id, get_attached_file( $id ) );
					if ( ! is_array( $metadata ) || empty( $metadata['width'] ) ) { throw new RuntimeException( 'Client media image processing failed: ' . $key . '; attachment retained for safe retry' ); }
					wp_update_attachment_metadata( $id, $metadata );
				}
				$plan['attachments'][ $key ] = $id;
			}
			foreach ( $plan['products'] as $source => $key ) {
				$product = $plan['woo_products'][ $source ]; $id = $plan['attachments'][ $key ];
				$correct = $id && (int) $product->get_image_id() === (int) $id && (int) $product->get_meta( '_rollsbar_client_media_attachment_id', true ) === (int) $id &&
					$product->get_meta( '_rollsbar_client_media_key', true ) === $key && $product->get_meta( '_rollsbar_client_media_canon', true ) === self::VERSION;
				if ( $correct ) { ++$result['unchanged']; continue; }
				++$result['assigned'];
				if ( $dry_run ) { continue; }
				$product->set_image_id( $id );
				$product->update_meta_data( '_rollsbar_client_media_attachment_id', $id );
				$product->update_meta_data( '_rollsbar_client_media_key', $key );
				$product->update_meta_data( '_rollsbar_client_media_canon', self::VERSION );
				$product->save();
			}
			return $result;
		} finally { if ( ! $dry_run ) { delete_option( 'rollsbar_client_media_sync_lock' ); } }
	}

	/** Canonical assignment survives a stale featured image and legacy catalog img. */
	public static function attachment_for( WC_Product $product ): int {
		static $map = null;
		if ( null === $map ) {
			$manifest = json_decode( (string) @file_get_contents( self::root() . '/manifest.json' ), true );
			$map = array();
			foreach ( $manifest['assignments'] ?? array() as $row ) {
				if ( 'resolved' === $row['status'] ) { $map[ $row['source_id'] ] = $row['media_key']; }
			}
		}
		$source = (string) $product->get_meta( '_rollsbar_source_id', true );
		$id = (int) $product->get_meta( '_rollsbar_client_media_attachment_id', true );
		return isset( $map[ $source ] ) && $id && get_post_meta( $id, '_rollsbar_client_media_key', true ) === $map[ $source ] &&
			get_post_meta( $id, '_rollsbar_client_media_canon', true ) === self::VERSION ? $id : 0;
	}

	/** Called by catalog import only AFTER canonical products have been created. */
	public static function after_catalog_import(): void {
		$env = wp_get_environment_type();
		if ( in_array( $env, array( 'local', 'development' ), true ) ||
			( 'staging' === $env && defined( 'WP_CLI' ) && WP_CLI && strtolower( (string) wp_parse_url( home_url( '/' ), PHP_URL_HOST ) ) === 'staging.rollsbar.ru' ) ) {
			// A smoke/limited import must not start a partially provisioned media sync.
			foreach ( self::validate()['products'] as $source => $key ) {
				if ( ! wc_get_product_id_by_sku( RollsBar_Catalog_Importer::sku_for( $source ) ) ) { return; }
			}
			self::sync( false, true );
		}
	}

	public static function register_cli(): void {
		if ( defined( 'WP_CLI' ) && WP_CLI ) { WP_CLI::add_command( 'rollsbar media', 'RollsBar_Client_Media_Command' ); }
	}
}

if ( defined( 'WP_CLI' ) && WP_CLI ) {
	final class RollsBar_Client_Media_Command {
		/** Reconcile the committed client canon. Use --dry-run and --confirm-staging. */
		public function sync( array $args, array $assoc ): void {
			WP_CLI::success( wp_json_encode( RollsBar_Client_Media::sync( isset( $assoc['dry-run'] ), isset( $assoc['confirm-staging'] ) ) ) );
		}
		/** Validate repo manifest/assets without changing WordPress. */
		public function validate(): void { WP_CLI::success( wp_json_encode( RollsBar_Client_Media::validate()['counts'] ) ); }
	}
}

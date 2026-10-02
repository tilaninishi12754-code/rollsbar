<?php
/**
 * WooCommerce catalog importer for the approved Rolls Bar catalog.
 *
 * Usage:
 *   wp rollsbar catalog validate
 *   wp rollsbar catalog import --dry-run
 *   wp rollsbar catalog import --limit=5
 *   wp rollsbar catalog import
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class RollsBar_Catalog_Importer {

	private const CATEGORY_MAP = array(
		'rolls'    => 'Роллы',
		'pizza'    => 'Пицца',
		'hits'     => 'Хит-меню',
		'combo'    => 'Комбо',
		'sets'     => 'Сеты',
		'baked'    => 'Запечённые',
		'tempura'  => 'Темпура',
		'desserts' => 'Десерты',
		'drinks'   => 'Напитки',
		'snacks'   => 'Закуски',
		'wok'      => 'WOK и рис',
		'soups'    => 'Супы',
	);

	public static function catalog_path(): string {
		$packaged = ROLLSBAR_CORE_DIR . 'data/catalog.json';

		if ( is_readable( $packaged ) ) {
			return $packaged;
		}

		return dirname( ROLLSBAR_CORE_DIR, 3 ) . '/data/catalog.json';
	}

	public static function load_catalog(): array {
		$path = self::catalog_path();

		if ( ! is_readable( $path ) ) {
			throw new RuntimeException( 'Rolls Bar catalog file is not readable: ' . $path );
		}

		$data = json_decode( (string) file_get_contents( $path ), true );

		if ( ! is_array( $data ) || empty( $data['products'] ) || ! is_array( $data['products'] ) ) {
			throw new RuntimeException( 'Invalid Rolls Bar catalog JSON.' );
		}

		return $data;
	}

	public static function sku_for( string $id ): string {
		$normalized = strtoupper( preg_replace( '/[^A-Za-z0-9]+/', '-', $id ) );
		return 'RB-' . trim( $normalized, '-' );
	}

	public static function variation_sku( string $product_id, string $label ): string {
		$base  = self::sku_for( $product_id );
		$label = strtoupper( preg_replace( '/[^A-Za-z0-9А-Яа-яЁё]+/u', '-', $label ) );
		$label = trim( $label, '-' );

		return $base . '-' . substr( md5( $label ), 0, 8 );
	}

	private static function category_id( string $slug ): int {
		$name = self::CATEGORY_MAP[ $slug ] ?? $slug;
		$term = term_exists( $slug, 'product_cat' );

		if ( ! $term ) {
			$term = wp_insert_term(
				$name,
				'product_cat',
				array( 'slug' => sanitize_title( $slug ) )
			);
		}

		if ( is_wp_error( $term ) ) {
			throw new RuntimeException( $term->get_error_message() );
		}

		return (int) ( is_array( $term ) ? $term['term_id'] : $term );
	}

	private static function find_product_id( string $sku ): int {
		$id = wc_get_product_id_by_sku( $sku );
		return $id ? (int) $id : 0;
	}

	private static function configure_common( WC_Product $product, array $row ): void {
		$product->set_name( (string) $row['name'] );
		$product->set_status( 'publish' );
		$product->set_catalog_visibility( 'visible' );
		$product->set_description( (string) ( $row['desc'] ?? '' ) );
		$product->set_short_description( (string) ( $row['desc'] ?? '' ) );
		$product->set_category_ids( array( self::category_id( (string) $row['cat'] ) ) );
		$product->set_stock_status( 'instock' );

		if ( ! empty( $row['img'] ) ) {
			$product->update_meta_data( '_rollsbar_source_image', esc_url_raw( (string) $row['img'] ) );
		}

		if ( isset( $row['options'] ) ) {
			$product->update_meta_data(
				'_rollsbar_options_json',
				wp_json_encode( $row['options'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES )
			);
		}

		$product->update_meta_data( '_rollsbar_source_id', (string) $row['id'] );
		$product->update_meta_data( '_rollsbar_catalog_source', 'approved-2026-10-01' );
	}

	private static function import_simple( array $row, bool $dry_run ): int {
		$sku = self::sku_for( (string) $row['id'] );
		$id  = self::find_product_id( $sku );

		if ( $dry_run ) {
			return $id;
		}

		$product = $id ? wc_get_product( $id ) : new WC_Product_Simple();

		if ( ! $product instanceof WC_Product_Simple ) {
			wp_delete_post( $id, true );
			$product = new WC_Product_Simple();
		}

		$product->set_sku( $sku );
		$product->set_regular_price( (string) $row['price'] );
		self::configure_common( $product, $row );

		return (int) $product->save();
	}

	private static function import_variable( array $row, bool $dry_run ): int {
		$sku = self::sku_for( (string) $row['id'] );
		$id  = self::find_product_id( $sku );

		if ( $dry_run ) {
			return $id;
		}

		$product = $id ? wc_get_product( $id ) : new WC_Product_Variable();

		if ( ! $product instanceof WC_Product_Variable ) {
			wp_delete_post( $id, true );
			$product = new WC_Product_Variable();
		}

		$product->set_sku( $sku );
		self::configure_common( $product, $row );

		$labels = array_values(
			array_map(
				static fn( array $variant ): string => (string) $variant['label'],
				$row['variants']
			)
		);

		$attribute = new WC_Product_Attribute();
		$attribute->set_id( 0 );
		$attribute->set_name( 'Вариант' );
		$attribute->set_options( $labels );
		$attribute->set_position( 0 );
		$attribute->set_visible( true );
		$attribute->set_variation( true );

		$product->set_attributes( array( $attribute ) );
		$product_id = (int) $product->save();

		$existing = $product->get_children();
		foreach ( $existing as $variation_id ) {
			wp_delete_post( $variation_id, true );
		}

		foreach ( $row['variants'] as $variant ) {
			$variation = new WC_Product_Variation();
			$variation->set_parent_id( $product_id );
			$variation->set_sku(
				self::variation_sku( (string) $row['id'], (string) $variant['label'] )
			);
			$variation->set_regular_price( (string) $variant['price'] );
			$variation->set_stock_status( 'instock' );
			$variation->set_attributes(
				array( 'Вариант' => (string) $variant['label'] )
			);
			$variation->save();
		}

		WC_Product_Variable::sync( $product_id );

		return $product_id;
	}

	public static function import_all( bool $dry_run = false, int $limit = 0 ): array {
		$catalog = self::load_catalog();

		if ( $limit > 0 ) {
			$catalog['products'] = array_slice( $catalog['products'], 0, $limit );
		}
		$result  = array(
			'cards'       => 0,
			'source_rows' => 0,
			'created_or_updated' => 0,
			'dry_run'     => $dry_run,
			'limit'       => max( 0, $limit ),
		);

		foreach ( $catalog['products'] as $row ) {
			++$result['cards'];

			$variants = ! empty( $row['variants'] ) && is_array( $row['variants'] )
				? $row['variants']
				: array();

			$result['source_rows'] += $variants ? count( $variants ) : 1;

			if ( $variants ) {
				self::import_variable( $row, $dry_run );
			} else {
				self::import_simple( $row, $dry_run );
			}

			++$result['created_or_updated'];
		}

		return $result;
	}

	public static function register_cli(): void {
		if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
			return;
		}

		WP_CLI::add_command( 'rollsbar catalog', 'RollsBar_Catalog_Importer_Command' );
	}
}

if ( defined( 'WP_CLI' ) && WP_CLI ) {
	final class RollsBar_Catalog_Importer_Command {

		public function validate(): void {
			$data = RollsBar_Catalog_Importer::load_catalog();

			$cards = count( $data['products'] );
			$rows  = 0;

			foreach ( $data['products'] as $row ) {
				$rows += ! empty( $row['variants'] ) && is_array( $row['variants'] )
					? count( $row['variants'] )
					: 1;
			}

			WP_CLI::success(
				sprintf(
					'Catalog valid: %d cards / %d source rows. Approved commit: %s',
					$cards,
					$rows,
					(string) ( $data['approved_source_commit'] ?? 'unknown' )
				)
			);
		}

		/**
		 * Import or update WooCommerce products from the approved catalog.
		 *
		 * ## OPTIONS
		 *
		 * [--dry-run]
		 * : Validate traversal without writing products.
		 *
		 * [--limit=<number>]
		 * : Import only the first N product cards. Useful for staging smoke tests.
		 */
		public function import( array $args, array $assoc_args ): void {
			unset( $args );

			$dry_run = isset( $assoc_args['dry-run'] );
			$limit   = isset( $assoc_args['limit'] ) ? absint( $assoc_args['limit'] ) : 0;
			$result  = RollsBar_Catalog_Importer::import_all( $dry_run, $limit );

			WP_CLI::success(
				sprintf(
					'%s: %d cards / %d source rows%s.',
					$dry_run ? 'Dry run complete' : 'Import complete',
					$result['cards'],
					$result['source_rows'],
					$result['limit'] ? ' (limit=' . $result['limit'] . ')' : ''
				)
			);
		}
	}
}

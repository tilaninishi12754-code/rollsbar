<?php
/** Read-only real Woo + active-theme reader acceptance. Never imports fixtures. */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { exit( 1 ); }
require_once __DIR__ . '/shrimp-options-repair.php';
try {
	global $wpdb;
	if ( ! is_object( $wpdb ) || ! is_callable( array( $wpdb, 'prepare' ) ) || ! is_callable( array( $wpdb, 'get_col' ) ) ) { throw new RuntimeException( 'REFUSE: usable WordPress database handle required.' ); }
	RollsBar_Shrimp_Options_Repair::guard( array( 'environment' => wp_get_environment_type(), 'home' => get_option( 'home' ), 'siteurl' => get_option( 'siteurl' ), 'blog_public' => get_option( 'blog_public' ) ), false );
	$check = static function ( $ok, $message ) { if ( ! $ok ) { throw new RuntimeException( $message ); } };
	$source = json_decode( file_get_contents( __DIR__ . '/../data/catalog.json' ), true, 512, JSON_THROW_ON_ERROR )['products'];
	$expected = array_column( $source, 'id' );
	$products = wc_get_products( array( 'status' => 'publish', 'visibility' => 'visible', 'limit' => -1 ) );
	$ids = array(); $variables = 0; $variations = 0; $wok = 0; $wok_choices = 0; $shrimp = null;
	foreach ( $products as $product ) {
		$id = (string) $product->get_meta( '_rollsbar_source_id', true );
		$check( in_array( $id, $expected, true ) && ! isset( $ids[$id] ), 'Unexpected or duplicate public identity' );
		$check( 'visible' === $product->get_catalog_visibility(), 'Canonical product excluded from public catalog/search' );
		$ids[$id] = true;
		if ( $product->is_type( 'variable' ) ) { ++$variables; $variations += count( $product->get_children() ); }
		if ( str_starts_with( $id, 'wok-' ) ) {
			++$wok; $selection = rollsbar_product_selection_data( $product );
			$check( ! $selection['blocked'] && 1 === count( $selection['options'] ) && ! $selection['options'][0]['pending'], 'WOK pending/blocked' );
			$check( 3 === count( $selection['options'][0]['choices'] ), 'WOK choices mismatch' );
			$wok_choices += count( $selection['options'][0]['choices'] );
		}
		if ( 'shrimp-tempura' === $id ) { $shrimp = $product; }
	}
	$check( 118 === count( $products ) && 118 === count( $ids ) && ! array_diff( $expected, array_keys( $ids ) ), 'Public catalog must have all 118 canonical identities' );
	$check( 13 === $variables && 26 === $variations && 6 === $wok && 18 === $wok_choices, 'Variable/WOK count mismatch' );
	$matches = $wpdb->get_col( $wpdb->prepare( "SELECT post_id FROM {$wpdb->postmeta} WHERE meta_key=%s AND BINARY meta_value=BINARY %s", '_rollsbar_source_id', 'shrimp-tempura' ) );
	$check( 1 === count( $matches ) && $shrimp && (int) $matches[0] === $shrimp->get_id(), 'Shrimp identity must be unique across all statuses/types' );
	$check( RollsBar_Shrimp_Options_Repair::canonical() === json_decode( $shrimp->get_meta( '_rollsbar_options_json', true ), true ), 'Live Woo shrimp metadata mismatch' );
	$selection = rollsbar_product_selection_data( $shrimp );
	$check( ! $selection['blocked'] && $selection['required'] && $selection['options'] === array( array( 'label' => 'Соус', 'choices' => array( 'чесночный', 'сырный', 'томатный' ), 'pending' => false ) ), 'Active frontend reader shrimp mismatch' );
	foreach ( array( 'upsell-soy-sauce', 'upsell-ginger', 'upsell-wasabi' ) as $hidden ) {
		$matches = $wpdb->get_col( $wpdb->prepare( "SELECT post_id FROM {$wpdb->postmeta} WHERE meta_key=%s AND BINARY meta_value=BINARY %s", '_rollsbar_source_id', $hidden ) );
		$check( count( $matches ) <= 1, 'Hidden support identity duplicate' );
		// Provisional support products are local-only seeds; never create them
		// on staging to satisfy QA. Absence also excludes them from public search.
		if ( ! $matches ) { echo 'hidden_support=' . $hidden . ":absent_not_provisioned\n"; continue; }
		$product = wc_get_product( (int) $matches[0] );
		$check( $product && 'hidden' === $product->get_catalog_visibility() && ! isset( $ids[$hidden] ), 'Upsell leaked into public catalog' );
	}
	echo "S1-R2 LIVE WOO PASS: main=118 identities=118 variable_parents=13 variations=26 wok=6/18 shrimp=3 pending=false hidden_upsells=excluded\n";
	echo json_encode( array( 'shrimp_source_matches' => 1, 'product_id' => $shrimp->get_id(), 'live_theme_selection' => $selection ), JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR ) . "\n";
} catch ( Throwable $error ) {
	fwrite( STDERR, 'S1-R2 LIVE WOO FAIL: ' . $error->getMessage() . "\n" ); exit( 1 );
}

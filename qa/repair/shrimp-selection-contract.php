<?php
// Feed the repair's exact serialized format through real selector/cart readers.
define( 'ROLLSBAR_CART_QA', true );
require dirname( __DIR__ ) . '/visual/cart-fixture.php';
require $root . '/wordpress/deploy/shrimp-options-repair.php';
$product = null;
foreach ( $fixture_products as $candidate ) { if ( 'shrimp-tempura' === $candidate->get_meta( '_rollsbar_source_id' ) ) { $product = $candidate; } }
if ( ! $product ) { throw new RuntimeException( 'Missing shrimp fixture' ); }
$canonical = RollsBar_Shrimp_Options_Repair::canonical();
$product->row['meta']['_rollsbar_options_json'] = json_encode( $canonical, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
$selection = rollsbar_product_selection_data( $product );
if ( $selection['blocked'] || ! $selection['required'] || $selection['options'] !== array( array( 'label' => 'Соус', 'choices' => array( 'чесночный', 'сырный', 'томатный' ), 'pending' => false ) ) ) { throw new RuntimeException( 'Selector JSON contract failed' ); }
foreach ( $canonical[0]['choices'] as $choice ) {
	$expected = array( array( 'label' => 'Соус', 'value' => $choice ) );
	if ( RollsBar_Cart_Actions::options( $product, array( $choice ) ) !== $expected ) { throw new RuntimeException( 'Cart option contract failed' ); }
}
try { RollsBar_Cart_Actions::options( $product, array( 'терияки' ) ); throw new RuntimeException( 'WOK substitution accepted' ); }
catch ( Exception $e ) { if ( 'WOK substitution accepted' === $e->getMessage() ) { throw $e; } }
echo json_encode( array( 'pass' => true, 'choices' => $selection['options'][0]['choices'], 'pending' => false ), JSON_UNESCAPED_UNICODE ) . "\n";

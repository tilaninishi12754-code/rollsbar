<?php
// Pure server contracts: signed provider fixtures, no WordPress DB/order writes.
define( 'ABSPATH', __DIR__ ); define( 'HOUR_IN_SECONDS', 3600 );
function wp_json_encode( $v ) { return json_encode( $v, JSON_UNESCAPED_UNICODE ); }
function wp_salt( $v ) { return 'fixture-only-' . $v; }
function wp_get_environment_type() { return $GLOBALS['rb_fixture_environment'] ?? 'staging'; }
require __DIR__ . '/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-geocode-policy.php';
require __DIR__ . '/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-delivery-minimum.php';
function check_rule( $ok, $label ) { if ( ! $ok ) { throw new RuntimeException( $label ); } echo "PASS $label\n"; }
function identity( $patch = array() ) { return array_merge( array( 'region' => 'Крым', 'area' => 'Симферопольский', 'city' => 'Симферополь', 'city_fias_id' => 'fixture-city', 'street' => 'Гагарина', 'street_fias_id' => 'fixture-street', 'house' => '1', 'house_fias_id' => 'fixture-house', 'geo_lat' => '44.9', 'geo_lon' => '34.1', 'qc_geo' => '0' ), $patch ); }
check_rule( 92 === count( RollsBar_Delivery_Minimum::rules() ), 'all 92 source cells retained' );
$tiers = array();
foreach ( RollsBar_Delivery_Minimum::rules() as $r ) {
 if ( ! in_array( $r['type'], array( 'street', 'locality' ), true ) ) { continue; }
 foreach ( $r['aliases'] as $alias ) {
  $patch = 'street' === $r['type'] ? array( 'street' => $alias ) : array( 'city' => '', 'settlement' => $alias, 'settlement_fias_id' => 'fixture-settlement' );
  $data = identity( $patch ); $rule = RollsBar_Delivery_Minimum::classify( $data );
  check_rule( $rule['minimum'] === $r['minimum'], $r['cell'] . ' exact ' . $alias . ' = ' . $r['minimum'] );
  $proof = RollsBar_Delivery_Minimum::proof( $data, $alias . ', дом 1' );
  check_rule( 'resolved' === RollsBar_Delivery_Minimum::verify( $proof, $alias . ', дом 1', $r['minimum'] )['status'], 'exact threshold accepted ' . $r['cell'] );
  check_rule( 'below_minimum' === RollsBar_Delivery_Minimum::verify( $proof, $alias . ', дом 1', $r['minimum'] - 0.01 )['status'], 'one kopeck below rejected ' . $r['cell'] );
  $tiers[$r['minimum']] = true;
 }
}
check_rule( count( $tiers ) === 7, 'all seven tiers covered' );
foreach ( array( 'Кечкеметская', 'Беспалова' ) as $street ) { check_rule( 'ambiguous' === RollsBar_Delivery_Minimum::classify( identity( array( 'street' => $street, 'qc_geo' => 2 ) ) )['status'], 'imprecise split street remains callback: ' . $street ); }
foreach ( array( array( 'street' => 'Киевская', 'geo_lat'=>0, 'geo_lon'=>0 ), array( 'street' => 'Несуществующая', 'geo_lat'=>0, 'geo_lon'=>0 ), array( 'region' => 'Московская' ), array( 'city' => 'Другой', 'area' => 'Другой' ), array( 'house' => '' ), array( 'house_fias_id' => '' ), array( 'street_fias_id' => '', 'geo_lat'=>0, 'geo_lon'=>0 ) ) as $i => $patch ) { check_rule( 'resolved' !== RollsBar_Delivery_Minimum::classify( identity( $patch ) )['status'], 'unsupported identity/outside geography fail closed ' . $i ); }
foreach ( array( null, 1, 2, 3, 4, 5 ) as $precision ) { check_rule( 'resolved' !== RollsBar_Delivery_Minimum::classify( identity( array( 'qc_geo' => $precision, 'house_fias_id' => '' ) ) )['status'], 'approximate address without verified FIAS house fails closed ' . var_export( $precision, true ) ); }
$denisovka = identity(array('city'=>'','settlement'=>'Денисовка','settlement_fias_id'=>'807c873c-8913-45a8-9255-5e04c55500bd','house_fias_id'=>'3f41224e-ea1a-4314-a9df-98b16219fc5c','qc_geo'=>3));
check_rule(3000===RollsBar_Delivery_Minimum::classify($denisovka)['minimum'],'verified whole-locality FIAS house determines minimum without house coordinates');
check_rule(false===RollsBar_Geocode_Policy::evaluate(3)['allow_auto_zone'],'approximate coordinates remain forbidden for geographic zone assignment');
check_rule(1200===RollsBar_Delivery_Minimum::classify(identity(array('qc_geo'=>3)))['minimum'],'whole approved street identity is independent of geocode precision');
$denisovka['house_fias_id']='';
check_rule(null===RollsBar_Delivery_Minimum::classify($denisovka)['minimum'],'locality without verified house still fails closed');
$proof = RollsBar_Delivery_Minimum::proof( identity(), 'г Симферополь, ул Гагарина, д 1' );
check_rule( 'unresolved' === RollsBar_Delivery_Minimum::verify( $proof . 'x', 'г Симферополь, ул Гагарина, д 1', 9999 )['status'], 'tampered proof rejected' );
check_rule( 'unresolved' === RollsBar_Delivery_Minimum::verify( $proof, 'Другой адрес', 9999 )['status'], 'stale proof cannot authorize edited address' );
check_rule( 'unresolved' === RollsBar_Delivery_Minimum::verify( '', 'г Симферополь, ул Гагарина, д 1', 9999 )['status'], 'missing proof cannot authorize delivery' );
echo "DELIVERY_RULES_FIXTURE_PASS\n";

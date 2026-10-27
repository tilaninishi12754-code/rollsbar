<?php
/** Installed Woo contracts; fixtures never dispatch checkout or save an order. */
if ( ! defined( 'ABSPATH' ) ) { exit( 1 ); }
require __DIR__ . '/verify-checkout-direct-port.php';
rb_direct_assert( class_exists( 'RollsBar_Delivery_Minimum' ), 'delivery classifier loaded' );
$methods = WC()->shipping()->get_shipping_methods();
rb_direct_assert( isset( $methods['rollsbar_delivery'] ) && 'yes' === $methods['rollsbar_delivery']->enabled, 'native delivery method registered and enabled' );
rb_direct_assert( Automattic\WooCommerce\Blocks\Utils\CartCheckoutUtils::shipping_methods_exist(), 'Woo exposes native delivery/pickup control' );
rb_direct_assert( ! RollsBar_Checkout::field_locale(array())['RU']['address_1']['required'], 'pickup has no hidden required address' );

class RB_Delivery_Fixture_Cart extends WC_Cart {
 public float $fixture_amount = 0;
 public function calculate_totals() {}
 public function get_cart_contents_total() { return $this->fixture_amount; }
}
$previous_cart = WC()->cart;
$previous_chosen = WC()->session->get( 'chosen_shipping_methods', array() );
try {
 WC()->cart = new RB_Delivery_Fixture_Cart();
 $data = array( 'qc_geo' => '0', 'house' => '1', 'house_fias_id' => 'fixture-house', 'geo_lat' => '44.9', 'geo_lon' => '34.1', 'region' => 'Крым', 'area' => 'Симферопольский', 'city' => 'Симферополь', 'city_fias_id' => 'fixture-city', 'street' => 'Гагарина', 'street_fias_id' => 'fixture-street' );
 $display = 'г Симферополь, ул Гагарина, д 1';
 $request = new WP_REST_Request( 'POST', '/wc/store/v1/checkout' );
 $request->set_body_params(array('shipping_address'=>array('address_1'=>$display),'extensions'=>array('rollsbar-delivery'=>array('address_proof'=>RollsBar_Delivery_Minimum::proof($data,$display)))));
 WC()->session->set('chosen_shipping_methods',array('rollsbar_delivery'));
 foreach ( array(array(1199.99,false),array(1200,true),array(4000,true)) as $case ) {
  WC()->cart->fixture_amount=$case[0];
  $response=RollsBar_Delivery_Checkout::validate_request(null,null,$request);
  rb_direct_assert($case[1] ? null===$response : is_wp_error($response),'pre-order native delivery minimum at '.$case[0]);
 }
 $request->set_param('shipping_address',array('address_1'=>'Другой адрес'));
 rb_direct_assert(is_wp_error(RollsBar_Delivery_Checkout::validate_request(null,null,$request)),'server rejects stale proof after address edit');
 $request->set_param('extensions',array('rollsbar-delivery'=>array('minimum'=>0)));
 rb_direct_assert(is_wp_error(RollsBar_Delivery_Checkout::validate_request(null,null,$request)),'client threshold cannot authorize delivery');
 WC()->session->set('chosen_shipping_methods',array('pickup_location:0'));
 $request->set_param('shipping_address',array());
 rb_direct_assert(null===RollsBar_Delivery_Checkout::validate_request(null,null,$request),'native pickup bypasses delivery address/minimum only');
 WC()->session->set('chosen_shipping_methods',array('forged'));
 rb_direct_assert(is_wp_error(RollsBar_Delivery_Checkout::validate_request(null,null,$request)),'unknown fulfillment fails closed');
} finally {
 WC()->cart=$previous_cart;
 WC()->session->set('chosen_shipping_methods',$previous_chosen);
}
rb_direct_assert(0===$order->get_id(),'all native integration orders remain unsaved');
echo "DELIVERY_NATIVE_INTEGRATION_PASS\n";

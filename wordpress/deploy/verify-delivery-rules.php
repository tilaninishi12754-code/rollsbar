<?php
/** Installed Woo contracts; fixtures never dispatch checkout or save an order. */
if ( ! defined( 'ABSPATH' ) ) { exit( 1 ); }
require __DIR__ . '/verify-checkout-direct-port.php';
$cod = WC()->payment_gateways()->payment_gateways()['cod'];
rb_direct_assert('Наличными или картой при получении' === $cod->get_title(), 'actual native COD title supports cash and card at receipt');
rb_direct_assert('Оплатите заказ наличными или картой при получении.' === $cod->instructions, 'actual native thank-you instructions match receipt payment');
ob_start();$cod->thankyou_page();$receipt_instructions=ob_get_clean();
rb_direct_assert(str_contains($receipt_instructions,'наличными или картой')&&!str_contains($receipt_instructions,'при доставке заказа'), 'actual COD thank-you renderer has no delivery-only cash instruction');
$receipt_order = new WC_Order();$receipt_order->set_payment_method('cod');
$receipt_shipping = new WC_Order_Item_Shipping();$receipt_shipping->set_method_id('pickup_location');
$receipt_shipping->set_total(0);
$receipt_shipping->add_meta_data('pickup_location','Симферополь, Кечкеметская улица, 1');
$receipt_shipping->add_meta_data('pickup_address','Кечкеметская улица, 1, Симферополь');
$receipt_order->add_item($receipt_shipping);
$receipt_display = $receipt_order->get_shipping_to_display();
rb_direct_assert('Самовывоз: Симферополь, Кечкеметская улица, 1' === $receipt_display, 'actual native order shipping display has one pickup address and no collection translation');
rb_direct_assert('Наличными или картой при получении' === $receipt_order->get_payment_method_title(), 'existing COD order title is corrected at presentation without rewriting order');
rb_direct_assert(0 === $receipt_order->get_id() && 0 === $receipt_shipping->get_id(), 'receipt regression uses unsaved order and shipping fixtures only');
rb_direct_assert( class_exists( 'RollsBar_Delivery_Minimum' ), 'delivery classifier loaded' );
rb_direct_assert( ! WC_Validation::is_phone('+7','RU'), 'actual native phone validator rejects country prefix alone' );
rb_direct_assert( WC_Validation::is_phone('+7 (978) 000-00-00','RU'), 'actual native phone validator accepts full formatted number' );
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
$previous_mode = WC()->session->get( 'rollsbar_cart_mode', 'delivery' );
try {
 WC()->cart = new RB_Delivery_Fixture_Cart();
 WC()->session->set('rollsbar_cart_mode','pickup');
 WC()->session->set('chosen_shipping_methods',array('rollsbar_delivery'));
 RollsBar_Delivery_Checkout::choose_mode('pickup');
 rb_direct_assert(array()===WC()->session->get('chosen_shipping_methods'),'empty-cart preference clears obsolete native rate');
 $available=array('rollsbar_delivery'=>new WC_Shipping_Rate('rollsbar_delivery','Доставка',0,array(),'rollsbar_delivery'),'pickup_location:0'=>new WC_Shipping_Rate('pickup_location:0','Самовывоз',0,array(),'pickup_location'));
 rb_direct_assert('pickup_location:0'===RollsBar_Delivery_Checkout::default_method('rollsbar_delivery',$available,''),'empty-cart pickup preference initializes native pickup rate');
 rb_direct_assert('rollsbar_delivery'===RollsBar_Delivery_Checkout::default_method('rollsbar_delivery',$available,'rollsbar_delivery'),'explicit native delivery selection overrides earlier preference');
 $data = array( 'qc_geo' => '0', 'house' => '1', 'house_fias_id' => 'fixture-house', 'geo_lat' => '44.9', 'geo_lon' => '34.1', 'region' => 'Крым', 'area' => 'Симферопольский', 'city' => 'Симферополь', 'city_fias_id' => 'fixture-city', 'street' => 'Гагарина', 'street_fias_id' => 'fixture-street' );
 $display = 'г Симферополь, ул Гагарина, д 1';
 $request = new WP_REST_Request( 'POST', '/wc/store/v1/checkout' );
 $signed_proof=RollsBar_Delivery_Minimum::proof($data,$display);
 $request->set_body_params(array('billing_address'=>$address,'shipping_address'=>array_merge($address,array('address_1'=>$display)),'payment_method'=>'cod','additional_fields'=>$order_fields,'extensions'=>array('rollsbar-delivery'=>array('address_proof'=>$signed_proof))));
 RollsBar_Checkout::prepare_store_request(null,null,$request);
 $request->set_attributes(array('args'=>$args));
 rb_direct_assert(!is_wp_error($request->has_valid_params()),'actual installed Store API schema accepts signed proof extension');
 rb_direct_assert(!is_wp_error($request->sanitize_params())&&$signed_proof===$request->get_param('extensions')['rollsbar-delivery']['address_proof'],'actual native REST sanitization retains signed proof');
 rb_direct_assert(true===$native_route->validate_callback($request),'actual native field validator accepts signed delivery payload without dispatch');
 WC()->session->set('chosen_shipping_methods',array('rollsbar_delivery'));
 foreach ( array(array(1199.99,true),array(1200,true),array(4000,true)) as $case ) {
  WC()->cart->fixture_amount=$case[0];
  $response=RollsBar_Delivery_Checkout::validate_request(null,null,$request);
  rb_direct_assert($case[1] ? null===$response : is_wp_error($response),'pre-order native delivery minimum at '.$case[0]);
 }
 $request->set_param('shipping_address',array('address_1'=>'Другой адрес'));
 rb_direct_assert(null===RollsBar_Delivery_Checkout::validate_request(null,null,$request),'callback accepts edited address pending manager clarification');
 $request->set_param('extensions',array('rollsbar-delivery'=>array('minimum'=>0)));
 rb_direct_assert(null===RollsBar_Delivery_Checkout::validate_request(null,null,$request),'callback accepts absent proof without claiming confirmed delivery terms');
 $request->set_param('billing_address',array_merge($address,array('first_name'=>'','address_1'=>'')));
 $request->set_param('shipping_address',array_merge($address,array('first_name'=>'','address_1'=>'')));
 $request->set_param('additional_fields',array('rollsbar/privacy-consent'=>false));
 RollsBar_Checkout::prepare_store_request(null,null,$request);
 rb_direct_assert(true===$native_route->validate_callback($request),'actual native phone-only callback accepts absent name/address and unchecked consent');
 rb_direct_assert(null===RollsBar_Delivery_Checkout::validate_request(null,null,$request),'native phone-only delivery callback bypasses commercial minimum gate');
 WC()->session->set('chosen_shipping_methods',array('pickup_location:0'));
 $request->set_param('shipping_address',array());
 rb_direct_assert(null===RollsBar_Delivery_Checkout::validate_request(null,null,$request),'native pickup bypasses delivery address/minimum only');
 WC()->session->set('chosen_shipping_methods',array('forged'));
 rb_direct_assert(is_wp_error(RollsBar_Delivery_Checkout::validate_request(null,null,$request)),'unknown fulfillment fails closed');
} finally {
 WC()->cart=$previous_cart;
 WC()->session->set('chosen_shipping_methods',$previous_chosen);
 WC()->session->set('rollsbar_cart_mode',$previous_mode);
}
rb_direct_assert(0===$order->get_id(),'all native integration orders remain unsaved');
echo "DELIVERY_NATIVE_INTEGRATION_PASS\n";

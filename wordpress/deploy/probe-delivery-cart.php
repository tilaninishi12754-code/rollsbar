<?php
// Real WC cart/session loading regression, isolated in memory. Never invoke an order route.
$saved_cart=WC()->cart;$saved_session=WC()->session;$saved_customer=WC()->customer;$saved_actions=$GLOBALS['wp_actions'];
$saved_hooks=array_map(static fn($hook)=>clone $hook,$GLOBALS['wp_filter']);
try {
 add_filter('woocommerce_cart_session_initialize','__return_false',PHP_INT_MAX);
 foreach(array(1,10) as $quantity){
  WC()->session=new class extends WC_Session_Handler {public function __construct(){}public function save_data($old_session_key=0){}};
  WC()->customer=new WC_Customer(0);
  WC()->customer->set_billing_country('RU');WC()->customer->set_shipping_country('RU');
  WC()->customer->set_shipping_city('Симферополь');WC()->customer->set_shipping_address_1('г Симферополь, ул Балаклавская, д 1');
  $key=md5('rollsbar-in-memory-cart');
  WC()->session->set('cart',array($key=>array('key'=>$key,'product_id'=>10,'variation_id'=>0,'variation'=>array(),'quantity'=>$quantity,'line_subtotal'=>420*$quantity,'line_total'=>420*$quantity,'line_subtotal_tax'=>0,'line_tax'=>0,'line_tax_data'=>array('subtotal'=>array(),'total'=>array()))));
  WC()->session->set('chosen_shipping_methods',array('rollsbar_delivery'));
  WC()->cart=new WC_Cart();
  unset($GLOBALS['wp_actions']['woocommerce_load_cart_from_session'],$GLOBALS['wp_actions']['woocommerce_after_calculate_totals']);
  $before=WC()->cart->get_cart_contents_total();
  $data=array('region'=>'Крым','city'=>'Симферополь','area'=>'Симферопольский','street'=>'Балаклавская','street_fias_id'=>'fixture-street','house'=>'1','house_fias_id'=>'fixture-house','qc_geo'=>0,'geo_lat'=>44.9,'geo_lon'=>34.1);
  $display='г Симферополь, ул Балаклавская, д 1';
  WC()->session->set('rollsbar_delivery_address_proof',RollsBar_Delivery_Minimum::proof($data,$display));
  $request=new WP_REST_Request('POST','/wc/store/v1/checkout');$request->set_param('shipping_address',array('address_1'=>$display));
  $result=RollsBar_Delivery_Checkout::validate_request(null,null,$request);
  echo wp_json_encode(array('quantity'=>$quantity,'before_total'=>$before,'after_total'=>WC()->cart->get_cart_contents_total(),'needs_shipping'=>WC()->cart->needs_shipping(),'chosen'=>WC()->session->get('chosen_shipping_methods'),'blocked'=>is_wp_error($result),'message'=>is_wp_error($result)?$result->get_error_message():'PASS','orders_created'=>0),JSON_UNESCAPED_UNICODE)."\n";
  if(defined('ROLLSBAR_ASSERT_LOADED_CART')){
   if(abs(WC()->cart->get_cart_contents_total()-420*$quantity)>.001 || is_wp_error($result)!==($quantity===1))throw new RuntimeException('Native lazy cart minimum regression');
  }
 }
}finally{WC()->cart=$saved_cart;WC()->session=$saved_session;WC()->customer=$saved_customer;$GLOBALS['wp_actions']=$saved_actions;$GLOBALS['wp_filter']=$saved_hooks;}
echo "NATIVE_LAZY_CART_FIXTURE_NO_ORDERS\n";

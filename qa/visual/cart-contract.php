<?php
// Exercise the production mutation seam and cart-item metadata with the existing catalog adapter.
define('ROLLSBAR_CART_QA',true);
require __DIR__.'/cart-fixture.php';
$fixture_cart=new FixtureCart();$checks=0;
function check($condition,$message) { global $checks;if(!$condition)throw new Exception($message);$checks++; }
function rejected($request) { global $fixture_cart;$before=$fixture_cart->items;try{RollsBar_Cart_Actions::mutate($request);}catch(Exception $e){check($fixture_cart->items===$before,'Rejected action changed cart');return;}throw new Exception('Invalid action accepted'); }
$simple=null;$variable=null;$option_product=null;$variations=0;$options=0;$parents=0;
foreach($fixture_products as $p){
 $request=['operation'=>'add','source_id'=>$p->get_meta('_rollsbar_source_id'),'product_id'=>$p->get_id()];
 if($p->is_type('variable')){
  $variable??=$p;$parents++;
  foreach($p->get_available_variations() as $v){
   RollsBar_Cart_Actions::mutate($request+['variation_id'=>$v->get_id()]);$variations++;
   $last=end($fixture_cart->items);check($last['variation_id']===$v->get_id(),'Variation identity lost');check($last['variation']===$v->get_variation_attributes(),'Native variation attributes lost');
  }
 }elseif($p->get_meta('_rollsbar_options_json')){
  $option_product??=$p;$groups=json_decode($p->get_meta('_rollsbar_options_json'),true);
  foreach($groups[0]['choices'] as $choice){
   RollsBar_Cart_Actions::mutate($request+['options'=>[$choice]]);$options++;
   $last=end($fixture_cart->items);check($last['rollsbar_options'][0]['value']===$choice,'Option not stored in native item data');
   check(RollsBar_Cart_Actions::item_data([],$last)[0]['value']===$choice,'Option not displayed in Woo item data');
   $order=new class {public array $meta=[];function add_meta_data($k,$v){$this->meta[$k]=$v;}};
   RollsBar_Cart_Actions::order_item($order,'key',$last,null);check(in_array($choice,$order->meta,true),'Option lost in order item');
  }
 }else{$simple??=$p;}
}
check([$parents,$variations,$options]===[13,26,21],'Catalog selection coverage changed');
$r=['operation'=>'add','source_id'=>$simple->get_meta('_rollsbar_source_id'),'product_id'=>$simple->get_id()];
RollsBar_Cart_Actions::mutate($r);RollsBar_Cart_Actions::mutate($r);
check(RollsBar_Cart_Actions::snapshot()['counts']->{$r['source_id']}===2,'Repeat simple add');
$r['operation']='minus';RollsBar_Cart_Actions::mutate($r);check(RollsBar_Cart_Actions::snapshot()['counts']->{$r['source_id']}===1,'Simple decrement');
RollsBar_Cart_Actions::mutate($r);check(!isset(RollsBar_Cart_Actions::snapshot()['counts']->{$r['source_id']}),'Remove at zero');
RollsBar_Cart_Actions::mutate($r);check(!isset(RollsBar_Cart_Actions::snapshot()['counts']->{$r['source_id']}),'Repeated remove remains zero');
$r['operation']='add';rejected(array_replace($r,['source_id'=>'wrong']));rejected(array_replace($r,['product_id'=>999999]));rejected(array_replace($r,['operation'=>'unknown']));rejected($r+['variation_id'=>12345]);
$v=['operation'=>'add','source_id'=>$variable->get_meta('_rollsbar_source_id'),'product_id'=>$variable->get_id()];
rejected($v);rejected($v+['variation_id'=>999999]);
$foreign=null;foreach($fixture_products as $p)if($p!==$variable&&$p->is_type('variable')){$foreign=$p->get_available_variations()[0];break;}
rejected($v+['variation_id'=>$foreign->get_id()]);
$variable->row['variants'][0]['available']=false;rejected($v+['variation_id'=>$variable->get_available_variations()[0]->get_id()]);unset($variable->row['variants'][0]['available']);
$o=['operation'=>'add','source_id'=>$option_product->get_meta('_rollsbar_source_id'),'product_id'=>$option_product->get_id()];
rejected($o);rejected($o+['options'=>['invented sauce']]);rejected($o+['options'=>[['nested'=>'invalid']]]);
$fixture_reject_hook='woocommerce_add_to_cart_validation';rejected($r);$fixture_reject_hook=null;
RollsBar_Cart_Actions::mutate($r);$fixture_reject_hook='woocommerce_update_cart_validation';rejected(array_replace($r,['operation'=>'minus']));$fixture_reject_hook=null;
echo json_encode(['pass'=>true,'checks'=>$checks,'variable_parents'=>$parents,'variation_choices'=>$variations,'confirmed_options'=>$options,'native_cart_adapter'=>true,'live_backend_verified'=>false],JSON_PRETTY_PRINT).PHP_EOL;

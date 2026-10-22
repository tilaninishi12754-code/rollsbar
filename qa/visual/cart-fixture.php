<?php
// Local adapter for the real plugin mutation seam; NOT a live Woo/DB verification.
ob_start(); require __DIR__.'/preview.php'; ob_end_clean();
require $root.'/wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-cart-actions.php';
function absint($value) { return abs((int)$value); }
function apply_filters($hook,$value,...$args) { global $fixture_reject_hook;return $hook===$fixture_reject_hook?false:$value; }
function do_action(...$args) {}
function wc_get_product($id) {
 global $fixture_products;
 foreach($fixture_products as $p) {
  if($p->get_id()===$id)return $p;
  if($p->is_type('variable'))foreach($p->get_available_variations() as $v)if($v->get_id()===$id)return $v;
 }
 return false;
}
class FixtureCart {
 public array $items=[];
 function get_cart() { return $this->items; }
 function set_quantity($key,$qty) { if(!$qty)unset($this->items[$key]);else $this->items[$key]['quantity']=$qty;return true; }
 function add_to_cart($id,$qty,$variation,$attributes,$data) {
  $key=hash('sha256',json_encode([$id,$variation,$attributes,$data]));
  if(isset($this->items[$key]))$this->items[$key]['quantity']+=$qty;
  else $this->items[$key]=['product_id'=>$id,'variation_id'=>$variation,'variation'=>$attributes,'quantity'=>$qty]+$data;
  return $key;
 }
}
if(defined('ROLLSBAR_CART_QA'))return;
$input=json_decode(stream_get_contents(STDIN),true);
$fixture_cart=new FixtureCart();$fixture_cart->items=$input['items']??[];
try {
 $request=$input['request'];
 if(($request['operation']??'')!=='read')RollsBar_Cart_Actions::mutate($request);
 echo json_encode(['success'=>true,'data'=>RollsBar_Cart_Actions::snapshot(),'items'=>$fixture_cart->items],JSON_UNESCAPED_UNICODE);
} catch(Exception $e) {
 echo json_encode(['success'=>false,'data'=>RollsBar_Cart_Actions::snapshot()+['message'=>$e->getMessage()],'items'=>$fixture_cart->items],JSON_UNESCAPED_UNICODE);
}

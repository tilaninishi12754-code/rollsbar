<?php
// Execute production provisioning + cart paths with the deterministic local Woo adapter.
define('ROLLSBAR_CART_QA',true);
require __DIR__.'/cart-fixture.php';
$fixture_cart=new FixtureCart();$checks=0;
function verify($value,$message){global $checks;if(!$value)throw new Exception($message);$checks++;}
function must_reject($request){global $fixture_cart;$before=$fixture_cart->items;try{RollsBar_Cart_Actions::mutate($request);}catch(Exception $e){verify($before===$fixture_cart->items,'Rejected request mutated cart');return;}throw new Exception('Invalid request accepted');}
verify(count($catalog['products'])===118&&count(array_filter($fixture_products,fn($p)=>$p->get_meta('_rollsbar_upsell_only')!=='yes'))===118,'Main catalog changed');
verify(count($fixture_products)===121,'Upsells not provisioned separately');
$upsells=RollsBar_Catalog_Importer::upsell_products();verify(count($upsells)===3,'Missing hidden Woo upsells');
foreach($upsells as $p){verify($p instanceof WC_Product_Simple&&$p->get_catalog_visibility()==='hidden','Upsell visibility/type');verify($p->get_meta('_rollsbar_upsell_only')==='yes','Upsell-only metadata');verify(str_contains($p->get_meta('_rollsbar_price_provenance'),'provisional'),'Price provenance');}
$first=$upsells[0];$first->set_name('Изменённый соус');$first->set_regular_price('37');$first->update_meta_data('_rollsbar_source_image','/admin-photo.png');
$again=RollsBar_Catalog_Importer::provision_upsells();verify($again['created']===0&&$again['existing']===3&&count($fixture_products)===121,'Provisioning duplicated products');
verify($first->get_name()==='Изменённый соус'&&$first->get_price()==='37'&&$first->get_meta('_rollsbar_source_image')==='/admin-photo.png','Provisioning overwrote admin changes');
$fixture_environment='production';try{RollsBar_Catalog_Importer::provision_upsells();throw new Exception('Production provisional provisioning accepted');}catch(RuntimeException $e){verify(str_contains($e->getMessage(),'locally'),'Environment guard');}$fixture_environment='local';
$parents=0;$variations=0;$wok=0;$shrimp=0;$mutated=0;
foreach($fixture_products as $p){
 $id=$p->get_meta('_rollsbar_source_id');$r=['operation'=>'add','product_id'=>$p->get_id(),'source_id'=>$id];
 $requests=[];
 if($p->is_type('variable')){$parents++;foreach($p->get_available_variations() as $v){$requests[]=$r+['variation_id'=>$v->get_id()];$variations++;}}
 elseif($p->get_meta('_rollsbar_options_json')){foreach(json_decode($p->get_meta('_rollsbar_options_json'),true)[0]['choices'] as $choice){$requests[]=$r+['options'=>[$choice]];if(str_starts_with($id,'wok-'))$wok++;elseif($id==='shrimp-tempura')$shrimp++;}}
 else $requests[]=$r;
 foreach($requests as $request){
  RollsBar_Cart_Actions::mutate($request);$state=RollsBar_Cart_Actions::snapshot();$line=end($state['lines']);$key=$line['key'];
  verify($line['source_id']===$id,'Line parent identity');verify($line['variation_id']===($request['variation_id']??0),'Line variation identity');
  if(isset($request['options']))verify(str_contains($line['name'],$request['options'][0])&&$line['options'][0]['value']===$request['options'][0],'Option label/metadata lost');
  if(isset($request['variation_id']))verify(str_contains($line['name'],wc_get_product($request['variation_id'])->row['label']),'Variation label lost');
  $before=$fixture_cart->items;RollsBar_Cart_Actions::mutate(['operation'=>'line_plus','key'=>$key]);verify($fixture_cart->items[$key]['quantity']===2,'Line increment');
  unset($before[$key]);$others=$fixture_cart->items;unset($others[$key]);verify($before===$others,'Mutated another option/variation line');
  RollsBar_Cart_Actions::mutate(['operation'=>'line_minus','key'=>$key]);verify($fixture_cart->items[$key]['quantity']===1,'Line decrement');$mutated++;
 }
}
verify([$parents,$variations,$wok,$shrimp]===[13,26,18,3],'Exhaustive identity coverage');
$state=RollsBar_Cart_Actions::snapshot();$keys=array_column($state['lines'],'key');verify(count($keys)===count(array_unique($keys)),'Incompatible selections merged');
must_reject(['operation'=>'line_plus','key'=>'foreign-session-key']);must_reject(['operation'=>'line_remove','key'=>['invalid']]);
$key=$keys[0];$item=$fixture_cart->items[$key];$p=wc_get_product($item['variation_id']?:$item['product_id']);$p->row['stock']=1;must_reject(['operation'=>'line_plus','key'=>$key]);unset($p->row['stock']);
$p->row['sold_individually']=true;must_reject(['operation'=>'line_plus','key'=>$key]);unset($p->row['sold_individually']);
$fixture_reject_hook='woocommerce_update_cart_validation';must_reject(['operation'=>'line_remove','key'=>$key]);$fixture_reject_hook=null;
RollsBar_Cart_Actions::mutate(['operation'=>'mode','mode'=>'pickup']);verify(RollsBar_Cart_Actions::snapshot()['mode']==='pickup','Receiving preview mode not canonical');must_reject(['operation'=>'mode','mode'=>'invented']);
foreach($keys as $key)RollsBar_Cart_Actions::mutate(['operation'=>'line_remove','key'=>$key]);
$empty=RollsBar_Cart_Actions::snapshot();verify($empty['lines']===[]&&(array)$empty['counts']===[]&&str_replace("\u{00a0}",' ',$empty['subtotal'])==='0 ₽','Empty transition retained state');
echo json_encode(['pass'=>true,'checks'=>$checks,'main_products'=>118,'hidden_upsells'=>3,'variable_parents'=>$parents,'variations'=>$variations,'wok_choices'=>$wok,'shrimp_choices'=>$shrimp,'line_paths_exercised'=>$mutated,'live_backend_verified'=>false],JSON_PRETTY_PRINT).PHP_EOL;

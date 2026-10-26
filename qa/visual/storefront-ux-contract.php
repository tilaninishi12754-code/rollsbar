<?php
require __DIR__.'/cart-contract.php';
$fixture_cart=new class extends FixtureCart {
 public int $calls=0;
 function add_to_cart($id,$qty,$variation,$attributes,$data){$this->calls++;return parent::add_to_cart($id,$qty,$variation,$attributes,$data);}
};
function add_request($p,$quantity,$extra=[]){return ['operation'=>'add','source_id'=>$p->get_meta('_rollsbar_source_id'),'product_id'=>$p->get_id(),'quantity'=>$quantity]+$extra;}
RollsBar_Cart_Actions::mutate(add_request($simple,3));check($fixture_cart->calls===1,'Simple quantity sent multiple adds');check(end($fixture_cart->items)['quantity']===3,'Simple x3');
$pizza=null;foreach($fixture_products as $p)if($p->is_type('variable')&&$p->row['cat']==='pizza'){$pizza=$p;break;}
$vs=$pizza->get_available_variations();
foreach([2,3] as $i=>$qty){$before=$fixture_cart->calls;RollsBar_Cart_Actions::mutate(add_request($pizza,$qty,['variation_id'=>$vs[$i]->get_id()]));check($fixture_cart->calls===$before+1,'Pizza not atomic');check(end($fixture_cart->items)['quantity']===$qty,'Pizza quantity lost');}
$choices=json_decode($option_product->get_meta('_rollsbar_options_json'),true);
RollsBar_Cart_Actions::mutate(add_request($option_product,2,['options'=>[$choices[0]['choices'][0]]]));check(end($fixture_cart->items)['quantity']===2,'Options x2');
foreach([0,-1,1.5,'2','bad',null,true,[],PHP_INT_MAX*2.0] as $bad)rejected(add_request($simple,$bad));
rejected(add_request($pizza,2,['variation_id'=>$foreign->get_id()]));rejected(add_request($option_product,2,['options'=>['wrong']]));rejected(array_replace(add_request($simple,3),['source_id'=>'wrong']));
$fixture_cart->items=[];RollsBar_Cart_Actions::mutate(add_request($pizza,1,['variation_id'=>$vs[0]->get_id()]));
$line=RollsBar_Cart_Actions::snapshot()['lines'][0];$req=['operation'=>'line_plus','key'=>$line['key'],'source_id'=>$line['source_id'],'variation_id'=>$line['variation_id']];
rejected(array_replace($req,['source_id'=>'wrong']));rejected(array_replace($req,['variation_id'=>$vs[1]->get_id()]));
RollsBar_Cart_Actions::mutate($req);check(end($fixture_cart->items)['quantity']===2,'Exact pizza line plus');
RollsBar_Cart_Actions::mutate(add_request($pizza,3,['variation_id'=>$vs[1]->get_id()]));rejected($req);
$req['operation']='line_minus';rejected($req);
RollsBar_Cart_Actions::mutate(['operation'=>'line_remove','key'=>array_key_last($fixture_cart->items)]);
RollsBar_Cart_Actions::mutate($req);RollsBar_Cart_Actions::mutate($req);check(!$fixture_cart->items,'Pizza decrement to zero');
echo json_encode(['status'=>'PASS','checks'=>$checks,'atomic_add_calls'=>$fixture_cart->calls,'multi_size_server_safety'=>'PASS']).PHP_EOL;

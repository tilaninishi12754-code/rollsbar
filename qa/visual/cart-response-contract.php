<?php
// Exercise the real ajax boundary with shutdown deliberately not run yet.
require __DIR__.'/cart-contract.php';
class JsonSent extends Error { public function __construct(public bool $success,public array $data) {} }
function check_ajax_referer(...$args) { return true; }
function wp_unslash($v) { return $v; }
function wc_get_notices(...$args) { return []; }
function wc_clear_notices() {}
function wp_send_json_success($data) { verify_persisted($data);throw new JsonSent(true,$data); }
function wp_send_json_error($data) { verify_persisted($data);throw new JsonSent(false,$data); }
$fixture_session=new class extends FixtureSession {
 public array $persisted=[];
 public int $saves=0;
 function save_data() { $this->persisted=$this->data;$this->saves++; }
};
$fixture_cart=new class extends FixtureCart {
 function calculate_totals() { WC()->session->set('cart',$this->items); }
 function get_cart_hash() { return hash('sha256',json_encode($this->items)); }
};
function verify_persisted($data) {
 global $fixture_session,$checks;
 $persisted=$fixture_session->persisted['cart']??[];
 $quantities=array_map(fn($line)=>$line['quantity'],$persisted);
 $emitted=[];foreach($data['lines'] as $line)$emitted[$line['key']]=$line['quantity'];
 if($quantities!==$emitted)throw new Error('Response published before native session persistence');
 $checks++;
}
function ajax_request($request) {
 global $fixture_cart,$fixture_session;
 // A fresh request reads only persisted native session data, never previous RAM.
 $fixture_cart->items=$fixture_session->persisted['cart']??[];
 $_POST=['request'=>json_encode($request)];
 try {RollsBar_Cart_Actions::ajax();}catch(JsonSent $response){return $response;}
 throw new Error('No JSON response');
}
$pizza=null;foreach($fixture_products as $p)if($p->is_type('variable')&&$p->row['cat']==='pizza'){$pizza=$p;break;}
$variation=$pizza->get_available_variations()[0]->get_id();
$add=['operation'=>'add','source_id'=>$pizza->get_meta('_rollsbar_source_id'),'product_id'=>$pizza->get_id(),'variation_id'=>$variation,'quantity'=>1];
for($cycle=0;$cycle<4;$cycle++){
 $result=ajax_request($add);check($result->success,'Add response failed');$line=$result->data['lines'][0];
 check(ajax_request(['operation'=>'read'])->data['lines'][0]['quantity']===1,'Fresh read lost add');
 $exact=['operation'=>'line_plus','key'=>$line['key'],'source_id'=>$line['source_id'],'variation_id'=>$variation];
 check(ajax_request($exact)->data['lines'][0]['quantity']===2,'Exact plus failed');
 check(ajax_request(['operation'=>'read'])->data['lines'][0]['quantity']===2,'Fresh read lost plus');
 check(!ajax_request(array_replace($exact,['variation_id'=>-1]))->success,'Wrong variation accepted');
 check(ajax_request(['operation'=>'read'])->data['lines'][0]['quantity']===2,'Error response changed persistence');
 ajax_request(['operation'=>'line_remove','key'=>$line['key']]);
 check(ajax_request(['operation'=>'read'])->data['lines']===[],'Removed line resurrected');
}
echo json_encode(['status'=>'PASS','checks'=>$checks,'cycles'=>4,'saves_before_response'=>$fixture_session->saves]).PHP_EOL;

<?php
require __DIR__.'/delivery_rules_fixture.php';
function is_wp_error($v){return $v instanceof WP_Error;}
class WP_Error {function __construct(public $code,public $message,public $data=[]){} }
class WP_REST_Response {function __construct(private $data,private $status=200){}function get_data(){return $this->data;}function get_status(){return $this->status;}}
class PolicyRequest {function __construct(public $params=[],private $method='POST'){}function get_method(){return $this->method;}function get_route(){return '/wc/store/v1/checkout';}function get_param($key){return $this->params[$key]??null;}}
function WC(){return $GLOBALS['wc'];}
function wc_load_cart(){}
function is_front_page(){return $GLOBALS['front']??true;}
function is_checkout(){return false;}
function is_cart(){return false;}
class PolicySession {public $data=[];public $saves=0;function get($key,$default=null){return $this->data[$key]??$default;}function __unset($key){unset($this->data[$key]);}function save_data(){$this->saves++;}}
$GLOBALS['wc']=(object)['session'=>new PolicySession(),'cart'=>new class {public $amount=420;function get_cart_contents_total(){return $this->amount;}}];
require __DIR__.'/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php';
require __DIR__.'/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-delivery-checkout.php';
require __DIR__.'/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-address-suggestions.php';
$session=WC()->session;$session->data['chosen_shipping_methods']=['rollsbar_delivery'];
$address='г Симферополь, ул Гагарина, д 1';$proof=RollsBar_Delivery_Minimum::proof(identity(),$address);
$request=new PolicyRequest(['shipping_address'=>['address_1'=>$address],'extensions'=>['rollsbar-delivery'=>['address_proof'=>$proof]]]);
foreach([420,1199.99,1200,2000] as $amount){WC()->cart->amount=$amount;$r=RollsBar_Delivery_Checkout::validate_request(null,null,$request);check_rule(($amount<1200)===is_wp_error($r),'server enforces known minimum at '.$amount);}
WC()->cart->amount=420;$session->data['rollsbar_delivery_address_proof']=$proof;$request->params['extensions']=[];
check_rule(is_wp_error(RollsBar_Delivery_Checkout::validate_request(null,null,$request)),'saved native-session proof prevents bypass by omitting client extension');
$request->params['shipping_address']['address_1']='Улица вне справочника';
check_rule(null===RollsBar_Delivery_Checkout::validate_request(null,null,$request),'unknown edited address remains callback');
$session->data['chosen_shipping_methods']=['pickup_location:0'];$request->params['shipping_address']['address_1']=$address;
check_rule(null===RollsBar_Delivery_Checkout::validate_request(null,null,$request),'pickup ignores delivery minimum');
$note='Привезти 30.10 к 14:00';
foreach([['POST',200,'success',true],['POST',400,'failure',false],['PUT',200,'success',false],['POST',200,'pending',false]] as [$method,$status,$payment,$clear]){
 $session->data['store_api_customer_note']=$note;$session->data['contact']='preserve';
 $r=new WP_REST_Response(['order_id'=>42,'payment_result'=>['payment_status'=>$payment]],$status);
 check_rule($r===RollsBar_Checkout::clear_completed_note($r,null,new PolicyRequest([],$method)),'native response preserved');
 check_rule($clear?null===$session->get('store_api_customer_note'):$note===$session->get('store_api_customer_note'),'note cleanup only after confirmed success '.$method.' '.$status.' '.$payment);
 check_rule('preserve'===$session->get('contact'),'customer contact/session remains intact');
}
check_rule(str_contains(RollsBar_Checkout::dynamic_page_headers([])['Cache-Control'],'no-store'),'HTML never reused as stale storefront');
$GLOBALS['front']=false;check_rule([]===RollsBar_Checkout::dynamic_page_headers([]),'static/unrelated routes unchanged');
check_rule(RollsBar_Address_Suggestions::local_scope(['region'=>'Крым','city'=>'Симферополь']),'city accepted');
check_rule(RollsBar_Address_Suggestions::local_scope(['region'=>'Крым','area'=>'Симферопольский','settlement'=>'Мазанка']),'nearby villages accepted');
check_rule(!RollsBar_Address_Suggestions::local_scope(['region'=>'Москва','street'=>'Симферопольская']),'Moscow namesake excluded');
check_rule(RollsBar_Address_Suggestions::local_scope(['region'=>'Крым','area'=>'Бахчисарайский','settlement'=>'Приятное Свидание']),'explicit client-table village outside primary district retained');
check_rule(!RollsBar_Address_Suggestions::local_scope(['region'=>'Крым','area'=>'Бахчисарайский','settlement'=>'Другой посёлок']),'unrelated district results remain excluded');
$border=identity(['city'=>'','area'=>'Бахчисарайский','settlement'=>'Приятное Свидание','settlement_fias_id'=>'fixture-approved-village']);
check_rule(4000===RollsBar_Delivery_Minimum::classify($border)['minimum'],'H9 minimum retained under actual neighbouring district');
$border['settlement']='Другой посёлок';
check_rule(null===RollsBar_Delivery_Minimum::classify($border)['minimum'],'neighbouring district is not opened by village exception');
echo "CHECKOUT_POLICY_FIXTURE_PASS\n";

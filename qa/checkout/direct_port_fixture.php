<?php
// In-memory fixture. No WordPress bootstrap, database, order save, mail, or HTTP.
define('ABSPATH', __DIR__);
function __($v,$domain=''){return $v;}
function esc_html($v){return $v;}
function is_email($v){return filter_var($v,FILTER_VALIDATE_EMAIL);}
function wp_salt($v){return 'fixture-only-key';}
function is_user_logged_in(){return false;}
function is_checkout(){return true;}
function is_order_received_page(){return false;}
function wc_get_cart_url(){return 'https://staging.rollsbar.ru/cart/';}
function wc_get_checkout_url(){return 'https://staging.rollsbar.ru/checkout/';}
function wp_parse_url($url,$component){return parse_url($url,$component);}
function get_post_type_object($type){return (object)['rewrite'=>['slug'=>'product']];}
function WC(){return $GLOBALS['wc'];}
class WC_Order {public function __construct(public string $email){} public function get_billing_email(){return $this->email;}}
class Request {public array $params=[];public function get_method(){return 'POST';}public function get_route(){return '/wc/store/v1/checkout';}public function get_param($key){return $this->params[$key]??null;}public function set_param($key,$v){$this->params[$key]=$v;}}
$GLOBALS['wc']=(object)['session'=>new class {public function get_customer_id(){return 'isolated-fixture-session';}}];
require __DIR__.'/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php';
$woo=$argv[1]??(__DIR__.'/../.runtime/woo-11.1.2/woocommerce');
require $woo.'/src/StoreApi/Exceptions/RouteException.php';
require $woo.'/src/StoreApi/Utilities/OrderController.php';
function check($ok,$label){if(!$ok){throw new RuntimeException($label);}echo "PASS $label\n";}
$ref=new ReflectionClass(Automattic\WooCommerce\StoreApi\Utilities\OrderController::class);
$controller=$ref->newInstanceWithoutConstructor();$validate=$ref->getMethod('validate_email');
foreach(['','broken'] as $value){$rejected=false;try{$validate->invoke($controller,new WC_Order($value));}catch(Automattic\WooCommerce\StoreApi\Exceptions\RouteException $e){$rejected=true;}check($rejected,'real Woo 11.1.2 rejects '.($value?:'empty').' email');}
$email=RollsBar_Checkout::internal_email();
check(!RollsBar_Checkout::validate_phone(true,'+7'),'country prefix is not a complete phone');
check(RollsBar_Checkout::validate_phone(true,'+7 (978) 000-00-00'),'full formatted phone accepted');
check(!RollsBar_Checkout::validate_phone(false,'+79780000000'),'native invalid phone result is never bypassed');
$GLOBALS['wc']->customer=new class {
 public int $saved=0; public array $values=[];
 function set_billing_country($v){$this->values['country']=$v;}
 function set_shipping_country($v){$this->values['shipping_country']=$v;}
 function set_billing_email($v){$this->values['email']=$v;}
 function save(){$this->saved++;}
};
$_SERVER['HTTP_SEC_PURPOSE']='prefetch';RollsBar_Checkout::prepare_native_customer();
check(WC()->customer->saved===0&&WC()->customer->values===[],'speculative checkout does not write native customer/session');
unset($_SERVER['HTTP_SEC_PURPOSE']);RollsBar_Checkout::prepare_native_customer();
check(WC()->customer->saved===1&&WC()->customer->values['email']===$email,'actual checkout activation seeds native context');
$excluded=RollsBar_Checkout::commerce_speculation_exclusions(['/keep/*']);
check(in_array('/checkout/*',$excluded,true)&&in_array('/cart/*',$excluded,true)&&in_array('/product/*',$excluded,true),'only stateful Woo document paths excluded from speculative loading');
check(in_array('/keep/*',$excluded,true)&&!in_array('/*',$excluded,true),'existing and unrelated speculation configuration preserved');
$validate->invoke($controller,new WC_Order($email));check(true,'real Woo 11.1.2 email validator accepts internal identity');
check($email===RollsBar_Checkout::internal_email(),'deterministic per native session');
check(str_ends_with($email,'@checkout.rollsbar.invalid'),'reserved .invalid destination');
check(false===RollsBar_Checkout::block_internal_mail(null,['to'=>$email]),'technical recipient cannot reach wp_mail');
check(false===RollsBar_Checkout::block_internal_mail(null,['to'=>'operator@example.org','headers'=>['Cc: '.$email]]),'technical CC cannot reach wp_mail');
check(null===RollsBar_Checkout::block_internal_mail(null,['to'=>'operator@example.org']),'operator delivery path preserved');
$r=new Request;$r->params=['billing_address'=>['email'=>'','first_name'=>'Анна'],'create_account'=>true];RollsBar_Checkout::prepare_store_request(null,null,$r);
check($r->params['billing_address']['email']===$email&&$r->params['billing_address']['country']==='RU','native request hydrated before schema validation');
check($r->params['shipping_address']['country']==='RU','native hidden shipping country restored before validation');
check($r->params['create_account']===false,'guest cannot create account');
$l=RollsBar_Checkout::field_locale([])['RU'];
foreach(['first_name','phone'] as $key){check($l[$key]['required']&&!$l[$key]['hidden'],"$key visible required");}
check(!$l['address_1']['required']&&!$l['address_1']['hidden'],'native customer address optional for pickup; delivery proof gate requires exact address');
foreach(['last_name','company','address_2','state','postcode'] as $key){check(!$l[$key]['required']&&$l[$key]['hidden'],"$key hidden optional");}
check(!$l['city']['required']&&$l['city']['hidden'],'locality optional hidden; delivery uses one address');
check($l['country']['required']&&!$l['country']['hidden'],'native country lookup remains required; seeded RU control omitted by presentation');
file_put_contents(__DIR__.'/../visual-results/checkout-direct/locale.json',json_encode($l,JSON_UNESCAPED_UNICODE));
check(RollsBar_Checkout::pickup_locations([['name'=>'Rolls Bar']])[0]['name']==='Симферополь, Кечкеметская улица, 1','pickup exact');

$operator=RollsBar_Checkout::remove_internal_reply_headers(['to'=>'operator@example.org','headers'=>"Reply-to: <$email>\r\nContent-Type: text/html",'message'=>"Contact: $email"]);
check(null===RollsBar_Checkout::block_internal_mail(null,$operator),'operator mail preserved after technical Reply-To removal');
check(!str_contains($operator['message'],$email),'internal identity not presented as customer contact');
$display='<ul><li>Итого: 420</li><li>Email: <span>'.$email.'</span></li></ul><p>+79780000000</p><p class="woocommerce-customer-details--email">'.$email.'</p>';
$clean=RollsBar_Checkout::omit_internal_contact_html($display);
check(!str_contains($clean,'@checkout.rollsbar.invalid')&&!str_contains($clean,'Email:'),'technical contact rows absent from confirmation presentation');
check(str_contains($clean,'420')&&str_contains($clean,'+79780000000'),'native total and phone presentation preserved');
check(RollsBar_Checkout::omit_internal_contact_html('<p>operator@example.org</p>')==='<p>operator@example.org</p>','ordinary unrelated contact markup unchanged');
$validate->invoke($controller,new WC_Order($email));check(true,'presentation omission does not alter native email contract');

file_put_contents(__DIR__.'/../visual-results/checkout-direct/return-ui.js',RollsBar_Checkout::return_ui_script());

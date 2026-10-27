<?php
// In-memory fixture. No WordPress bootstrap, database, order save, mail, or HTTP.
define('ABSPATH', __DIR__);
function __($v,$domain=''){return $v;}
function esc_html($v){return $v;}
function is_email($v){return filter_var($v,FILTER_VALIDATE_EMAIL);}
function wp_salt($v){return 'fixture-only-key';}
function is_user_logged_in(){return false;}
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
foreach(['first_name','phone','address_1'] as $key){check($l[$key]['required']&&!$l[$key]['hidden'],"$key visible required");}
foreach(['last_name','company','address_2','state','postcode'] as $key){check(!$l[$key]['required']&&$l[$key]['hidden'],"$key hidden optional");}
check(!$l['city']['required']&&!$l['city']['hidden'],'locality optional visible');
file_put_contents(__DIR__.'/../visual-results/checkout-direct/locale.json',json_encode($l,JSON_UNESCAPED_UNICODE));
check(RollsBar_Checkout::pickup_locations([['name'=>'Rolls Bar']])[0]['name']==='Симферополь, Кечкеметская улица, 1','pickup exact');

$operator=RollsBar_Checkout::remove_internal_reply_headers(['to'=>'operator@example.org','headers'=>"Reply-to: <$email>\r\nContent-Type: text/html",'message'=>"Contact: $email"]);
check(null===RollsBar_Checkout::block_internal_mail(null,$operator),'operator mail preserved after technical Reply-To removal');
check(!str_contains($operator['message'],$email),'internal identity not presented as customer contact');

file_put_contents(__DIR__.'/../visual-results/checkout-direct/return-ui.js',RollsBar_Checkout::return_ui_script());

<?php
define('ABSPATH',__DIR__);define('MINUTE_IN_SECONDS',60);
function wp_salt($key){return 'fixture-only';}
function sanitize_text_field($v){return (string)$v;}
function wp_unslash($v){return $v;}
function get_transient($key){return $GLOBALS['window']??false;}
function set_transient($key,$value,$ttl){$GLOBALS['window']=$value;$GLOBALS['ttl']=$ttl;}
class WP_Error{function __construct(public $code,public $message,public $data){}}
function verify_window($ok,$message){if(!$ok)throw new RuntimeException($message);echo "PASS $message\n";}
require __DIR__.'/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-address-suggestions.php';
$method=new ReflectionMethod(RollsBar_Address_Suggestions::class,'check_rate_limit');
verify_window(true===$method->invoke(null),'new minute accepts first request');
verify_window($GLOBALS['window']['count']===1&&$GLOBALS['ttl']<=60,'first request initializes bounded minute');
$end=time()+23;$GLOBALS['window']=array('count'=>89,'expires'=>$end);
verify_window(true===$method->invoke(null),'90th request in window allowed');
verify_window($GLOBALS['window']['expires']===$end&&$GLOBALS['ttl']<=23,'further activity does not extend the minute');
$error=$method->invoke(null);verify_window($error instanceof WP_Error&&$error->data['status']===429,'91st request in same minute rejected');
verify_window($GLOBALS['window']['expires']===$end,'rejected request does not extend lockout');
$GLOBALS['window']=array('count'=>90,'expires'=>time()-1);
verify_window(true===$method->invoke(null)&&$GLOBALS['window']['count']===1,'next minute resets count without requiring inactivity');
$GLOBALS['window']=45;
verify_window(true===$method->invoke(null)&&$GLOBALS['window']['count']===46,'legacy counter migration retains request count');
echo "ADDRESS_RATE_WINDOW_FIXTURE_PASS\n";

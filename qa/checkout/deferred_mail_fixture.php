<?php
// Real installed-version Woo queue with in-memory WP/AS/order seams; no mail/DB.
namespace {
 define('ABSPATH',__DIR__);$GLOBALS['actions']=[];$GLOBALS['jobs']=[];$GLOBALS['sent']=[];
 function add_action($hook,$callback,...$args){$GLOBALS['actions'][$hook][]=$callback;}
 class WC_Order {function __construct(private int $id){} function get_id(){return $this->id;}}
 class WC_Emails {static function send_queued_transactional_email($filter,$args){$GLOBALS['sent'][]=[$filter,$args];}}
 function WC(){return new class {
  function queue(){return new class {function add(...$args){$GLOBALS['jobs'][]=$args;}};}
  function call_function($name,$id){return new WC_Order($id);}
 };}
 function verify_mail($ok,$message){if(!$ok)throw new \RuntimeException($message);echo "PASS $message\n";}
 require __DIR__.'/../.runtime/woo-11.1.2/woocommerce/src/Internal/Email/DeferredEmailQueue.php';
 $q=new \Automattic\WooCommerce\Internal\Email\DeferredEmailQueue();$q->init();
 verify_mail($q->push('woocommerce_order_status_pending_to_processing',[42,new WC_Order(42)]),'native saved-order args queue successfully');
 verify_mail(!$GLOBALS['sent']&&!$GLOBALS['jobs'],'request path sends no mail and defers durable enqueue to shutdown');
 $q->dispatch();verify_mail(count($GLOBALS['jobs'])===1,'shutdown schedules exactly one native action');
 $job=$GLOBALS['jobs'][0];
 verify_mail($job[0]==='woocommerce_send_queued_transactional_email'&&$job[2]==='woocommerce-emails','native Action Scheduler hook/group retained');
 $q->dispatch();verify_mail(count($GLOBALS['jobs'])===1,'repeated dispatch does not duplicate notification');
 $q->send_queued_transactional_email(...$job[1]);
 verify_mail(count($GLOBALS['sent'])===1&&$GLOBALS['sent'][0][1][1]->get_id()===42,'worker restores native order identity and sends original callback');
 verify_mail(!$q->push('event',[new WC_Order(0)]),'unsaved-order fixture is never scheduled');
 verify_mail(!$q->push('event',[new \stdClass()]),'unserializable args return false for Woo synchronous fallback, not silent loss');
}

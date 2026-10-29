<?php
/** Read-only inspection of the single explicitly authorized, labeled order. */
if (!defined('ABSPATH') || wp_get_environment_type()!=='staging')throw new RuntimeException('staging required');
global $wpdb;
$id=__TEST_ORDER_ID__;$order=wc_get_order($id);
if(!$order || !str_contains($order->get_customer_note(),'ТЕСТ — НЕ ГОТОВИТЬ И НЕ ЗВОНИТЬ. Один заказ разрешён владельцем'))throw new RuntimeException('not the authorized labeled test order');
$after=gmdate('Y-m-d H:i:s',$order->get_date_created()->getTimestamp()-60);
$rows=$wpdb->get_results($wpdb->prepare("SELECT action_id,status,args FROM {$wpdb->prefix}actionscheduler_actions WHERE hook=%s AND scheduled_date_gmt >= %s ORDER BY action_id DESC LIMIT 100",'woocommerce_send_queued_transactional_email',$after),ARRAY_A);
$jobs=[];foreach($rows as $row){
 $args=json_decode($row['args'],true);$matches=false;
 if(is_array($args))array_walk_recursive($args,static function($value)use($id,&$matches){if((is_int($value)||is_string($value))&&(string)$value===(string)$id)$matches=true;});
 if($matches)$jobs[]=array('action_id'=>(int)$row['action_id'],'status'=>$row['status']);
}
$sent=$order->get_new_order_email_sent();
$complete=count(array_filter($jobs,static fn($job)=>$job['status']==='complete'));
$failed=count(array_filter($jobs,static fn($job)=>$job['status']==='failed'));
$enabled=\Automattic\WooCommerce\Utilities\FeaturesUtil::feature_is_enabled('deferred_transactional_emails');
$pass=$enabled&&$sent&&$complete>=1&&$failed===0;
echo wp_json_encode(array('status'=>$pass?'PASS':'WAITING_OR_FAILURE','order_id'=>$id,'order_status'=>$order->get_status(),'payment_method'=>$order->get_payment_method(),'new_order_email_sent'=>(bool)$sent,'native_queued_jobs'=>$jobs,'feature_enabled'=>$enabled,'technical_email_reserved'=>str_ends_with($order->get_billing_email(),'@checkout.rollsbar.invalid'),'account_created'=>$order->get_customer_id()!==0,'orders_created_by_verification'=>0));

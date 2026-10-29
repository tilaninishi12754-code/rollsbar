<?php
/** Staging-only diagnostics. No orders, messages, queue jobs or option writes. */
if (!defined('ABSPATH') || wp_get_environment_type() !== 'staging') {throw new RuntimeException('staging required');}
$start=microtime(true);
$emails=WC()->mailer();
$result=array('environment'=>'staging','woo'=>WC_VERSION,
 'deferred_feature'=>get_option('woocommerce_feature_deferred_transactional_emails_enabled','no'),
 'effective_deferred'=>apply_filters('woocommerce_defer_transactional_emails',\Automattic\WooCommerce\Utilities\FeaturesUtil::feature_is_enabled('deferred_transactional_emails')),
 'sync_new_order_hook'=>has_action('woocommerce_order_status_pending_to_processing',array('WC_Emails','send_transactional_email'))!==false,
 'queued_new_order_hook'=>has_action('woocommerce_order_status_pending_to_processing',array('WC_Emails','queue_transactional_email'))!==false,
 'smtp_configured'=>RollsBar_SMTP::is_configured(),'cron_disabled'=>defined('DISABLE_WP_CRON')&&DISABLE_WP_CRON,
 'mailer_init_seconds'=>microtime(true)-$start,'smtp_connections'=>array());
foreach(array('Exception','SMTP','PHPMailer') as $class){require_once ABSPATH.WPINC.'/PHPMailer/'.$class.'.php';}
if($result['smtp_configured'])for($i=0;$i<3;$i++){
 $m=new \PHPMailer\PHPMailer\PHPMailer(true);do_action('phpmailer_init',$m);
 $m->SMTPDebug=0;$m->Timeout=12;$m->Timelimit=12;$t=microtime(true);$ok=false;
 try{$ok=$m->smtpConnect();}catch(\Throwable $error){}finally{$m->smtpClose();}
 $result['smtp_connections'][]=array('seconds'=>microtime(true)-$t,'success'=>$ok);
}
$table=$wpdb->prefix.'actionscheduler_actions';
$result['email_queue_counts']=$wpdb->get_results("SELECT status,COUNT(*) AS count FROM `$table` WHERE hook='woocommerce_send_queued_transactional_email' GROUP BY status",ARRAY_A);
$result['orders_created']=0;$result['messages_sent']=0;
echo 'MAIL_LATENCY_PROBE_BEGIN'.PHP_EOL.wp_json_encode($result).PHP_EOL.'MAIL_LATENCY_PROBE_END'.PHP_EOL;

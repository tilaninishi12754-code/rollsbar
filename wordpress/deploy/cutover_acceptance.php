<?php
// Backend persistence and message-rendering proof; all mail is intercepted.
if (!defined('WP_CLI') || !WP_CLI || home_url()!=='https://rollsbar.ru' || wp_get_environment_type()!=='production' || !defined('DISABLE_WP_CRON') || !DISABLE_WP_CRON) { throw new RuntimeException('Production preview guard'); }
add_filter('action_scheduler_allow_async_request_runner','__return_false',PHP_INT_MAX);
add_filter('pre_wp_mail',static function($result,$atts){$GLOBALS['rb_cutover_mails'][]=$atts;return true;},PHP_INT_MAX,2);
$GLOBALS['rb_cutover_mails']=array();
$check=static function($ok,$name){if(!$ok)throw new RuntimeException($name);echo $name."=PASS\n";};
$check(defined('WC_VERSION') && WC_VERSION==='11.1.2','pinned_woocommerce');
$gateways=WC()->payment_gateways()->payment_gateways();
$enabled=array_keys(array_filter($gateways,static fn($g)=>'yes'===$g->enabled));
$check($enabled===array('cod'),'receipt_payment_only');
$check(RollsBar_SMTP::is_configured(),'smtp_configuration_present');
foreach(array('Exception','SMTP','PHPMailer') as $c)require_once ABSPATH.WPINC.'/PHPMailer/'.$c.'.php';
$mailer=new \PHPMailer\PHPMailer\PHPMailer(true);do_action('phpmailer_init',$mailer);$mailer->Timeout=12;$mailer->getSMTPInstance()->Timelimit=12;$mailer->SMTPDebug=0;
$authenticated=false;
try {$authenticated=$mailer->Mailer==='smtp' && $mailer->smtpConnect();}catch(\Throwable $e){}finally{$mailer->smtpClose();}
$check($authenticated,'smtp_authentication_without_sending');
$admin=(string)get_option('admin_email');
if (str_contains($admin,'@staging.rollsbar.ru')) {
  $recipients=explode(',',(string)WC()->mailer()->get_emails()['WC_Email_New_Order']->get_recipient());
  $replacement=sanitize_email(trim($recipients[0]??''));
  if(!is_email($replacement))throw new RuntimeException('Missing production administrator contact');
  // The CLI-wide pre_wp_mail filter suppresses core's old-address change notice.
  update_option('admin_email',$replacement);
}
$order=null;$application=0;
try {
  $items=wc_get_products(array('status'=>'publish','type'=>'simple','limit'=>20));$product=null;
  foreach($items as $p){if($p->is_purchasable() && (float)$p->get_price()>0){$product=$p;break;}}
  $check($product instanceof WC_Product,'purchasable_catalog');
  $order=wc_create_order(array('status'=>'pending','customer_id'=>0,'created_via'=>'rollsbar_cutover_qa'));
  if(is_wp_error($order))throw new RuntimeException('Native order creation failed');
  $order->set_billing_first_name('ТЕСТ ПЕРЕНОСА — НЕ ГОТОВИТЬ');$order->set_billing_phone('+79990000000');
  $order->set_customer_note('Изолированная техническая проверка. Уведомления перехвачены. Запись будет удалена.');
  $order->set_payment_method('cod');$order->set_payment_method_title($gateways['cod']->title);
  $order->add_product($product,1);$order->calculate_totals();$order->save();
  $reloaded=wc_get_order($order->get_id());
  $check($reloaded && $reloaded->get_payment_method()==='cod' && $reloaded->get_billing_phone()==='+79990000000' && count($reloaded->get_items())===1,'native_order_persistence');
  $before=count($GLOBALS['rb_cutover_mails']);
  WC()->mailer()->get_emails()['WC_Email_New_Order']->trigger($order->get_id(),$order);
  $check(count($GLOBALS['rb_cutover_mails'])===$before+1,'native_order_email_render_intercepted');
  $mail=end($GLOBALS['rb_cutover_mails']);
  $check(str_contains($mail['message'],'rollsbar.ru') && !str_contains($mail['message'],'staging.rollsbar.ru'),'native_order_email_production_links');
  $locations=RollsBar_Vacancy_Page::locations();$location_id=array_key_first($locations);$location=$locations[$location_id]??null;
  $check(is_array($location),'career_locations_preserved');
  $data=RollsBar_Vacancy_Page::validate(array('location'=>$location_id,'city'=>$location['city'],'name'=>'Техническая проверка переноса','phone'=>'+79990000000','position'=>'other','consent'=>'1','comment'=>'Изолированная проверка. Не связываться; уведомления перехвачены.'));
  $check(!is_wp_error($data),'career_validation');
  $application=wp_insert_post(array('post_type'=>'rb_job_application','post_status'=>'private','post_title'=>'ТЕСТ ПЕРЕНОСА — временная запись','meta_input'=>array('_rollsbar_application'=>$data,'_rollsbar_mail_status'=>'queued')),true);
  if(is_wp_error($application))throw new RuntimeException('Career fixture save failed');
  $before=count($GLOBALS['rb_cutover_mails']);
  RollsBar_Vacancy_Page::send_application($application);
  RollsBar_Vacancy_Page::send_application($application);
  $check(get_post_status($application)==='private' && get_post_meta($application,'_rollsbar_mail_status',true)==='sent' && count($GLOBALS['rb_cutover_mails'])===$before+1,'career_private_storage_mail_idempotency');
  $mail=end($GLOBALS['rb_cutover_mails']);$headers=is_array($mail['headers'])?implode("\n",$mail['headers']):(string)$mail['headers'];
  $check($mail['to']===RollsBar_Vacancy_Page::RECIPIENT && str_contains($headers,'Cc: '.RollsBar_Vacancy_Page::COPY_RECIPIENT),'career_primary_and_copy_preserved');
  $type=get_post_type_object('rb_job_application');$check(!$type->public && !$type->publicly_queryable && !$type->show_in_rest,'career_not_public');
} finally {
  if($application && !is_wp_error($application))wp_delete_post((int)$application,true);
  if($order instanceof WC_Order)$order->delete(true);
}
echo "synthetic_order_and_application_cleanup=PASS\nexternal_messages_sent=0\n";

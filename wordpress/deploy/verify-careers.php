<?php
// Run only through staging transport; all email calls below are intercepted.
if ( wp_get_environment_type() !== 'staging' || home_url() !== 'https://staging.rollsbar.ru' ) { throw new RuntimeException('Staging only'); }
function career_assert($condition,$message) { if (!$condition) throw new RuntimeException($message); }
$locations=RollsBar_Vacancy_Page::locations();career_assert(count($locations)>=1,'Missing establishment');$id=array_key_first($locations);
$valid=['location'=>$id,'city'=>$locations[$id]['city'],'name'=>'ТЕСТ fixture','phone'=>'89781234567','position'=>'kitchen','consent'=>'1'];
$data=RollsBar_Vacancy_Page::validate($valid);career_assert(!is_wp_error($data)&&$data['phone']==='+79781234567'&&$data['address']===$locations[$id]['address'],'Canonical fields');
$cases=[['name'=>''],['phone'=>'00000000000'],['phone'=>'7123'],['phone'=>['bad']],['consent'=>''],['location'=>99999999],['city'=>'Москва'],['position'=>'invented'],['birthday'=>'2030-01-01'],['birthday'=>'2000-02-30'],['comment'=>str_repeat('а',3001)]];
foreach($cases as $case)career_assert(is_wp_error(RollsBar_Vacancy_Page::validate(array_merge($valid,$case))),'Invalid input accepted');
foreach(['rb_job_location','rb_job_application'] as $type){$t=get_post_type_object($type);career_assert(!$t->public&&!$t->publicly_queryable&&!$t->show_in_rest&&$t->cap->read_post==='manage_woocommerce','Private admin contract');}
$fixture=wp_insert_post(['post_type'=>'rb_job_location','post_status'=>'draft','post_title'=>'QA TEMP ADDRESS']);update_post_meta($fixture,'_rollsbar_job_city','Тестгород');
$mail_calls=0;$mail_result=false;$mail_filter=static function($pre,$args)use(&$mail_calls,&$mail_result){$mail_calls++;career_assert($args['to']==='stroy_business24@mail.ru','Wrong recipient');career_assert(in_array('Cc: botnetagancy@gmail.com',$args['headers'],true),'Wrong copy recipient');career_assert(str_contains($args['message'],'Адрес заведения:'),'Missing address');return $mail_result;};
$application=0;
try{
 career_assert(!isset(RollsBar_Vacancy_Page::locations()[$fixture]),'Draft leaked');wp_update_post(['ID'=>$fixture,'post_status'=>'publish']);career_assert(isset(RollsBar_Vacancy_Page::locations()[$fixture]),'Admin addition missing');
 career_assert(!is_wp_error(RollsBar_Vacancy_Page::validate(array_merge($valid,['location'=>$fixture,'city'=>'Тестгород']))),'Second city/address rejected');
 wp_update_post(['ID'=>$fixture,'post_status'=>'draft']);career_assert(is_wp_error(RollsBar_Vacancy_Page::validate(array_merge($valid,['location'=>$fixture,'city'=>'Тестгород']))),'Hidden address accepted');
 $application=wp_insert_post(['post_type'=>'rb_job_application','post_status'=>'private','post_title'=>'QA TEMP fixture','meta_input'=>['_rollsbar_application'=>$data,'_rollsbar_mail_status'=>'queued']]);
 add_filter('pre_wp_mail',$mail_filter,10,2);
 RollsBar_Vacancy_Page::send_application($application);career_assert(get_post_meta($application,'_rollsbar_mail_status',true)==='failed','Failure not saved');
 career_assert(as_next_scheduled_action(RollsBar_Vacancy_Page::MAIL_HOOK,[$application],'rollsbar-careers')!==false,'Retry missing');
 $mail_result=true;RollsBar_Vacancy_Page::send_application($application);RollsBar_Vacancy_Page::send_application($application);career_assert($mail_calls===2&&get_post_meta($application,'_rollsbar_mail_status',true)==='sent','Sent replay / retry failure');
}finally{remove_filter('pre_wp_mail',$mail_filter,10);if($application){as_unschedule_all_actions(RollsBar_Vacancy_Page::MAIL_HOOK,[$application],'rollsbar-careers');wp_delete_post($application,true);}wp_delete_post($fixture,true);}
echo "CAREERS_INTEGRATION_PASS validations=11 private_storage=yes editable_locations=yes retry=yes sent_idempotency=yes real_emails=0\n";

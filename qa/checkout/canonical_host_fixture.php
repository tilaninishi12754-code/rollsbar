<?php
define('ABSPATH',__DIR__);
function wp_get_environment_type(){return $GLOBALS['environment']??'staging';}
function home_url($path){return 'https://staging.rollsbar.ru'.$path;}
function wp_parse_url($url,$component){return parse_url($url,$component);}
require __DIR__.'/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php';
function host_check($ok,$message){if(!$ok)throw new RuntimeException($message);echo "PASS $message\n";}
foreach(['GET','HEAD'] as $method){
 host_check('https://staging.rollsbar.ru/checkout/?a=1'===RollsBar_Checkout::canonical_staging_host_target('staging.rollsbar.ru.','/checkout/?a=1',$method),'alias normalized preserving path/query '.$method);
}
foreach(['POST','PUT','DELETE'] as $method)host_check(''===RollsBar_Checkout::canonical_staging_host_target('staging.rollsbar.ru.','/?wc-ajax=rollsbar_cart',$method),'never replay mutation '.$method);
foreach(['staging.rollsbar.ru','evil.test.','staging.rollsbar.ru.evil.test.'] as $host)host_check(''===RollsBar_Checkout::canonical_staging_host_target($host,'/','GET'),'no redirect loop or unrelated host '.$host);
host_check('https://staging.rollsbar.ru/evil.test/path'===RollsBar_Checkout::canonical_staging_host_target('staging.rollsbar.ru.','//evil.test/path','GET'),'target origin cannot be supplied by request path');
$GLOBALS['environment']='production';
host_check(''===RollsBar_Checkout::canonical_staging_host_target('staging.rollsbar.ru.','/','GET'),'production excluded');

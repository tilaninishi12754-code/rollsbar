<?php
/** Exercise the actual environment/host gate without bootstrapping WordPress. */
define('ABSPATH',__DIR__);
function wp_get_environment_type(){return $GLOBALS['runtime_environment'];}
function home_url($path='/'){return $GLOBALS['runtime_home'];}
function wp_parse_url($url,$component=-1){return parse_url($url,$component);}
require __DIR__.'/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-core.php';
$cases=array(
 array('staging','https://staging.rollsbar.ru',true),
 array('staging','http://localhost',true),
 array('production','https://rollsbar.ru',true),
 array('production','https://ROLLSBAR.RU/',true),
 array('production','https://rollsbar.ru.other.example',false),
 array('production','https://unrelated.example',false),
 array('production','https://staging.rollsbar.ru',false),
 array('development','https://rollsbar.ru',false),
 array('local','https://rollsbar.ru',false),
);
foreach($cases as [$environment,$home,$expected]){
 $GLOBALS['runtime_environment']=$environment;$GLOBALS['runtime_home']=$home;
 if(RollsBar_Core::checkout_runtime_enabled()!==$expected)throw new RuntimeException('Runtime gate mismatch');
}
echo "production_runtime_gate=PASS; cases=".count($cases)."\n";

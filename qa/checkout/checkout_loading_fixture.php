<?php
define('ABSPATH',__DIR__);
function is_checkout(){return $GLOBALS['checkout']??true;}
function is_order_received_page(){return $GLOBALS['received']??false;}
function has_block($name,$id){return $GLOBALS['native']??true;}
function wc_get_page_id($name){return 42;}
function wp_dequeue_script($handle){$GLOBALS['removed'][]=$handle;}
require __DIR__.'/../../wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php';
function verify_loading($ok,$message){if(!$ok)throw new RuntimeException($message);echo "PASS $message\n";}
RollsBar_Checkout::native_checkout_scripts();
verify_loading(['wc-checkout']===($GLOBALS['removed']??[]),'only classic submission script removed on native checkout; native assets retained');
verify_loading([]===RollsBar_Checkout::checkout_resource_hints(['cart.js'],'prefetch'),'active checkout does not speculate on cart assets');
verify_loading(['keep']===RollsBar_Checkout::checkout_resource_hints(['keep'],'preconnect'),'connection hints retained');
foreach(['checkout','received','native'] as $flag){
 $GLOBALS[$flag]='received'===$flag; $GLOBALS['removed']=[];
 RollsBar_Checkout::native_checkout_scripts();
 verify_loading([]===$GLOBALS['removed'],'no classic dequeue for '.$flag.' exclusion');
 if('native'!==$flag)verify_loading(['keep']===RollsBar_Checkout::checkout_resource_hints(['keep'],'prefetch'),'other documents retain hints');
 unset($GLOBALS[$flag]);
}

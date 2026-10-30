<?php
// Public staging HTTP reads from the host, to separate PHP wait from client transport.
if(!function_exists('curl_init')){echo "HOST_TIMING_CURL_UNAVAILABLE\n";return;}
foreach(array('/','/wp-content/plugins/rollsbar-core/assets/js/checkout.js') as $path){
 for($sample=0;$sample<3;$sample++){
  $handle=curl_init('https://staging.rollsbar.ru'.$path);
  curl_setopt_array($handle,array(CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>15));
  curl_exec($handle);$info=curl_getinfo($handle);
  echo wp_json_encode(array('path'=>$path,'sample'=>$sample,'status'=>$info['http_code'],'dns'=>$info['namelookup_time'],'connect'=>$info['connect_time'],'tls'=>$info['appconnect_time']??null,'ttfb'=>$info['starttransfer_time'],'total'=>$info['total_time'],'error'=>curl_errno($handle)))."\n";
  curl_close($handle);
 }
}

<?php
// Read-only aggregate counters; no raw IP, counter key or customer data printed.
global $wpdb;
$rows=$wpdb->get_results($wpdb->prepare("SELECT option_name,option_value FROM {$wpdb->options} WHERE option_name LIKE %s LIMIT 30",$wpdb->esc_like('_transient_rb_addr_rl_').'%'),ARRAY_A);
$counters=array();foreach($rows as $row){$key=substr($row['option_name'],strlen('_transient_'));$value=maybe_unserialize($row['option_value']);$counters[]=array('count'=>is_array($value)?($value['count']??null):(int)$value,'expires_utc'=>gmdate('c',(int)get_option('_transient_timeout_'.$key,0)));}
echo wp_json_encode(array('address_rate_counters'=>$counters,'now_utc'=>gmdate('c')))."\n";

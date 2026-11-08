<?php
// Runs only in a new temporary database. Never bootstrap against source staging.
if ( ! defined('WP_CLI') || ! WP_CLI || DB_NAME !== getenv('CUTOVER_TEMP_DB') || ! preg_match('/rbdrill_[0-9]{8}$/', DB_NAME) ) { throw new RuntimeException('Temporary database guard failed'); }
global $wpdb;
$prefix=$wpdb->prefix;
if (!preg_match('/^[A-Za-z0-9_]+$/',$prefix)) { throw new RuntimeException('Invalid table prefix'); }
$admins=get_users(array('role__in'=>array('administrator','shop_manager'),'fields'=>'ID'));
$admins=array_map('intval',$admins);
if (!$admins) { throw new RuntimeException('Missing operator accounts'); }
$keep=implode(',',$admins);
$wpdb->query("DELETE FROM {$wpdb->usermeta} WHERE user_id NOT IN ($keep)");
$wpdb->query("DELETE FROM {$wpdb->users} WHERE ID NOT IN ($keep)");
$wpdb->query("DELETE FROM {$wpdb->usermeta} WHERE meta_key IN ('session_tokens','_application_passwords') OR meta_key LIKE '%persistent_cart%'");
$wpdb->query("DELETE FROM {$wpdb->posts} WHERE post_type IN ('shop_order','shop_order_refund','shop_order_placehold','shop_webhook')");
if ('rb_job_application'===get_post_type(392)) { $wpdb->delete($wpdb->posts,array('ID'=>392)); }
$wpdb->query("DELETE FROM {$wpdb->postmeta} WHERE post_id NOT IN (SELECT ID FROM {$wpdb->posts})");
$wpdb->query("DELETE FROM {$wpdb->term_relationships} WHERE object_id NOT IN (SELECT ID FROM {$wpdb->posts})");
$wpdb->query("DELETE FROM {$wpdb->comments} WHERE comment_type IN ('order_note','webhook_delivery') OR comment_post_ID NOT IN (SELECT ID FROM {$wpdb->posts})");
$wpdb->query("DELETE FROM {$wpdb->commentmeta} WHERE comment_id NOT IN (SELECT comment_ID FROM {$wpdb->comments})");
$tables=$wpdb->get_col('SHOW TABLES');
$empty=array('woocommerce_sessions','woocommerce_api_keys','woocommerce_downloadable_product_permissions','woocommerce_payment_tokens','woocommerce_payment_tokenmeta','woocommerce_log','wc_customer_lookup','wc_reserved_stock','wc_download_log','wc_webhooks');
foreach($tables as $table) {
  $suffix=substr($table,strlen($prefix));
  if (str_starts_with($suffix,'actionscheduler_') || str_starts_with($suffix,'wc_order') || in_array($suffix,$empty,true)) {
    if (!preg_match('/^[A-Za-z0-9_]+$/',$table)) { throw new RuntimeException('Unsafe table'); }
    $wpdb->query("TRUNCATE TABLE `$table`");
  }
}
$wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '\\_transient\\_%' OR option_name LIKE '\\_site\\_transient\\_%' OR option_name IN ('cron','recently_activated','auto_updater.lock','core_updater.lock')");
update_option('blogname','Rolls Bar');
update_option('blog_public','0');
update_option('woocommerce_coming_soon','no');
update_option('woocommerce_store_pages_only','no');
$products=(int)$wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type='product' AND post_status='publish'");
if ($products!==121) { throw new RuntimeException('Catalog count changed; inspect source'); }
if ((int)$wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type IN ('shop_order','shop_order_refund','shop_order_placehold')")!==0) { throw new RuntimeException('Old orders remain'); }
echo "sanitized_business_content=PASS\n";

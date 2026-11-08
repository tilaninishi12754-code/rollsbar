from cutover_prepare import run
print(run(None,'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
root="$HOME/www/rollsbar.ru"
wp --path="$root" eval 'echo wp_json_encode(array("production"=>wp_get_environment_type()==="production","home"=>home_url()==="https://rollsbar.ru","public"=>get_option("blog_public"),"cron_disabled"=>defined("DISABLE_WP_CRON")&&DISABLE_WP_CRON,"products"=>(int)wp_count_posts("product")->publish,"synthetic_orders"=>count(wc_get_orders(array("created_via"=>"rollsbar_cutover_qa","limit"=>1))),"synthetic_applications"=>(new WP_Query(array("post_type"=>"rb_job_application","post_status"=>"any","s"=>"ТЕСТ ПЕРЕНОСА","fields"=>"ids","posts_per_page"=>1)))->found_posts,"runtime"=>RollsBar_Core::checkout_runtime_enabled()));'
echo
[[ -f "$HOME/rollsbar-backups/production-live-20261108/SHA256SUMS" ]] && echo live_backup=present || echo live_backup=absent
[[ -f "$root/cutover-maintenance.html" ]] && echo maintenance_file=present || echo maintenance_file=absent
[[ -f "$HOME/.rollsbar-production-backend-verified" ]] && echo backend_proof=present || true
''',timeout=120))

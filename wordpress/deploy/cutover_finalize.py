"""Open indexing/normal cron only after explicit production verification."""
import os,json,shlex,pathlib,hashlib
from cutover_prepare import run,write_private,SECRET,RELEASE
from cutover_tls import read_state,trusted_tls

def main():
    state=read_state()
    promoted=state.get('promoted_release','')
    if state.get('release')!=RELEASE or state.get('phase')!='preview_active' or len(promoted)!=40:raise RuntimeError('Final release gate')
    if not all(trusted_tls(d) for d in ('rollsbar.ru','www.rollsbar.ru')):raise RuntimeError('Trusted TLS required')
    # Verify every tracked theme/plugin file, not only the promoted six.
    expected={str(p).removeprefix('wordpress/'):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('wordpress/wp-content/themes/rollsbar-theme','wordpress/wp-content/plugins/rollsbar-core') for p in pathlib.Path(folder).rglob('*') if p.is_file()}
    raw=run(None,'set -euo pipefail\ncd "$HOME/www/rollsbar.ru"\nfind wp-content/themes/rollsbar-theme wp-content/plugins/rollsbar-core -type f -print0 | sort -z | xargs -0 sha256sum',timeout=180)
    actual={line.split(maxsplit=1)[1]:line.split(maxsplit=1)[0] for line in raw.splitlines()}
    if any(actual.get(path)!=digest for path,digest in expected.items()):raise RuntimeError('Production application bytes mismatch')
    print('all_production_application_bytes=PASS',flush=True)
    script='''set -euo pipefail
umask 077
export PATH="$HOME/.local/bin:$PATH"
root="$HOME/www/rollsbar.ru"
[[ "$(cat "$HOME/.rollsbar-production-backend-verified")" == SOURCE_RELEASE ]]
[[ "$(cat "$HOME/.rollsbar-production-release-sha")" == PROMOTED_RELEASE ]]
[[ "$(wp --path="$root" config get WP_ENVIRONMENT_TYPE)" == production ]]
[[ "$(wp --path="$root" option get home)" == https://rollsbar.ru ]]
[[ "$(wp --path="$root" post list --post_type=product --post_status=publish --format=count)" == 121 ]]
wp --path="$root" eval 'if (wc_get_orders(array("created_via"=>"rollsbar_cutover_qa","limit"=>1))) { exit(1); } $q=new WP_Query(array("post_type"=>"rb_job_application","post_status"=>"any","s"=>"ТЕСТ ПЕРЕНОСА","fields"=>"ids","posts_per_page"=>1)); if ($q->posts) { exit(1); } echo "synthetic_fixtures_absent=PASS\\n"; if(!RollsBar_Core::checkout_runtime_enabled())exit(1);' 
wp --path="$root" option update blog_public 1 >/dev/null
wp --path="$root" config set DISABLE_WP_CRON false --raw >/dev/null
if [[ -f "$root/cutover-maintenance.html" ]]; then
 grep -q '<title>Rolls Bar</title>' "$root/cutover-maintenance.html"
 rm -- "$root/cutover-maintenance.html"
fi
wp --path="$root" rewrite flush --hard >/dev/null
[[ "$(wp --path="$root" option get blog_public)" == 1 ]]
wp --path="$root" eval 'if (!defined("DISABLE_WP_CRON") || DISABLE_WP_CRON) { exit(1); }'
[[ "$(wp --path="$HOME/www/staging.rollsbar.ru" --skip-plugins --skip-themes option get blog_public)" == 0 ]]
echo production_indexing_and_cron=PASS
backup="$HOME/rollsbar-backups/production-live-20261108"
[[ ! -e "$backup" ]]
mkdir -p "$backup"
wp --path="$root" --skip-plugins --skip-themes db export "$backup/database.sql" --quiet >/dev/null
gzip "$backup/database.sql"
tar -czf "$backup/site-files.tar.gz" -C "$root" .
printf 'production_release=%s\\nsource_release=%s\\nproducts=121\\n' PROMOTED_RELEASE SOURCE_RELEASE > "$backup/manifest.txt"
(cd "$backup"; sha256sum database.sql.gz site-files.tar.gz manifest.txt > SHA256SUMS; sha256sum -c SHA256SUMS >/dev/null)
gzip -t "$backup/database.sql.gz"
tar -tzf "$backup/site-files.tar.gz" >/dev/null
echo production_full_backup=PASS
echo staging_still_noindex=PASS
'''.replace('SOURCE_RELEASE',shlex.quote(RELEASE)).replace('PROMOTED_RELEASE',shlex.quote(promoted))
    print(run(None,script,timeout=600),flush=True)
    state['phase']='live';state['finalization_run']=os.environ.get('GITHUB_RUN_ID');write_private(None,SECRET,json.dumps(state))
    print('production_cutover_live=PASS',flush=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:print('production_finalization_failed=true; type='+type(exc).__name__);raise SystemExit(1)

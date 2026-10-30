"""Narrow staging-only release; native backup/transport and explicit file scope."""
import argparse,hashlib,json,os,shlex,subprocess
from pathlib import Path
import apply_client_media_staging as transport
from apply_storefront_ux_staging import verify
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'qa/visual-results/delivery-rules'
BASE='921698e085263f23493e8f757aa0e7c1b561946c'
PREVIOUS_APP='8db781d77f662194cd557b8f16fc94479b3bafd1'
CHANGED=[transport.PLUGIN+p for p in [
 'data/delivery-minimum.json','includes/class-rollsbar-delivery-minimum.php',
 'includes/class-rollsbar-delivery-checkout.php','includes/class-rollsbar-native-delivery-method.php',
 'rollsbar-core.php','includes/class-rollsbar-address-suggestions.php',
 'includes/class-rollsbar-checkout.php','includes/class-rollsbar-cart-actions.php',
 'assets/js/checkout.js','assets/css/checkout.css','assets/delivery-map.html','data/delivery-geography.json']]
RECEIPT='$HOME/.rollsbar-delivery-rules-release'

def verify_mail():
 order_id=os.environ.get('ROLLSBAR_MAIL_TEST_ORDER_ID','')
 if not order_id.isdecimal() or int(order_id)<=0:raise ValueError('explicit authorized test order ID required')
 php=(ROOT/'wordpress/deploy/verify-checkout-mail-queue.php').read_text().removeprefix('<?php').replace('__TEST_ORDER_ID__',str(int(order_id)))
 return f'''mail_proof="$(wp_cmd eval {shlex.quote(php)})"
printf '%s\\n' "$mail_proof"
if [[ "$mail_proof" == *'"status":"PASS"'* ]]; then
 sed -i 's/phase=native_verified_awaiting_single_authorized_order/phase=authorized_order_and_native_email_verified/' "$HOME/.rollsbar-mail-queue-release"
else
 echo MAIL_QUEUE_NOT_YET_VERIFIED
 exit 2
fi
cat "$HOME/.rollsbar-mail-queue-release"
'''

def enable_mail(sha):
 probe=(ROOT/'wordpress/deploy/probe-checkout-mail-latency.php').read_text().removeprefix('<?php')
 return f'''export WP_PATH PROJECT_ROOT
source "$PROJECT_ROOT/wordpress/deploy/prepare-s1-r2-backup.sh"
[[ "$ROLLSBAR_FRESH_BACKUP_VERIFIED" == YES ]]
mail_previous="$(wp_cmd eval 'echo get_option("woocommerce_feature_deferred_transactional_emails_enabled","no");')"
[[ "$mail_previous" == no ]]
wp_cmd eval 'if (WC_VERSION!=="11.1.2" || !class_exists("Automattic\\\\WooCommerce\\\\Internal\\\\Email\\\\DeferredEmailQueue") || !function_exists("as_enqueue_async_action")) throw new RuntimeException("native deferred email prerequisites missing");'
trap 'wp_cmd option update woocommerce_feature_deferred_transactional_emails_enabled "$mail_previous" >/dev/null' ERR
wp_cmd option update woocommerce_feature_deferred_transactional_emails_enabled yes --autoload=no
wp_cmd eval 'WC()->mailer(); if (!apply_filters("woocommerce_defer_transactional_emails",Automattic\\WooCommerce\\Utilities\\FeaturesUtil::feature_is_enabled("deferred_transactional_emails")) || !has_action("woocommerce_order_status_pending_to_processing",array("WC_Emails","queue_transactional_email")) || has_action("woocommerce_order_status_pending_to_processing",array("WC_Emails","send_transactional_email")) || !has_action("woocommerce_send_queued_transactional_email")) throw new RuntimeException("native email queue not active"); echo "NATIVE_MAIL_QUEUE_ENABLED\\n";'
trap - ERR
umask 077
printf '%s\\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" "previous=$mail_previous" 'feature=deferred_transactional_emails' 'enabled=yes' 'phase=native_verified_awaiting_single_authorized_order' > "$HOME/.rollsbar-mail-queue-release"
cat "$HOME/.rollsbar-mail-queue-release"
wp_cmd eval {shlex.quote(probe)}
'''

def scope():
 paths=subprocess.check_output(['git','diff','--name-only',BASE,'--',transport.PLUGIN,transport.THEME],cwd=ROOT,text=True).splitlines()
 if sorted(paths)!=sorted(CHANGED):raise ValueError('Delivery batch application files differ from the explicit twelve-file scope')

def backend():
 return 'wp_cmd eval-file "$PROJECT_ROOT/wordpress/deploy/verify-delivery-rules.php"\n'+verify()

def apply(sha):
 stage='';publish=''
 for path in CHANGED:
  live='$WP_PATH/'+path.removeprefix('wordpress/')
  stage+=f'mkdir -p "$(dirname "{live}")"\ninstall -m 0644 "$PROJECT_ROOT/{path}" "{live}.delivery-new"\n'
  publish+=f'mv -f "{live}.delivery-new" "{live}"\n'
 return f'''[[ -d "$PROJECT_ROOT/.git" && -z "$(git -C "$PROJECT_ROOT" status --porcelain)" ]]
{transport.code_hash_guard(sha,before=True,changed=CHANGED,base=PREVIOUS_APP)}
{verify()}
business_before="$(wp_cmd eval {shlex.quote(transport.BUSINESS_PHP)})"
git -C "$PROJECT_ROOT" fetch --depth=1 origin {sha}
git -C "$PROJECT_ROOT" checkout --detach {sha}
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == {sha} ]]
export WP_PATH PROJECT_ROOT
source "$PROJECT_ROOT/wordpress/deploy/prepare-s1-r2-backup.sh"
[[ "$ROLLSBAR_FRESH_BACKUP_VERIFIED" == YES ]]
echo DELIVERY_FRESH_BACKUP_VERIFIED
umask 077
printf '%s\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" 'phase=applying' > "{RECEIPT}"
{stage}
{publish}
{transport.code_hash_guard(sha,changed=CHANGED,base=BASE)}
wp_cmd eval 'delete_transient("wc_shipping_method_count"); WC_Cache_Helper::get_transient_version("shipping",true);'
[[ "$(wp_cmd eval {shlex.quote(transport.BUSINESS_PHP)})" == "$business_before" ]]
{backend()}
printf '%s\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" 'phase=backend_verified' > "{RECEIPT}"
echo DELIVERY_BACKEND_PASS
'''

def manifest():
 files=sorted(OUT.glob('*.png'))
 if len(files)!=20:raise ValueError('Ten modal, seven address and three adversarial screenshots required')
 reference=sorted((ROOT/'qa/visual-results/delivery-reference').glob('*.png'))
 if len(reference)!=15:raise ValueError('Five immutable reference/candidate/unmasked diff sets required')
 maps=sorted((OUT/'map').glob('*.png'))
 if len(maps)!=5:raise ValueError('Five restored-map screenshots required')
 return hashlib.sha256('\n'.join(str(p.relative_to(ROOT/'qa/visual-results'))+':'+hashlib.sha256(p.read_bytes()).hexdigest() for p in files+reference+maps).encode()).hexdigest()

def finalize(sha):
 proof=json.loads((OUT/'evidence.json').read_text(encoding='utf8'))
 if proof.get('status')!='AUTOMATED_PASS_AWAITING_SCREENSHOT_REVIEW' or proof.get('release_sha')!=sha or proof.get('mode')!='live':raise ValueError('Exact live native checkout PASS required')
 if [r['width'] for r in proof['checks']]!=[1440,701,700,390,320] or proof['submissions'] or proof['errors']:raise ValueError('Incomplete browser proof')
 if proof.get('native_presubmit',{}).get('status')!='PASS':raise ValueError('Native pre-submit assembly must PASS without HTTP submission')
 map_proof=json.loads((OUT/'map/evidence.json').read_text(encoding='utf8'))
 if map_proof.get('status')!='PASS' or map_proof.get('release_sha')!=sha or [c['width'] for c in map_proof['checks']]!=[1440,701,700,390,320] or map_proof['errors']:raise ValueError('Exact live five-width map proof required')
 addresses=json.loads((OUT/'address-evidence.json').read_text(encoding='utf8'))
 if addresses.get('status')!='PASS' or addresses.get('release_sha')!=sha:raise ValueError('Exact live provider address coverage required')
 adversarial=json.loads((OUT/'adversarial-evidence.json').read_text(encoding='utf8'))
 if adversarial.get('status')!='PASS' or adversarial.get('release_sha')!=sha or [c['width'] for c in adversarial['checks']]!=[320,700,701]:raise ValueError('Exact live adversarial pickup/reopen/precision gate required')
 reference=json.loads((ROOT/'qa/visual-results/delivery-reference/evidence.json').read_text(encoding='utf8'))
 if reference.get('release_sha')!=sha or reference.get('status')!='MODAL_CHROME_PASS_CONTENT_CHANGED_BY_OWNER' or reference.get('reference')!='5e7836e22110ec076603bb1fa2b12f8bb90ee756:index.html' or reference.get('masks')!=[]:raise ValueError('Immutable modal geometry and unmasked source diffs required')
 for path in ['original-browser.json','browser.json']:
  data=json.loads((ROOT/'qa/visual-results/storefront-ux-staging'/path).read_text(encoding='utf8'))
  if data.get('status')!='PASS' or data.get('release_sha')!=sha:raise ValueError('Exact storefront regression proof required: '+path)
 if os.environ.get('ROLLSBAR_REVIEWED_MANIFEST')!=manifest():raise ValueError('Exact screenshot set must be inspected')
 return f'''[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == {sha} ]]
{transport.code_hash_guard(sha,changed=CHANGED,base=BASE)}
grep -qx 'release={sha}' "{RECEIPT}"
grep -qx 'phase=backend_verified' "{RECEIPT}"
{backend()}
printf '%s\n' '{sha}' > "$HOME/.rollsbar-staging-deployed-sha.delivery-new"
chmod 600 "$HOME/.rollsbar-staging-deployed-sha.delivery-new"
mv -f "$HOME/.rollsbar-staging-deployed-sha.delivery-new" "$HOME/.rollsbar-staging-deployed-sha"
sed -i 's/phase=backend_verified/phase=browser_verified/' "{RECEIPT}"
cat "{RECEIPT}"
echo DELIVERY_STAGING_PASS
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['apply','inspect','finalize','manifest','probe-mail','enable-mail','verify-mail','probe-address','probe-cart'],required=True);args=p.parse_args()
 OUT.mkdir(parents=True,exist_ok=True)
 if args.phase=='manifest':print(manifest());return
 sha=transport.release_sha();scope()
 script=('wp_cmd eval '+shlex.quote((ROOT/'wordpress/deploy/probe-checkout-mail-latency.php').read_text().removeprefix('<?php'))) if args.phase=='probe-mail' else verify_mail() if args.phase=='verify-mail' else enable_mail(sha) if args.phase=='enable-mail' else apply(sha) if args.phase=='apply' else finalize(sha) if args.phase=='finalize' else f'''cat "{RECEIPT}" 2>/dev/null || true
cat "$HOME/.rollsbar-staging-deployed-sha"
git -C "$PROJECT_ROOT" rev-parse HEAD
printf 'actual_wp_version='; wp_cmd core version
printf 'actual_woo_version='; wp_cmd plugin get woocommerce --field=version
for file in database.sql.gz uploads.tar.gz manifest.txt SHA256SUMS; do
 if [[ -s "$HOME/rollsbar-backups/staging/20261023T215945Z/$file" ]]; then echo "historical_$file=present"; else echo "historical_$file=missing"; fi
done
'''
 if args.phase=='probe-address':script='wp_cmd eval '+shlex.quote((ROOT/'wordpress/deploy/probe-local-addresses.php').read_text(encoding='utf8').removeprefix('<?php'))
 if args.phase=='probe-cart':script='wp_cmd eval '+shlex.quote('\n'.join((ROOT/'wordpress/deploy'/name).read_text(encoding='utf8').removeprefix('<?php') for name in ['probe-delivery-cart.php','probe-storefront-timing.php']))
 output=transport.execute(script);(OUT/(args.phase+'.log')).write_text(output,encoding='utf8')
 if args.phase=='apply':
  if 'DELIVERY_BACKEND_PASS' not in output:raise RuntimeError('Missing backend receipt')
  target=ROOT/'qa/visual-results/storefront-ux-staging';target.mkdir(parents=True,exist_ok=True)
  (target/'media.json').write_text(output.split('UX_MEDIA_BEGIN\n')[-1].split('\nUX_MEDIA_END')[0].strip(),encoding='utf8')
if __name__=='__main__':main()

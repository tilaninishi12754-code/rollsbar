"""Narrow staging-only release; native backup/transport and explicit file scope."""
import argparse,hashlib,json,os,shlex,subprocess
from pathlib import Path
import apply_client_media_staging as transport
from apply_storefront_ux_staging import verify
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'qa/visual-results/delivery-rules'
BASE='921698e085263f23493e8f757aa0e7c1b561946c'
CHANGED=[transport.PLUGIN+p for p in [
 'data/delivery-minimum.json','includes/class-rollsbar-delivery-minimum.php',
 'includes/class-rollsbar-delivery-checkout.php','includes/class-rollsbar-native-delivery-method.php',
 'rollsbar-core.php','includes/class-rollsbar-address-suggestions.php',
 'includes/class-rollsbar-checkout.php','includes/class-rollsbar-cart-actions.php',
 'assets/js/checkout.js','assets/css/checkout.css']]
RECEIPT='$HOME/.rollsbar-delivery-rules-release'

def scope():
 paths=subprocess.check_output(['git','diff','--name-only',BASE,'--',transport.PLUGIN,transport.THEME],cwd=ROOT,text=True).splitlines()
 if sorted(paths)!=sorted(CHANGED):raise ValueError('Delivery batch application files differ from the explicit ten-file scope')

def backend():
 return 'wp_cmd eval-file "$PROJECT_ROOT/wordpress/deploy/verify-delivery-rules.php"\n'+verify()

def apply(sha):
 stage='';publish=''
 for path in CHANGED:
  live='$WP_PATH/'+path.removeprefix('wordpress/')
  stage+=f'mkdir -p "$(dirname "{live}")"\ninstall -m 0644 "$PROJECT_ROOT/{path}" "{live}.delivery-new"\n'
  publish+=f'mv -f "{live}.delivery-new" "{live}"\n'
 return f'''[[ -d "$PROJECT_ROOT/.git" && -z "$(git -C "$PROJECT_ROOT" status --porcelain)" ]]
{transport.code_hash_guard(sha,before=True,changed=CHANGED,base=BASE)}
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
 files=sorted(OUT.glob('delivery-*.png'))+sorted(OUT.glob('pickup-*.png'))
 if len(files)!=10:raise ValueError('Ten actual delivery/pickup screenshots required')
 return hashlib.sha256('\n'.join(p.name+':'+hashlib.sha256(p.read_bytes()).hexdigest() for p in files).encode()).hexdigest()

def finalize(sha):
 proof=json.loads((OUT/'evidence.json').read_text(encoding='utf8'))
 if proof.get('status')!='AUTOMATED_PASS_AWAITING_SCREENSHOT_REVIEW' or proof.get('release_sha')!=sha or proof.get('mode')!='live':raise ValueError('Exact live native checkout PASS required')
 if [r['width'] for r in proof['checks']]!=[1440,701,700,390,320] or proof['submissions'] or proof['errors']:raise ValueError('Incomplete browser proof')
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
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['apply','inspect','finalize','manifest'],required=True);args=p.parse_args()
 OUT.mkdir(parents=True,exist_ok=True)
 if args.phase=='manifest':print(manifest());return
 sha=transport.release_sha();scope()
 script=apply(sha) if args.phase=='apply' else finalize(sha) if args.phase=='finalize' else f'cat "{RECEIPT}" 2>/dev/null || true\ncat "$HOME/.rollsbar-staging-deployed-sha"\ngit -C "$PROJECT_ROOT" rev-parse HEAD\n'
 output=transport.execute(script);(OUT/(args.phase+'.log')).write_text(output,encoding='utf8')
 if args.phase=='apply':
  if 'DELIVERY_BACKEND_PASS' not in output:raise RuntimeError('Missing backend receipt')
  target=ROOT/'qa/visual-results/storefront-ux-staging';target.mkdir(parents=True,exist_ok=True)
  (target/'media.json').write_text(output.split('UX_MEDIA_BEGIN\n')[-1].split('\nUX_MEDIA_END')[0].strip(),encoding='utf8')
if __name__=='__main__':main()

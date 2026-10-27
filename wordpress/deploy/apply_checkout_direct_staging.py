"""Three-file checkout release, reusing verified staging-only transport/backup."""
import argparse,hashlib,json,os,re,shlex,subprocess
from pathlib import Path
import apply_client_media_staging as transport
from apply_storefront_ux_staging import verify
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'qa/visual-results/checkout-direct'
BASE='b481a6fa3d2db7a5524667c51d263ceb117a05d7'
PREVIOUS_APP='3a1bac237181dfc776e86e2a5c0f007d5494b3d3'
CHANGED=[transport.PLUGIN+p for p in ['assets/css/checkout.css','assets/js/checkout.js','includes/class-rollsbar-checkout.php']]
RECEIPT='$HOME/.rollsbar-checkout-direct-release'

def scope():
 paths=subprocess.check_output(['git','diff','--name-only',BASE,'--',transport.PLUGIN,transport.THEME],cwd=ROOT,text=True).splitlines()
 if sorted(paths)!=sorted(CHANGED):raise ValueError('Only the three authorized checkout app files may change')

def backend():
 return 'wp_cmd eval-file "$PROJECT_ROOT/wordpress/deploy/verify-checkout-direct-port.php"\n'+verify()

def apply(sha):
 copy=''.join(f'install -m 0644 "$PROJECT_ROOT/{p}" "$WP_PATH/{p.removeprefix("wordpress/")}.direct-new"\nmv -f "$WP_PATH/{p.removeprefix("wordpress/")}.direct-new" "$WP_PATH/{p.removeprefix("wordpress/")}"\n' for p in CHANGED)
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
echo DIRECT_PORT_FRESH_BACKUP_VERIFIED
printf '%s\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" 'phase=applying' > "{RECEIPT}"
{copy}
{transport.code_hash_guard(sha,changed=CHANGED,base=BASE)}
[[ "$(wp_cmd eval {shlex.quote(transport.BUSINESS_PHP)})" == "$business_before" ]]
{backend()}
printf '%s\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" 'phase=backend_verified' > "{RECEIPT}"
echo DIRECT_PORT_BACKEND_PASS
'''

def manifest():
 files=sorted(OUT.glob('candidate-*.png'))+sorted(OUT.glob('reference-*.png'))+sorted(OUT.glob('diff-*.png'))+sorted(OUT.glob('dadata-*.png'))
 if len(files)!=32:raise ValueError('Five top/CTA reference/candidate/diff sets plus two DaData captures required')
 return hashlib.sha256('\n'.join(p.name+':'+hashlib.sha256(p.read_bytes()).hexdigest() for p in files).encode()).hexdigest()

def finalize(sha):
 proof=json.loads((OUT/'evidence.json').read_text(encoding='utf8'))
 if proof.get('status')!='AUTOMATED_PASS_AWAITING_SCREENSHOT_REVIEW' or proof.get('release_sha')!=sha or proof.get('mode')!='live':raise ValueError('Exact live native gate must PASS')
 if [r['width'] for r in proof['checks']]!=[1440,701,700,390,320] or proof['submissions'] or proof['errors']:raise ValueError('Incomplete native proof')
 for path,count in [('browser.json',5),('interaction/browser.json',6)]:
  data=json.loads((ROOT/'qa/visual-results/storefront-ux-staging'/path).read_text(encoding='utf8'))
  if data.get('status')!='PASS' or data.get('release_sha')!=sha or len(data.get('checks',[]))!=count:raise ValueError('Exact storefront regression proof required')
 if os.environ.get('ROLLSBAR_REVIEWED_MANIFEST')!=manifest():raise ValueError('Screenshot review must identify this exact captured image set')
 return f'''[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == {sha} ]]
{transport.code_hash_guard(sha,changed=CHANGED,base=BASE)}
grep -qx 'release={sha}' "{RECEIPT}"
grep -qx 'phase=backend_verified' "{RECEIPT}"
{backend()}
printf '%s\n' '{sha}' > "$HOME/.rollsbar-staging-deployed-sha.direct-new"
chmod 600 "$HOME/.rollsbar-staging-deployed-sha.direct-new"
mv -f "$HOME/.rollsbar-staging-deployed-sha.direct-new" "$HOME/.rollsbar-staging-deployed-sha"
sed -i 's/phase=backend_verified/phase=browser_verified/' "{RECEIPT}"
cat "{RECEIPT}"
echo DIRECT_PORT_STAGING_PASS
'''

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['apply','inspect','finalize','manifest'],required=True);args=parser.parse_args()
 OUT.mkdir(parents=True,exist_ok=True)
 if args.phase=='manifest':print(manifest());return
 sha=transport.release_sha();scope()
 script=apply(sha) if args.phase=='apply' else finalize(sha) if args.phase=='finalize' else f'cat "{RECEIPT}" 2>/dev/null || true\ncat "$HOME/.rollsbar-staging-deployed-sha"\ngit -C "$PROJECT_ROOT" rev-parse HEAD\n'
 output=transport.execute(script);(OUT/(args.phase+'.log')).write_text(output,encoding='utf8')
 if args.phase=='apply':
  if 'DIRECT_PORT_BACKEND_PASS' not in output:raise RuntimeError('Missing backend receipt')
  media=output.split('UX_MEDIA_BEGIN\n')[-1].split('\nUX_MEDIA_END')[0].strip()
  (ROOT/'qa/visual-results/storefront-ux-staging').mkdir(parents=True,exist_ok=True)
  (ROOT/'qa/visual-results/storefront-ux-staging/media.json').write_text(media,encoding='utf8')
if __name__=='__main__':main()

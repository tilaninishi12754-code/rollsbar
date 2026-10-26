#!/usr/bin/env python3
"""Narrow storefront release: five code paths, no provisioners or business writes."""
import argparse
import json
import shlex
from pathlib import Path
import apply_client_media_staging as transport
from staging_catalog_audit import validate_catalog_audit

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'qa/visual-results/storefront-ux-staging'
BASE='bf2bf63a42f3b4b72ffe99a4b7c6a36493ad37a5'
CHANGED=[transport.PLUGIN+'includes/class-rollsbar-cart-actions.php',
 transport.THEME+'assets/js/app.js',transport.THEME+'assets/css/app.css',
 transport.THEME+'front-page.php',transport.THEME+'footer.php']
RECEIPT='$HOME/.rollsbar-storefront-ux-release'

def verify():
 return "wp_cmd eval "+shlex.quote(transport.CATALOG_GATE_PHP)+"; echo\necho 'UX_MEDIA_BEGIN'; wp_cmd eval-file \"$PROJECT_ROOT/wordpress/deploy/verify-client-media.php\"; echo; echo 'UX_MEDIA_END'\n"

def apply_script(sha):
 copy=''
 for path in CHANGED:
  live='$WP_PATH/'+path.removeprefix('wordpress/')
  copy+=f'install -m 0644 "$PROJECT_ROOT/{path}" "{live}.ux-new"\nmv -f "{live}.ux-new" "{live}"\n'
 return f'''
[[ -d "$PROJECT_ROOT/.git" && -z "$(git -C "$PROJECT_ROOT" status --porcelain)" ]]
{transport.code_hash_guard(sha,before=True,changed=CHANGED,base=BASE)}
{verify()}
business_before="$(wp_cmd eval {shlex.quote(transport.BUSINESS_PHP)})"
git -C "$PROJECT_ROOT" fetch --depth=1 origin {sha}
git -C "$PROJECT_ROOT" checkout --detach {sha}
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == {sha} ]]
export WP_PATH PROJECT_ROOT
source "$PROJECT_ROOT/wordpress/deploy/prepare-s1-r2-backup.sh"
[[ "$ROLLSBAR_FRESH_BACKUP_VERIFIED" == YES ]]
echo 'UX_BACKUP_VERIFIED_BEFORE_MUTATION'
umask 077
printf '%s\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" 'phase=applying' > "{RECEIPT}"
{copy}
{transport.code_hash_guard(sha,changed=CHANGED,base=BASE)}
[[ "$(sha256sum "$WP_PATH/wp-content/plugins/rollsbar-core/data/catalog.json" | cut -d ' ' -f 1)" == "$(sha256sum "$PROJECT_ROOT/wordpress/data/catalog.json" | cut -d ' ' -f 1)" ]]
[[ "$(wp_cmd eval {shlex.quote(transport.BUSINESS_PHP)})" == "$business_before" ]]
echo "business_data_sha256=$business_before"
{verify()}
printf '%s\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" 'phase=backend_verified' > "{RECEIPT}"
echo 'UX_BACKEND_PASS'
'''

def finalize_script(sha):
 return f'''
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == {sha} ]]
[[ -z "$(git -C "$PROJECT_ROOT" status --porcelain)" ]]
{transport.code_hash_guard(sha,changed=CHANGED,base=BASE)}
grep -qx 'release={sha}' "{RECEIPT}"
grep -qx 'phase=backend_verified' "{RECEIPT}"
{verify()}
umask 077
printf '%s\n' '{sha}' > "$HOME/.rollsbar-staging-deployed-sha.ux-new"
chmod 600 "$HOME/.rollsbar-staging-deployed-sha.ux-new"
mv -f "$HOME/.rollsbar-staging-deployed-sha.ux-new" "$HOME/.rollsbar-staging-deployed-sha"
sed -i 's/phase=backend_verified/phase=browser_verified/' "{RECEIPT}"
cat "{RECEIPT}"
echo 'UX_RELEASE_PASS'
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['apply','finalize','inspect'],required=True);args=p.parse_args()
 sha=transport.release_sha();OUT.mkdir(parents=True,exist_ok=True)
 if args.phase=='finalize':
  proof=json.loads((OUT/'browser.json').read_text(encoding='utf-8'))
  if proof.get('status')!='PASS' or proof.get('release_sha')!=sha or len(proof.get('checks',[]))!=5:raise ValueError('Exact release browser PASS required')
 script=apply_script(sha) if args.phase=='apply' else finalize_script(sha) if args.phase=='finalize' else f'cat "{RECEIPT}" 2>/dev/null || true\ncat "$HOME/.rollsbar-staging-deployed-sha"\ngit -C "$PROJECT_ROOT" rev-parse HEAD\n'+verify()
 output=transport.execute(script)
 (OUT/(args.phase+'.log')).write_text(output,encoding='utf-8')
 if args.phase=='apply':
  if 'UX_BACKEND_PASS' not in output:raise RuntimeError('No backend receipt')
  audits=[json.loads(line) for line in output.splitlines() if line.startswith('{"host":')]
  if len(audits)!=2:raise ValueError('Two catalog audits required')
  for a in audits:validate_catalog_audit(a)
  proofs=output.split('UX_MEDIA_BEGIN\n')[1:]
  for text in proofs:
   proof=json.loads(text.split('\nUX_MEDIA_END')[0].strip())
   if proof['counts']!={'assets':36,'preserved_rows':61,'resolved_rows':57,'resolved_source_ids':45,'deferred_rows':4,'deferred_products':2}:raise ValueError('Media canon changed')
  (OUT/'catalog.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
  (OUT/'media.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Narrow storefront release: five code paths, no provisioners or business writes."""
import argparse
import json
import shlex
import subprocess
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

CONTROLS_BASE='2ad7e69c690b21bb33ff48c6c92119b01ea8a218'
CONTROL_RULE='\n@media(min-width:701px) and (max-width:900px){.client-back-top{bottom:calc(86px + env(safe-area-inset-bottom))}}\n'

def require_control_delta():
 """Reuse previous full acceptance only for this exact additive tablet CSS fix."""
 global BASE, CHANGED
 css=transport.THEME+'assets/css/app.css'
 paths=subprocess.check_output(['git','diff','--name-only',CONTROLS_BASE,'--',transport.THEME,transport.PLUGIN],cwd=ROOT,text=True).splitlines()
 previous=subprocess.check_output(['git','show',CONTROLS_BASE+':'+css],cwd=ROOT,text=True)
 if paths!=[css] or (ROOT/css).read_text(encoding='utf-8')!=previous+CONTROL_RULE:
  raise ValueError('Focused acceptance requires the exact CSS-only delta from verified full release')
 BASE=CONTROLS_BASE; CHANGED=[css]

def require_interaction_delta():
 global BASE, CHANGED
 BASE='328cb664d1d6e6a63b300e6788a984497fa1320d'
 CHANGED=[transport.THEME+'assets/css/app.css',transport.THEME+'assets/js/app.js']
 paths=subprocess.check_output(['git','diff','--name-only',BASE,'--',transport.THEME,transport.PLUGIN],cwd=ROOT,text=True).splitlines()
 if sorted(paths)!=sorted(CHANGED):raise ValueError('Interaction release permits only storefront JS/CSS changes')

def verify_interaction_proof(sha):
 proof=json.loads((OUT/'interaction/browser.json').read_text(encoding='utf-8'))
 if proof.get('status')!='PASS' or proof.get('release_sha')!=sha or [(c.get('engine'),c.get('width')) for c in proof.get('checks',[])]!=[('chromium',w) for w in [320,390,430,701,900,1440]]:
  raise ValueError('Exact release interaction stress PASS at all six widths required')

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
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['apply','finalize','inspect'],required=True);p.add_argument('--controls-only',action='store_true');p.add_argument('--interaction-stability',action='store_true');args=p.parse_args()
 if args.interaction_stability:
  if args.controls_only:raise ValueError('Choose one release scope')
  require_interaction_delta()
 if args.controls_only:require_control_delta()
 sha=transport.release_sha();OUT.mkdir(parents=True,exist_ok=True)
 if args.phase=='finalize':
  if args.interaction_stability:verify_interaction_proof(sha)
  proof=json.loads((OUT/'browser.json').read_text(encoding='utf-8'))
  if args.controls_only and (proof.get('inherited_full_acceptance_sha')!=CONTROLS_BASE or proof.get('scope')!='floating-controls-701-900' or [c.get('width') for c in proof.get('checks',[])]!=[701,900]):raise ValueError('Focused browser proof must cover both changed breakpoints and verified base')
  if proof.get('status')!='PASS' or proof.get('release_sha')!=sha or len(proof.get('checks',[]))!=(2 if args.controls_only else 5):raise ValueError('Exact release browser PASS required')
 script=apply_script(sha) if args.phase=='apply' else finalize_script(sha) if args.phase=='finalize' else f'cat "{RECEIPT}" 2>/dev/null || true\ncat "$HOME/.rollsbar-staging-deployed-sha"\ngit -C "$PROJECT_ROOT" rev-parse HEAD\n'+verify()
 if args.controls_only and args.phase=='apply':script=f'[[ \"$(cat \"$HOME/.rollsbar-staging-deployed-sha\")\" == {CONTROLS_BASE} ]]\n'+script
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

#!/usr/bin/env python3
"""Fixed media-only release through the existing staging transport/backup architecture.

One exec request per phase, no mutating request retry. Failures require actual
state inspection. Checkout files and non-media business data are hash-guarded.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

from staging_catalog_audit import AUDIT_PHP, parse_audit, validate_catalog_audit
from staging_ssh import connect
from inspect_staging_release import sanitize

ROOT = Path(__file__).resolve().parents[2]
BASE = '4b1b9ef56b1cc8cd10586a88b543e9865f934b67'
BRANCH = 'wordpress/checkout-visual-parity-2026-10-25'
REPO = 'https://github.com/tilaninishi12754-code/rollsbar.git'
PREFIX = '''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="$HOME/www/staging.rollsbar.ru"
PROJECT_ROOT="$HOME/.rollsbar-deploy"
wp_cmd(){ wp --path="$WP_PATH" "$@"; }
[[ -f "$WP_PATH/wp-load.php" && ! -L "$WP_PATH" ]]
[[ "$(wp_cmd option get home)" == 'https://staging.rollsbar.ru' ]]
[[ "$(wp_cmd option get siteurl)" == 'https://staging.rollsbar.ru' ]]
[[ "$(wp_cmd eval 'echo wp_get_environment_type();')" == 'staging' ]]
[[ "$(wp_cmd option get blog_public)" == '0' ]]
'''
PLUGIN = 'wordpress/wp-content/plugins/rollsbar-core/'
THEME = 'wordpress/wp-content/themes/rollsbar-theme/'
CHANGED = [PLUGIN + 'includes/class-rollsbar-client-media.php', PLUGIN + 'includes/class-rollsbar-catalog-importer.php',
           THEME + 'functions.php', PLUGIN + 'rollsbar-core.php']
BUSINESS_PHP = r'''$rows=[];foreach(get_posts(['post_type'=>['product','product_variation'],'post_status'=>array_values(get_post_stati([],'names')),'numberposts'=>-1,'fields'=>'ids','orderby'=>'ID','order'=>'ASC']) as $id){$p=wc_get_product($id);$d=$p->get_data();unset($d['image_id'],$d['date_modified'],$d['date_created']);$meta=[];foreach($p->get_meta_data() as $m){$v=$m->get_data();if(str_starts_with($v['key'],'_rollsbar_client_media_'))continue;$meta[$v['key']]=$v['value'];}ksort($meta);$d['meta_data']=$meta;$rows[$id]=$d;}echo hash('sha256',wp_json_encode($rows));'''
CATALOG_GATE_PHP = AUDIT_PHP + r'''if(count($canonicalIds)!==118||$canonicalMissing!==0||$canonicalDuplicates!==0||$canonicalMarked!==0||$canonicalWrongStatus!==0||$parents!==13||$variations!==26||$actualVariationPosts!==26||$variationMismatches!==0||$blankAttrs!==0||count($upsellPosts)!==3||$upsellDuplicates!==0||$identityMismatches!==0||$wrongType!==0||$wrongVisibility!==0||$wrongStatus!==0||$missingProvenance!==0||$published!==121||$unexpectedPublished!==0){throw new RuntimeException('Catalog pre-mutation contract failed');}'''


def release_sha():
    sha = os.environ.get('ROLLSBAR_DEPLOY_SHA', '')
    if not re.fullmatch('[0-9a-f]{40}', sha) or os.environ.get('GITHUB_REF_NAME') != BRANCH:
        raise ValueError('Requires exact release SHA and authorized feature branch')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != sha:
        raise ValueError('Actions checkout differs from release SHA')
    return sha


def execute(script):
    client = connect()
    try:
        stdin, out, err = client.exec_command('bash -lc ' + shlex.quote('exec bash -s'), timeout=850)
        stdin.write(PREFIX + script + '\n'); stdin.flush(); stdin.channel.shutdown_write()
        output = out.read().decode('utf-8', 'replace')
        errors = err.read().decode('utf-8', 'replace')
        code = out.channel.recv_exit_status()
        print(sanitize(output, 150000), flush=True)
        if code:
            raise RuntimeError(f'Media phase failed exit={code}; inspect actual state before retry. stderr=' + sanitize(errors, 6000))
        return output
    finally:
        client.close()


def code_hash_guard(sha, before=False, *, changed=None, base=BASE):
    """Compare every tracked app file; only these four paths may differ before release."""
    lines = []
    changed = CHANGED if changed is None else changed
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', sha, '--', PLUGIN, THEME], cwd=ROOT, text=True).splitlines()
    for path in paths:
        live = '$WP_PATH/' + path.removeprefix('wordpress/')
        incoming = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if before and path in changed:
            try:
                previous = hashlib.sha256(subprocess.check_output(['git','show',base+':'+path], cwd=ROOT, stderr=subprocess.DEVNULL)).hexdigest()
                lines.append(f'actual="$(sha256sum "{live}" | cut -d " " -f 1)"; [[ "$actual" == {incoming} || "$actual" == {previous} ]]')
            except subprocess.CalledProcessError:
                lines.append(f'[[ ! -e "{live}" ]] || [[ "$(sha256sum "{live}" | cut -d " " -f 1)" == {incoming} ]]')
        else:
            lines.append(f'[[ "$(sha256sum "{live}" | cut -d " " -f 1)" == {incoming} ]]')
    return '\n'.join(lines) + '\n'


def apply_script(sha):
    # No bootstrap/repair/business provisioners: this is a narrow media-only operation.
    copy = ''
    for path in CHANGED:
        relative = path.removeprefix('wordpress/')
        copy += f'install -m 0644 "$PROJECT_ROOT/{path}" "$WP_PATH/{relative}.media-new"\nmv -f "$WP_PATH/{relative}.media-new" "$WP_PATH/{relative}"\n'
    return f'''
echo 'media_phase=read_only_preflight'
[[ -d "$PROJECT_ROOT/.git" && -z "$(git -C "$PROJECT_ROOT" status --porcelain)" ]]
wp_cmd eval {shlex.quote(CATALOG_GATE_PHP)}; echo
{code_hash_guard(sha, before=True)}
business_before="$(wp_cmd eval {shlex.quote(BUSINESS_PHP)})"
checkout_before="$(sha256sum "$WP_PATH/wp-content/plugins/rollsbar-core/assets/css/checkout.css" "$WP_PATH/wp-content/plugins/rollsbar-core/assets/js/checkout.js" "$WP_PATH/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php")"
git -C "$PROJECT_ROOT" fetch --depth=1 origin {sha}
git -C "$PROJECT_ROOT" checkout --detach {sha}
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == {sha} ]]
export WP_PATH PROJECT_ROOT
source "$PROJECT_ROOT/wordpress/deploy/prepare-s1-r2-backup.sh"
[[ "$ROLLSBAR_FRESH_BACKUP_VERIFIED" == YES ]]
echo 'media_phase=backup_verified_before_site_mutation'
umask 077
printf '%s\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" 'phase=applying' > "$HOME/.rollsbar-client-media-release"
mkdir -p "$WP_PATH/wp-content/plugins/rollsbar-core/data/product-media"
cp -a "$PROJECT_ROOT/wordpress/data/product-media/client-2026-10-21" "$WP_PATH/wp-content/plugins/rollsbar-core/data/product-media/"
{copy}
{code_hash_guard(sha)}
[[ "$(sha256sum "$WP_PATH/wp-content/plugins/rollsbar-core/data/catalog.json" | cut -d ' ' -f 1)" == "$(sha256sum "$PROJECT_ROOT/wordpress/data/catalog.json" | cut -d ' ' -f 1)" ]]
wp_cmd rollsbar media validate
echo 'MEDIA_DRY_RUN'; wp_cmd rollsbar media sync --dry-run --confirm-staging
echo 'MEDIA_FIRST_SYNC'; wp_cmd rollsbar media sync --confirm-staging
echo 'MEDIA_SECOND_SYNC'; wp_cmd rollsbar media sync --confirm-staging
business_after="$(wp_cmd eval {shlex.quote(BUSINESS_PHP)})"
[[ "$business_after" == "$business_before" ]]
[[ "$(sha256sum "$WP_PATH/wp-content/plugins/rollsbar-core/assets/css/checkout.css" "$WP_PATH/wp-content/plugins/rollsbar-core/assets/js/checkout.js" "$WP_PATH/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php")" == "$checkout_before" ]]
echo "business_data_sha256=$business_after"
echo 'checkout_unchanged=PASS'
wp_cmd eval {shlex.quote(AUDIT_PHP)}; echo
echo 'MEDIA_PROOF_BEGIN'; wp_cmd eval-file "$PROJECT_ROOT/wordpress/deploy/verify-client-media.php"; echo; echo 'MEDIA_PROOF_END'
printf '%s\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" 'phase=applied_backend_verified' > "$HOME/.rollsbar-client-media-release"
echo 'MEDIA_BACKEND_PASS'
'''


def inspect_script():
    return '''
echo 'media_release_receipt'; if [[ -f "$HOME/.rollsbar-client-media-release" ]]; then cat "$HOME/.rollsbar-client-media-release"; fi
echo 'repo_head'; git -C "$PROJECT_ROOT" rev-parse HEAD
echo 'deployed_marker'; cat "$HOME/.rollsbar-staging-deployed-sha"
echo 'media_lock'; wp_cmd option get rollsbar_client_media_sync_lock || true
if [[ -f "$WP_PATH/wp-content/plugins/rollsbar-core/includes/class-rollsbar-client-media.php" ]]; then
  wp_cmd rollsbar media sync --dry-run --confirm-staging
fi
'''


def finalize_script(sha):
    return f'''
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == {sha} ]]
[[ -z "$(git -C "$PROJECT_ROOT" status --porcelain)" ]]
{code_hash_guard(sha)}
grep -qx 'release={sha}' "$HOME/.rollsbar-client-media-release"
grep -qx 'phase=applied_backend_verified' "$HOME/.rollsbar-client-media-release"
wp_cmd rollsbar media sync --dry-run --confirm-staging
wp_cmd eval {shlex.quote(AUDIT_PHP)}; echo
echo 'MEDIA_PROOF_BEGIN'; wp_cmd eval-file "$PROJECT_ROOT/wordpress/deploy/verify-client-media.php"; echo; echo 'MEDIA_PROOF_END'
umask 077
printf '%s\n' '{sha}' > "$HOME/.rollsbar-staging-deployed-sha.media-new"
chmod 600 "$HOME/.rollsbar-staging-deployed-sha.media-new"
mv -f "$HOME/.rollsbar-staging-deployed-sha.media-new" "$HOME/.rollsbar-staging-deployed-sha"
sed -i 's/phase=applied_backend_verified/phase=browser_verified/' "$HOME/.rollsbar-client-media-release"
echo 'MEDIA_RELEASE_PASS'
'''


def main():
    p = argparse.ArgumentParser(); p.add_argument('--phase', choices=['apply','inspect','finalize'], default='apply'); args=p.parse_args()
    sha=release_sha()
    evidence=ROOT/'qa/visual-results/client-media'; evidence.mkdir(parents=True,exist_ok=True)
    if args.phase == 'finalize':
        browser=json.loads((evidence/'browser.json').read_text(encoding='utf-8'))
        if browser.get('status') != 'PASS' or browser.get('release_sha') != sha:
            raise ValueError('Browser evidence must PASS this exact release before marker promotion')
    output=execute(apply_script(sha) if args.phase=='apply' else finalize_script(sha) if args.phase=='finalize' else inspect_script())
    (evidence/(args.phase+'.log')).write_text(sanitize(output,150000),encoding='utf-8')
    if args.phase == 'apply':
        if 'MEDIA_BACKEND_PASS' not in output: raise RuntimeError('Missing backend pass receipt')
        proof=json.loads(output.split('MEDIA_PROOF_BEGIN\n')[1].split('\nMEDIA_PROOF_END')[0].strip())
        if proof['counts'] != {'assets':36,'preserved_rows':61,'resolved_rows':57,'resolved_source_ids':45,'deferred_rows':4,'deferred_products':2}: raise RuntimeError('Wrong live counts')
        successes=[json.loads(line.removeprefix('Success: ')) for line in output.splitlines() if line.startswith('Success: {')]
        dry, first, second=successes[-3:]
        if second['created'] != 0 or second['assigned'] != 0 or second['unchanged'] != 45 or second['reused'] != 36: raise RuntimeError('Live second sync is not idempotent')
        audits=[json.loads(line) for line in output.splitlines() if line.startswith('{"host":')]
        for audit in audits: validate_catalog_audit(audit)
        if len(audits)!=2: raise RuntimeError('Both before/after catalog audits required')
        proof.update({'release_sha':sha,'dry_run':dry,'first_sync':first,'second_sync':second})
        (evidence/'staging.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()

"""Fixed staging recovery inspection; sole mutation is safe stale-runtime removal."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

from staging_catalog_audit import AUDIT_PHP, parse_audit, validate_catalog_audit
from staging_ssh import connect, probe, cleanup_files, RUNTIME_FILE

OLD = '88826907fc7ffe805a7c47f36c35a74c0049e08e'
INCOMING = '7a8809379d1dd781ce706b552f68579a9ea09d54'
PROTECTED = '20261023T215945Z'
BRANCH = 'wordpress/checkout-visual-parity-2026-10-25'
ROOT = Path(__file__).resolve().parents[2]
PREFIX = '''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export GIT_OPTIONAL_LOCKS=0
WP_PATH="$HOME/www/staging.rollsbar.ru"
'''
IDENTITY = PREFIX + '''
printf 'marker='; cat "$HOME/.rollsbar-staging-deployed-sha"; printf '\\n'
printf 'repo_head='; git -C "$HOME/.rollsbar-deploy" rev-parse HEAD
echo 'repo_status_begin'
git -C "$HOME/.rollsbar-deploy" status --short
echo 'repo_status_end'
printf 'home='; wp --path="$WP_PATH" option get home
printf 'siteurl='; wp --path="$WP_PATH" option get siteurl
printf 'environment='; wp --path="$WP_PATH" eval 'echo wp_get_environment_type();'; printf '\\n'
printf 'wordpress='; wp --path="$WP_PATH" core version
printf 'woocommerce='; wp --path="$WP_PATH" plugin get woocommerce --field=version
printf 'theme='; wp --path="$WP_PATH" theme get rollsbar-theme --field=status
printf 'plugin='; wp --path="$WP_PATH" plugin get rollsbar-core --field=status
printf 'blog_public='; wp --path="$WP_PATH" option get blog_public
'''
ASSETS = PREFIX + '''
for asset in css/checkout.css js/checkout.js; do
  path="$WP_PATH/wp-content/plugins/rollsbar-core/assets/$asset"
  [[ -f "$path" && ! -L "$path" ]]
  printf 'asset=%s sha256=' "$asset"; sha256sum "$path" | cut -d ' ' -f 1
done
'''
BACKUPS = PREFIX + r'''
root="$HOME/rollsbar-backups/staging"
[[ -d "$root" && ! -L "$root" ]]
echo 'backup_names_begin'
find "$root" -mindepth 1 -maxdepth 1 -name '20??????T??????Z' -printf '%f\n' | LC_ALL=C sort
echo 'backup_names_end'
echo 'backup_partial_names_begin'
find "$root" -mindepth 1 -maxdepth 1 \( -name '.backup-staging.lock' -o -name '.tmp-*' \) -printf '%f\n'
echo 'backup_partial_names_end'
for name in $(find "$root" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -printf '%f\n' | LC_ALL=C sort); do
  [[ "$name" =~ ^20[0-9]{6}T[0-9]{6}Z$ ]] || exit 1
  path="$root/$name"
  [[ ! -L "$path" ]]
  if [[ ! -s "$path/database.sql.gz" || ! -s "$path/uploads.tar.gz" || ! -s "$path/manifest.txt" || ! -s "$path/SHA256SUMS" ]]; then
    echo "snapshot=$name incomplete"; continue
  fi
  echo "snapshot_begin=$name"
  grep -E '^(created_utc|project_code_commit|site_url|wordpress_version|woocommerce_version|published_products)=' "$path/manifest.txt"
  if [[ "$name" == '20261023T215945Z' || "$name" > '20261025T151212Z' ]]; then
    (cd "$path"; sha256sum -c SHA256SUMS; gzip -t database.sql.gz; tar -tzf uploads.tar.gz >/dev/null)
    echo "snapshot_verified=$name"
  fi
  echo "snapshot_end=$name"
done
'''


def execute(script, connector=connect):
    """Fresh exec-only transport and short SSH request; script goes via stdin."""
    client = connector()
    try:
        stdin, out, err = client.exec_command('bash -s', timeout=180)
        stdin.write(script)
        stdin.channel.shutdown_write()
        body = out.read().decode('utf-8', errors='replace')
        err.read()
        status = out.channel.recv_exit_status()
        if status:
            raise RuntimeError('Read-only inspection command failed, exit=' + str(status))
        return body
    finally:
        client.close()


def expected_hashes():
    return {sha: {asset: hashlib.sha256(subprocess.check_output(
        ['git', 'show', sha + ':wordpress/wp-content/plugins/rollsbar-core/assets/' + asset], cwd=ROOT)).hexdigest()
        for asset in ('css/checkout.css', 'js/checkout.js')} for sha in (OLD, INCOMING)}


def validate_identity(identity):
    values = dict(re.findall(r'(?m)^([a-z_]+)=([^\n]*)$', identity))
    required = {'home': 'https://staging.rollsbar.ru', 'siteurl': 'https://staging.rollsbar.ru',
                'environment': 'staging', 'wordpress': '7.1.3', 'woocommerce': '11.1.2',
                'theme': 'active', 'plugin': 'active', 'blog_public': '0'}
    if any(values.get(k) != v for k, v in required.items()):
        raise ValueError('Staging identity differs')
    if identity.split('repo_status_begin\n', 1)[1].split('repo_status_end', 1)[0].strip():
        raise ValueError('Unexpected remote checkout changes')
    return values


def classify(report):
    values = validate_identity(report['identity'])
    hashes = dict(re.findall(r'asset=(\S+) sha256=([0-9a-f]{64})', report['assets']))
    matching = [sha for sha, expected in report['expected_hashes'].items() if hashes == expected]
    report['asset_matches'] = matching
    backups = report['backups']
    if 'snapshot_verified=' + PROTECTED + '\n' not in backups or ' incomplete' in backups:
        raise ValueError('Protected/incomplete backup state is not accepted')
    partial = backups.split('backup_partial_names_begin\n', 1)[1].split('backup_partial_names_end', 1)[0].strip()
    if partial:
        raise ValueError('Backup lock/temp state requires Coordinator')
    names = backups.split('backup_names_begin\n', 1)[1].split('backup_names_end', 1)[0].split()
    if len(names) > 6 or any(not re.fullmatch(r'20[0-9]{6}T[0-9]{6}Z', n) for n in names):
        raise ValueError('Unexpected backup retention/name state')
    report['new_snapshots_since_known'] = [n for n in names if n > '20261025T151212Z']
    fresh = [n for n in names if n >= '20261025T200000Z']
    report['failed_run_snapshots'] = fresh
    if values.get('marker') != OLD or OLD not in matching:
        return 'UNKNOWN_PARTIAL_STATE'
    if fresh:
        if all('snapshot_verified=' + n in backups and 'project_code_commit=' + OLD in backups.split('snapshot_begin=' + n + '\n', 1)[1].split('snapshot_end=' + n, 1)[0] for n in fresh):
            return 'BACKUP_COMPLETED_PRE_BOOTSTRAP'
        return 'UNKNOWN_PARTIAL_STATE'
    if values.get('repo_head') == OLD:
        return 'EXEC_NOT_OBSERVED'
    if values.get('repo_head') == INCOMING:
        return 'PRE_BACKUP_PARTIAL'
    return 'UNKNOWN_PARTIAL_STATE'


def main():
    if os.environ.get('GITHUB_REF_NAME') != BRANCH:
        raise SystemExit('Inspection is feature-branch pinned')
    out = ROOT / 'qa/visual-results/ssh-release-recovery'
    out.mkdir(parents=True, exist_ok=True)
    report = {'result': 'BLOCKED', 'classification': 'UNKNOWN_PARTIAL_STATE'}
    stage = 'exec_probe'
    probe_ok = False
    try:
        probe()
        probe_ok = True
        report['tiny_probe'] = 'PASS'
        stage = 'inspection'
        for key, script in [('identity', IDENTITY), ('assets', ASSETS), ('backups', BACKUPS),
                            ('catalog_raw', PREFIX + 'wp --path="$WP_PATH" eval ' + shlex.quote(AUDIT_PHP) + '\n')]:
            report[key] = execute(script)
            print(key + '=' + report[key], flush=True)
            if key == 'identity':
                validate_identity(report[key])
        report['catalog'] = parse_audit(report['catalog_raw'])
        validate_catalog_audit(report['catalog'])
        report['expected_hashes'] = expected_hashes()
        report['classification'] = classify(report)
        if report['classification'] == 'UNKNOWN_PARTIAL_STATE':
            raise ValueError('Unclassified partial deployment')
        report['result'] = 'PASS'
    except Exception as exc:
        report['error'] = {'stage': stage, 'type': type(exc).__name__}
        print('release_inspect=BLOCKED stage=' + stage + ' type=' + type(exc).__name__, flush=True)
    finally:
        if probe_ok:
            try:
                report['runtime_cleanup'] = cleanup_files([RUNTIME_FILE])
            except Exception as exc:
                report['result'] = 'BLOCKED'
                report['cleanup_error'] = {'stage': 'cleanup', 'type': type(exc).__name__}
        (out / 'evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('release_inspect=' + report['result'] + ' classification=' + report['classification'], flush=True)
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

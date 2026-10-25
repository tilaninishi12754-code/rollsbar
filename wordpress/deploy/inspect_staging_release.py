"""Atomic, read-only staging forensics with bounded redacted per-probe evidence."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

from staging_catalog_audit import AUDIT_PHP, parse_audit, validate_catalog_audit
from staging_ssh import connect, cleanup_files, RUNTIME_FILE

OLD = '88826907fc7ffe805a7c47f36c35a74c0049e08e'
INCOMING = '7a8809379d1dd781ce706b552f68579a9ea09d54'
TOOLING = '6391b43af48f03ac66b04675b674e1f9cebfc559'
PROTECTED = '20261023T215945Z'
KNOWN_LATEST = '20261025T151212Z'
FAILED_AT = '20261025T200000Z'
BRANCH = 'wordpress/checkout-visual-parity-2026-10-25'
ROOT = Path(__file__).resolve().parents[2]
LIMIT = 8192
READ_LIMIT = 65536
PREFIX = 'set -uo pipefail\nexport PATH="$HOME/.local/bin:$PATH"\nexport GIT_OPTIONAL_LOCKS=0\nWP_PATH="$HOME/www/staging.rollsbar.ru"\n'
BACKUP_ROOT = '$HOME/rollsbar-backups/staging'


def sanitize(value, limit=LIMIT):
    for key, secret in os.environ.items():
        if secret and re.search(r'password|token|secret|api.?key|^DB_|telegram|dadata|ISP_MANAGER_USER', key, re.I):
            value = value.replace(secret, '[REDACTED]')
    lines = []
    for line in value.splitlines():
        if re.search(r'password|passwd|token|secret|api[ _-]?key|\bDB_(?:USER|NAME|HOST|PASS\w*)\b|telegram|dadata|(?:mysql|postgres)://', line, re.I):
            line = '[REDACTED sensitive line]'
        lines.append(line)
    return '\n'.join(lines)[:limit]


def execute(name, command, connector=connect):
    """One new exec-only connection per fact; never discard failed command output."""
    row = {'name': name, 'status': 'FAIL', 'exit_code': None, 'stdout': '',
           'stderr': '', 'exception_type': None, 'truncated': False}
    client = None
    try:
        client = connector()
        # Small facts use short direct requests. Only the fixed catalog body uses stdin.
        body = PREFIX + command + '\n'
        via_stdin = len(body) > 2048
        # Preserve the login environment (notably its initialized PATH) for large
        # stdin-fed probes too. The fixed request line keeps the probe body off
        # the SSH command line and the child shell inherits the login PATH.
        request = 'bash -lc ' + shlex.quote('exec bash -s') if via_stdin else 'bash -lc ' + shlex.quote(body)
        stdin, out, err = client.exec_command(request, timeout=45)
        if via_stdin:
            stdin.write(body)
            stdin.flush()
            stdin.channel.shutdown_write()
        for key, stream in [('stdout', out), ('stderr', err)]:
            raw = stream.read(READ_LIMIT + 1).decode('utf-8', errors='replace')
            clean = sanitize(raw, READ_LIMIT)
            row[key] = clean[:LIMIT]
            row['truncated'] |= len(raw) > READ_LIMIT or len(clean) > LIMIT
        if row['truncated']:
            out.channel.close()
        else:
            row['exit_code'] = out.channel.recv_exit_status()
            row['status'] = 'PASS' if row['exit_code'] == 0 else 'FAIL'
    except Exception as exc:
        row['exception_type'] = type(exc).__name__
        row['exception_message'] = sanitize(str(exc), 1024)
    finally:
        if client is not None:
            try:
                client.close()
            except Exception as exc:
                row['status'] = 'FAIL'
                row['exception_type'] = type(exc).__name__
    return row


def object_command(path):
    return 'path="' + path + '''"
if [[ -L "$path" ]]; then kind=symlink
elif [[ -f "$path" ]]; then kind=regular
elif [[ -d "$path" ]]; then kind=directory
elif [[ -e "$path" ]]; then kind=other
else printf 'absent\\n'; exit 0; fi
printf '%s|' "$kind"; stat -c '%a|%s' -- "$path"'''


def snapshot_path(name):
    if not re.fullmatch(r'20[0-9]{6}T[0-9]{6}Z', name):
        raise ValueError('Invalid fixed snapshot timestamp')
    return BACKUP_ROOT + '/' + name


def snapshot_complete(name):
    return 'path="' + snapshot_path(name) + '''"
[[ -d "$path" && ! -L "$path" ]] || exit 2
for file in database.sql.gz uploads.tar.gz manifest.txt SHA256SUMS; do
  [[ -f "$path/$file" && ! -L "$path/$file" && -s "$path/$file" ]] || exit 3
done
printf 'complete\\n' '''


def snapshot_verify(name):
    return snapshot_complete(name) + '\ncd "$path" && sha256sum -c SHA256SUMS && gzip -t database.sql.gz && tar -tzf uploads.tar.gz >/dev/null'


def base_probes():
    wp = 'wp --path="$WP_PATH" '
    marker = '$HOME/.rollsbar-staging-deployed-sha'
    root = '"' + BACKUP_ROOT + '"'
    return [
        ('ssh_exec', "printf 'SSH_EXEC_OK\\n'"),
        ('marker_object', object_command(marker)),
        ('marker_value', 'path="' + marker + '"; [[ -f "$path" && ! -L "$path" ]] || exit 2; value="$(cat "$path")"; if [[ "$value" =~ ^[0-9a-f]{40}$ ]]; then printf "%s\\n" "$value"; else echo "invalid marker contents suppressed"; exit 3; fi'),
        ('marker_mode', 'stat -c "%a" -- "' + marker + '"'),
        ('repo_exists', '[[ -d "$HOME/.rollsbar-deploy/.git" ]] && echo present'),
        ('repo_head', 'git -C "$HOME/.rollsbar-deploy" rev-parse HEAD'),
        ('repo_status', 'git -C "$HOME/.rollsbar-deploy" status --short'),
        ('wp_exists', '[[ -f "$WP_PATH/wp-load.php" ]] && echo present'),
        ('home', wp + 'option get home'), ('siteurl', wp + 'option get siteurl'),
        ('environment', wp + "eval 'echo wp_get_environment_type();'"),
        ('wordpress_version', wp + 'core version'),
        ('woocommerce_version', wp + 'plugin get woocommerce --field=version'),
        ('theme_status', wp + 'theme get rollsbar-theme --field=status'),
        ('rollsbar_core_status', wp + 'plugin get rollsbar-core --field=status'),
        ('blog_public', wp + 'option get blog_public'),
        *[(label, 'path="$WP_PATH/wp-content/plugins/rollsbar-core/assets/' + asset + '"; [[ -f "$path" && ! -L "$path" ]] && sha256sum "$path" | cut -d " " -f 1') for label, asset in [('checkout_css','css/checkout.css'),('checkout_js','js/checkout.js')]],
        ('backup_root', object_command(BACKUP_ROOT)),
        ('backup_names', 'find ' + root + " -mindepth 1 -maxdepth 1 -name '20??????T??????Z' -printf '%f\\n' | LC_ALL=C sort"),
        ('protected_snapshot', snapshot_verify(PROTECTED)),
        ('new_snapshot_candidates', 'find ' + root + " -mindepth 1 -maxdepth 1 -name '20??????T??????Z' -printf '%f\\n' | LC_ALL=C sort | awk '$0 >= \"" + FAILED_AT + "\"'"),
        ('backup_lock', object_command(BACKUP_ROOT + '/.backup-staging.lock')),
        ('backup_tmp_dirs', 'find ' + root + " -mindepth 1 -maxdepth 1 -name '.tmp-*' -printf '%f\\n' | LC_ALL=C sort"),
        ('runtime_object', object_command('$HOME/' + RUNTIME_FILE)),
        ('catalog_audit', wp + 'eval ' + shlex.quote(AUDIT_PHP)),
    ]


def collect(runner=execute, cleanup=None):
    """Collect every independent fact before any semantic validation/classification."""
    report = {'probes': []}
    def record(name, command):
        try:
            row = runner(name, command)
        except Exception as exc:
            row = {'name': name, 'status': 'FAIL', 'exit_code': None, 'stdout': '', 'stderr': '',
                   'exception_type': type(exc).__name__, 'exception_message': sanitize(str(exc))}
        report['probes'].append(row)
        print('probe=' + json.dumps(row, ensure_ascii=False), flush=True)
        return row
    for name, command in base_probes():
        record(name, command)
    rows = {r['name']: r for r in report['probes']}
    names = {PROTECTED}
    for label in ['backup_names', 'new_snapshot_candidates']:
        if rows[label]['status'] == 'PASS':
            names.update(n for n in rows[label]['stdout'].splitlines() if re.fullmatch(r'20[0-9]{6}T[0-9]{6}Z', n))
    # Fixed retention is six; a much larger unexpected listing stays blocked and bounded.
    for name in sorted(names)[:32]:
        record('snapshot_complete_' + name, snapshot_complete(name))
        if name in (PROTECTED, KNOWN_LATEST) or name > KNOWN_LATEST:
            record('snapshot_verify_' + name, snapshot_verify(name))
            record('snapshot_manifest_' + name, 'grep -E ' + shlex.quote('^(created_utc|project_code_commit|site_url|wordpress_version|woocommerce_version|published_products)=') + ' "' + snapshot_path(name) + '/manifest.txt"')
    try:
        if cleanup is None:
            receipts = cleanup_files([RUNTIME_FILE])
        else:
            receipts = cleanup()
        report['runtime_cleanup'] = receipts
        clean = bool(receipts) and all(not r['after']['exists'] for r in receipts)
        row = {'name': 'runtime_cleanup', 'status': 'PASS' if clean else 'FAIL', 'exit_code': None,
               'stdout': sanitize(json.dumps(receipts)), 'stderr': '', 'exception_type': None}
    except Exception as exc:
        row = {'name': 'runtime_cleanup', 'status': 'FAIL', 'exit_code': None, 'stdout': '', 'stderr': '',
               'exception_type': type(exc).__name__, 'exception_message': sanitize(str(exc))}
    report['probes'].append(row)
    print('probe=' + json.dumps(row), flush=True)
    return report


def expected_hashes():
    return {sha: {asset: hashlib.sha256(subprocess.check_output(
        ['git', 'show', sha + ':wordpress/wp-content/plugins/rollsbar-core/assets/' + asset], cwd=ROOT)).hexdigest()
        for asset in ('css/checkout.css', 'js/checkout.js')} for sha in (OLD, INCOMING, TOOLING)}


def normalize_validate_classify(report):
    report.update(result='BLOCKED', classification='UNKNOWN_PARTIAL_STATE', SAFE_FOR_NEW_DEPLOY_RETRY='NO')
    rows = {r['name']: r for r in report['probes']}
    values = {name: row['stdout'].strip() for name, row in rows.items() if row['status'] == 'PASS'}
    report['normalized'] = values
    issues = ['probe failed: ' + r['name'] for r in report['probes'] if r['status'] != 'PASS' or r.get('truncated')]
    if len(rows) != len(report['probes']):
        issues.append('duplicate probe labels')
    expected = {'ssh_exec':'SSH_EXEC_OK','repo_exists':'present','wp_exists':'present',
                'home':'https://staging.rollsbar.ru','siteurl':'https://staging.rollsbar.ru',
                'environment':'staging','wordpress_version':'7.1.3','woocommerce_version':'11.1.2',
                'theme_status':'active','rollsbar_core_status':'active','blog_public':'0',
                'marker_mode':'600','repo_status':'','backup_lock':'absent','backup_tmp_dirs':''}
    required = {name for name, _ in base_probes()} | {'runtime_cleanup'}
    issues += ['probe missing: ' + name for name in sorted(required - rows.keys())]
    for key, value in expected.items():
        if values.get(key) != value:
            issues.append('unexpected value: ' + key)
    if not values.get('marker_object', '').startswith('regular|600|'):
        issues.append('marker object is not a regular mode-600 file')
    if not values.get('backup_root', '').startswith('directory|'):
        issues.append('backup root is not a directory')
    for key in ['marker_value','repo_head']:
        if not re.fullmatch(r'[0-9a-f]{40}',values.get(key,'')):
            issues.append('invalid SHA: ' + key)
    try:
        report['catalog'] = parse_audit(values.get('catalog_audit',''))
        validate_catalog_audit(report['catalog'])
        if report['catalog'].get('deployed_sha') != values.get('marker_value'):
            issues.append('marker changed between independent reads')
    except (RuntimeError, ValueError):
        issues.append('catalog identity validation failed')
    assets = {}
    for key, asset in [('checkout_css','css/checkout.css'),('checkout_js','js/checkout.js')]:
        actual = values.get(key, '')
        matches = [sha for sha, hashes in report.get('expected_hashes', {}).items() if actual == hashes[asset]]
        assets[key] = {'sha256':actual,'matches':matches,'identity':'OLD' if OLD in matches else 'CANDIDATE' if INCOMING in matches else 'UNKNOWN'}
        if not re.fullmatch(r'[0-9a-f]{64}',actual) or assets[key]['identity'] == 'UNKNOWN':
            issues.append('unknown asset: ' + key)
    report['assets'] = assets
    asset_states = [a['identity'] for a in assets.values()]
    mixed = set(asset_states) == {'OLD','CANDIDATE'}
    report['mixed_asset_state'] = mixed
    names = values.get('backup_names','').splitlines()
    candidates = values.get('new_snapshot_candidates','').splitlines()
    valid_names = all(re.fullmatch(r'20[0-9]{6}T[0-9]{6}Z', n) for n in names + candidates)
    if not valid_names or len(names) > 6 or PROTECTED not in names:
        issues.append('unexpected backup inventory')
    if valid_names and sorted(candidates) != sorted(n for n in names if n >= FAILED_AT):
        issues.append('inconsistent failed-run snapshot inventory')
    report['complete_snapshots'] = [n for n in names if values.get('snapshot_complete_' + n) == 'complete']
    report['new_snapshots_since_known'] = [n for n in names if n > KNOWN_LATEST]
    report['failed_run_snapshots'] = candidates
    for name in names:
        if values.get('snapshot_complete_' + name) != 'complete':
            issues.append('snapshot incomplete/unproven: ' + name)
        if name in (PROTECTED, KNOWN_LATEST) or name > KNOWN_LATEST:
            if 'snapshot_verify_' + name not in values:
                issues.append('snapshot integrity unproven: ' + name)
            manifest = dict(re.findall(r'(?m)^([a-z_]+)=(.*)$',values.get('snapshot_manifest_' + name,'')))
            required_manifest = {'created_utc':name,'site_url':'https://staging.rollsbar.ru',
                                 'wordpress_version':'7.1.3','woocommerce_version':'11.1.2'}
            if any(manifest.get(k) != v for k,v in required_manifest.items()) or not re.fullmatch(r'[0-9a-f]{40}',manifest.get('project_code_commit','')) or not manifest.get('published_products','').isdigit():
                issues.append('snapshot manifest unproven: ' + name)
            if name >= FAILED_AT and (manifest.get('project_code_commit') != OLD or manifest.get('published_products') != '121'):
                issues.append('failed-run backup does not represent the accepted old release: ' + name)
    cleanup = report.get('runtime_cleanup', [])
    if len(cleanup) != 1 or cleanup[0].get('name') != RUNTIME_FILE or cleanup[0].get('after', {}).get('exists') is not False:
        issues.append('runtime absence not proven')
    marker = values.get('marker_value')
    category = 'UNKNOWN_PARTIAL_STATE'
    reasons = []
    if mixed:
        category = 'MIXED_ASSET_STATE'
        reasons.append('CSS and JS match different known application revisions')
    elif not issues and marker == OLD and asset_states == ['OLD','OLD']:
        if candidates:
            category = 'BACKUP_COMPLETED_PRE_BOOTSTRAP'
        elif values.get('repo_head') == OLD:
            category = 'EXEC_NOT_OBSERVED'
        elif values.get('repo_head') in (INCOMING, TOOLING):
            category = 'PRE_BACKUP_PARTIAL'
        reasons.append('old marker, both old assets, healthy identity/catalog, verified backups, no lock/temp, runtime absent')
    elif not issues and asset_states == ['CANDIDATE','CANDIDATE']:
        if marker == OLD:
            category = 'POST_BOOTSTRAP_PARTIAL'
        elif marker in (INCOMING, TOOLING):
            category = 'FULL_DEPLOY_MARKED'
        reasons.append('both candidate checkout assets are live; marker recorded separately; historical workflow completion is not inferred')
    safe = not issues and category in ('EXEC_NOT_OBSERVED','PRE_BACKUP_PARTIAL','BACKUP_COMPLETED_PRE_BOOTSTRAP')
    report.update(classification=category,classification_reasons=reasons,validation_issues=issues,
                  SAFE_FOR_NEW_DEPLOY_RETRY='YES' if safe else 'NO')
    # Candidate/mixed/unknown partial deployments require Coordinator review, not automatic retry.
    if safe:
        report['result'] = 'PASS'
    return report


def main():
    if os.environ.get('GITHUB_REF_NAME') != BRANCH:
        raise SystemExit('Inspection is feature-branch pinned')
    out = ROOT / 'qa/visual-results/ssh-release-recovery'
    out.mkdir(parents=True, exist_ok=True)
    report = collect()
    # Save all raw rows before any normalization that could itself fail.
    (out / 'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        report['expected_hashes'] = expected_hashes()
        normalize_validate_classify(report)
    except Exception as exc:
        report.update(result='BLOCKED',classification='UNKNOWN_PARTIAL_STATE',SAFE_FOR_NEW_DEPLOY_RETRY='NO',
                      normalization_error={'exception_type':type(exc).__name__,'message':sanitize(str(exc))})
    (out / 'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('release_inspect=' + report['result'] + ' classification=' + report['classification'] + ' SAFE_FOR_NEW_DEPLOY_RETRY=' + report['SAFE_FOR_NEW_DEPLOY_RETRY'],flush=True)
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

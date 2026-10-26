#!/usr/bin/env python3
"""One-time continuation of run 40272003110; never deploy, backup, or retry.

Tooling runs from Actions checkout; remote application stays at RELEASE.
Every read uses a fresh authenticated, exec-only connection. No cleanup writes.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

from inspect_staging_release import base_probes, execute, snapshot_complete, snapshot_path
from staging_catalog_audit import parse_audit, validate_catalog_audit

RELEASE = '22aeb21783a79f8cb670a3371486fa0d17647b0b'
OLD = '88826907fc7ffe805a7c47f36c35a74c0049e08e'
FRESH = '20261026T050120Z'
PROTECTED = '20261023T215945Z'
BRANCH = 'wordpress/checkout-visual-parity-2026-10-25'
ROOT = Path(__file__).resolve().parents[2]
ASSETS = {'checkout_css': 'css/checkout.css', 'checkout_js': 'js/checkout.js'}
EXPECTED = {
    'ssh_exec': 'SSH_EXEC_OK', 'repo_exists': 'present', 'wp_exists': 'present',
    'repo_head': RELEASE, 'repo_status': '', 'marker_mode': '600',
    'home': 'https://staging.rollsbar.ru', 'siteurl': 'https://staging.rollsbar.ru',
    'environment': 'staging', 'wordpress_version': '7.1.3',
    'woocommerce_version': '11.1.2', 'theme_status': 'active',
    'rollsbar_core_status': 'active', 'blog_public': '0',
    'backup_lock': 'absent', 'backup_tmp_dirs': '', 'runtime_object': 'absent',
}


def validate_input(release_sha, branch):
    if (not re.fullmatch(r'[0-9a-f]{40}', release_sha) or release_sha != RELEASE
            or branch != BRANCH):
        raise ValueError('Resume is pinned to the proven application release and feature branch')


def expected_hashes():
    return {name: hashlib.sha256(subprocess.check_output([
        'git', 'show', RELEASE + ':wordpress/wp-content/plugins/rollsbar-core/assets/' + asset
    ], cwd=ROOT)).hexdigest() for name, asset in ASSETS.items()}


def verified_snapshot(name):
    # Require checksums for all three payloads, not an arbitrary subset.
    return 'set -e\n' + snapshot_complete(name) + r'''
[[ "$(realpath "$path")" == "$path" ]]
cd "$path"
[[ "$(wc -l < SHA256SUMS)" == 3 ]]
for file in database.sql.gz uploads.tar.gz manifest.txt; do
  line="$(grep -E "^[0-9a-f]{64}  $file$" SHA256SUMS)"
  [[ "$line" == "$(sha256sum --text "$file")" ]]
done
gzip -t database.sql.gz
tar -tzf uploads.tar.gz >/dev/null
printf 'verified\n'
'''


def probes():
    names = set(EXPECTED) | set(ASSETS) | {'marker_object', 'marker_value',
                                         'backup_root', 'catalog_audit'}
    result = [(n, c) for n, c in base_probes() if n in names]
    for name, asset in ASSETS.items():
        result.append(('http_' + name,
            'curl --fail --silent --show-error --max-time 30 '
            'https://staging.rollsbar.ru/wp-content/plugins/rollsbar-core/assets/'
            + asset + ' | sha256sum | cut -d " " -f 1'))
    result.append(('woocommerce_status', 'wp --path="$WP_PATH" plugin get woocommerce --field=status'))
    for name in (FRESH, PROTECTED):
        result.append(('snapshot_' + name, verified_snapshot(name)))
    result.append(('fresh_manifest', 'grep -E '
                   "'^(created_utc|project_code_commit|site_url|wordpress_version|woocommerce_version|published_products|blog_public)=' "
                   '"' + snapshot_path(FRESH) + '/manifest.txt"'))
    return result


def verify_state(*, final=False, runner=execute, hashes=None):
    values = {}
    for name, command in probes():
        row = runner(name, command)
        if (row.get('status') != 'PASS' or row.get('exit_code') != 0
                or row.get('truncated') or row.get('exception_type')):
            raise RuntimeError('Resume read-only probe failed: ' + name)
        values[name] = row['stdout'].strip()
    asset_hashes = expected_hashes() if hashes is None else hashes
    required = dict(EXPECTED, marker_value=RELEASE if final else OLD,
                    woocommerce_status='active', **asset_hashes,
                    **{'http_' + name: value for name, value in asset_hashes.items()})
    for name, value in required.items():
        if values.get(name) != value:
            raise RuntimeError('Resume state mismatch: ' + name)
    if not values['marker_object'].startswith('regular|600|'):
        raise RuntimeError('Unsafe marker object')
    if not values['backup_root'].startswith('directory|'):
        raise RuntimeError('Unsafe backup root')
    for name in (FRESH, PROTECTED):
        if values['snapshot_' + name] != 'complete\nverified':
            raise RuntimeError('Snapshot verification incomplete')
    manifest_lines = values['fresh_manifest'].splitlines()
    manifest = dict(line.split('=', 1) for line in manifest_lines)
    expected_manifest = dict(created_utc=FRESH, project_code_commit=OLD,
        site_url='https://staging.rollsbar.ru', wordpress_version='7.1.3',
        woocommerce_version='11.1.2', published_products='121', blog_public='0')
    if manifest != expected_manifest or len(manifest_lines) != len(expected_manifest):
        raise RuntimeError('Fresh backup manifest differs from proven pre-release state')
    catalog = parse_audit(values['catalog_audit'])
    validate_catalog_audit(catalog, expected_deployed_sha=required['marker_value'])
    print('resume_readback=' + ('final' if final else 'partial') + '_PASS', flush=True)
    return catalog


def run_tool(name, env):
    # No shell and no retry. Existing scripts redact their own logs.
    subprocess.run([sys.executable, str(Path(__file__).with_name(name + '.py'))],
                   env=env, check=True, cwd=ROOT)


def run_resume(release_sha, branch, *, verifier=verify_state, tool=run_tool):
    validate_input(release_sha, branch)
    before = verifier()
    env = dict(os.environ, ROLLSBAR_DEPLOY_SHA=release_sha,
        ROLLSBAR_CONFIRM_STAGING_SEO='YES', ROLLSBAR_SEO_BACKUP_ALREADY_VERIFIED='YES',
        ROLLSBAR_CONFIRM_HTTP_HARDENING='YES')
    tool('provision_staging_seo', env)
    # Independent post-SEO proof as well as provisioner's own post-audit.
    after = verifier()
    if before != after:
        raise RuntimeError('Catalog changed during SEO; marker forbidden')
    tool('harden_staging_http', env)
    tool('audit_staging_seo', env)
    # Recheck partial identity/assets/catalog immediately before marker persistence.
    if verifier() != before:
        raise RuntimeError('Catalog changed before marker; marker forbidden')
    tool('mark_staging_deployed_sha', env)
    final = verifier(final=True)
    if {k: v for k, v in final.items() if k != 'deployed_sha'} != {
            k: v for k, v in before.items() if k != 'deployed_sha'}:
        raise RuntimeError('Final catalog differs from accepted release')
    print('STAGING RELEASE RESUME PASS', flush=True)


if __name__ == '__main__':
    try:
        run_resume(os.environ.get('ROLLSBAR_RELEASE_SHA', ''), os.environ.get('GITHUB_REF_NAME', ''))
    except Exception as exc:
        # Never print arbitrary subprocess/SSH exception text or secrets.
        raise SystemExit('Release resume blocked: ' + type(exc).__name__)

#!/usr/bin/env python3
"""Persist the exact Git SHA currently verified on RollsBar staging.

This runs only after the live staging deploy and HTTP hardening steps succeed.
The marker lives outside web-root and is later consumed by the backup manifest,
so a pre-deploy snapshot records the code revision that was actually serving at
the moment the snapshot was created, not the incoming revision about to deploy.
"""
from __future__ import annotations

import os
import re
import shlex

from staging_catalog_audit import AUDIT_PHP, parse_audit, validate_catalog_audit
from provision_staging_seo import run_remote
from staging_ssh import connect

DOMAIN = "staging.rollsbar.ru"
MARKER = ".rollsbar-staging-deployed-sha"


def q(value: str) -> str:
    return shlex.quote(value)


def marker_script(deploy_sha):
    if not re.fullmatch(r"[0-9a-f]{40}", deploy_sha):
        raise ValueError("Marker requires exact lowercase application SHA")
    remote = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="$HOME/www/{DOMAIN}"
MARKER="$HOME/{MARKER}"
TMP="$MARKER.tmp.$$"

[[ -f "$WP_PATH/wp-load.php" ]]
core="$(wp --path="$WP_PATH" core version)"
woo="$(wp --path="$WP_PATH" plugin get woocommerce --field=version)"
blog_public="$(wp --path="$WP_PATH" option get blog_public)"
theme="$(wp --path="$WP_PATH" theme get rollsbar-theme --field=status)"
plugin="$(wp --path="$WP_PATH" plugin get rollsbar-core --field=status)"
http_code="$(curl -L -sS -o /dev/null -w '%{{http_code}}' --max-time 20 https://{DOMAIN}/)"

[[ "$core" == '7.1.3' ]]
[[ "$woo" == '11.1.2' ]]
[[ "$blog_public" == '0' ]]
[[ "$theme" == 'active' ]]
[[ "$plugin" == 'active' ]]
[[ "$http_code" == '200' ]]

[[ "$(git -C "$HOME/.rollsbar-deploy" rev-parse HEAD)" == {q(deploy_sha)} ]]
[[ -z "$(git -C "$HOME/.rollsbar-deploy" status --porcelain)" ]]
[[ "$(wp --path="$WP_PATH" option get home)" == 'https://{DOMAIN}' ]]
[[ "$(wp --path="$WP_PATH" option get siteurl)" == 'https://{DOMAIN}' ]]
[[ "$(wp --path="$WP_PATH" eval 'echo wp_get_environment_type();')" == 'staging' ]]

umask 077
printf '%s\n' {q(deploy_sha)} > "$TMP"
chmod 600 "$TMP"
mv -f "$TMP" "$MARKER"
[[ "$(cat "$MARKER")" == {q(deploy_sha)} ]]
[[ "$(stat -c '%a' "$MARKER")" == '600' ]]

echo 'deployed_marker=updated'
echo 'deployed_marker_sha={deploy_sha}'
echo 'deployed_marker_mode=600'
echo 'STAGING DEPLOYED SHA MARKER PASS'
'''
    return remote


def execute(client, deploy_sha):
    script = marker_script(deploy_sha)  # Validate before opening any mutation path.
    audit = parse_audit(run_remote(client,
        'set -euo pipefail\nexport PATH="$HOME/.local/bin:$PATH"\n'
        'wp --path="$HOME/www/staging.rollsbar.ru" eval ' + q(AUDIT_PHP)))
    validate_catalog_audit(audit)
    result = run_remote(client, script)
    if "STAGING DEPLOYED SHA MARKER PASS" not in result:
        raise RuntimeError("Marker command returned without verification marker")
    print(result)


def main():
    client = None
    try:
        deploy_sha = os.environ.get("ROLLSBAR_DEPLOY_SHA", "")
        marker_script(deploy_sha)
        client = connect()
        execute(client, deploy_sha)
    except Exception as exc:
        raise SystemExit("Marker persistence failed: " + type(exc).__name__)
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()

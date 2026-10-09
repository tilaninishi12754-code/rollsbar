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
import socket
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
DEPLOY_SHA = os.environ["ROLLSBAR_DEPLOY_SHA"].strip().lower()
DOMAIN = "staging.rollsbar.ru"
MARKER = ".rollsbar-staging-deployed-sha"


def q(value: str) -> str:
    return shlex.quote(value)


def connect() -> paramiko.SSHClient:
    host = urlsplit(BASE).hostname or ""
    if not host:
        raise RuntimeError("Could not derive hosting hostname")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=22,
        username=USER,
        password=PASSWORD,
        timeout=15,
        auth_timeout=15,
        banner_timeout=15,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


if not re.fullmatch(r"[0-9a-f]{40}", DEPLOY_SHA):
    raise SystemExit("ROLLSBAR_DEPLOY_SHA must be an exact 40-character Git SHA")

client = None
try:
    client = connect()
    remote = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="$HOME/www/{DOMAIN}"
MARKER="$HOME/{MARKER}"
TMP="$MARKER.tmp.$$"

[[ -f "$WP_PATH/wp-load.php" ]]
core="$(wp --path="$WP_PATH" core version)"
woo="$(wp --path="$WP_PATH" plugin get woocommerce --field=version)"
products="$(wp --path="$WP_PATH" post list --post_type=product --post_status=publish --format=count)"
blog_public="$(wp --path="$WP_PATH" option get blog_public)"
theme="$(wp --path="$WP_PATH" theme get rollsbar-theme --field=status)"
plugin="$(wp --path="$WP_PATH" plugin get rollsbar-core --field=status)"
http_code="$(curl -L -sS -o /dev/null -w '%{{http_code}}' --max-time 20 https://{DOMAIN}/)"

[[ "$core" == '7.1.3' ]]
[[ "$woo" == '11.1.2' ]]
[[ "$products" == '118' ]]
[[ "$blog_public" == '0' ]]
[[ "$theme" == 'active' ]]
[[ "$plugin" == 'active' ]]
[[ "$http_code" == '200' ]]

umask 077
printf '%s\n' {q(DEPLOY_SHA)} > "$TMP"
chmod 600 "$TMP"
mv -f "$TMP" "$MARKER"
[[ "$(cat "$MARKER")" == {q(DEPLOY_SHA)} ]]
[[ "$(stat -c '%a' "$MARKER")" == '600' ]]

echo 'deployed_marker=updated'
echo 'deployed_marker_sha={DEPLOY_SHA}'
echo 'deployed_marker_mode=600'
echo 'STAGING DEPLOYED SHA MARKER PASS'
'''
    _, stdout, stderr = client.exec_command("bash -lc " + q(remote), timeout=120)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    print(out, end="" if out.endswith("\n") or not out else "\n")
    if status != 0:
        safe = " | ".join(line for line in err.splitlines() if "password" not in line.lower())[-1200:]
        raise RuntimeError(f"Remote deployed-SHA marker failed exit={status}: {safe}")
    if "STAGING DEPLOYED SHA MARKER PASS" not in out:
        raise RuntimeError("Marker command returned success without verification marker")
except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError) as exc:
    message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
    print(f"deployed_marker=failed type={exc.__class__.__name__} detail={message}")
    raise SystemExit(1)
finally:
    if client is not None:
        client.close()

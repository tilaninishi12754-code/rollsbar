#!/usr/bin/env python3
"""Promote REG.RU RollsBar staging from the 5-product smoke seed to the full catalog.

Idempotent: the RollsBar importer upserts by stable SKU. This script never touches
production and verifies the observable result after import.
"""
from __future__ import annotations

import os
import shlex
import socket
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_FULL_STAGING_IMPORT", "")
WP_PATH = "$HOME/www/staging.rollsbar.ru"
EXPECTED_PRODUCTS = 118


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


def exec_checked(client: paramiko.SSHClient, command: str) -> str:
    _, stdout, stderr = client.exec_command(command, timeout=420)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    print(out, end="" if out.endswith("\n") or not out else "\n")
    if status != 0:
        if err:
            print("remote_stderr_present=yes")
        raise RuntimeError(f"Remote catalog promotion failed with exit status {status}")
    return out


if CONFIRM != "YES":
    raise SystemExit("Refusing mutation: set ROLLSBAR_CONFIRM_FULL_STAGING_IMPORT=YES")

client = None
try:
    client = connect()
    remote = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH={WP_PATH}

wp --path="$WP_PATH" core is-installed
[[ "$(wp --path="$WP_PATH" option get home)" == "https://staging.rollsbar.ru" ]]
[[ "$(wp --path="$WP_PATH" option get blog_public)" == "0" ]]
[[ "$(wp --path="$WP_PATH" option get woocommerce_currency)" == "RUB" ]]

before="$(wp --path="$WP_PATH" post list --post_type=product --post_status=publish --format=count)"
echo "products_before=$before"
wp --path="$WP_PATH" rollsbar catalog validate
wp --path="$WP_PATH" rollsbar catalog import

after="$(wp --path="$WP_PATH" post list --post_type=product --post_status=publish --format=count)"
echo "products_after=$after"
[[ "$after" == "{EXPECTED_PRODUCTS}" ]]

# Re-run the importer once as an idempotency proof. Product count must remain exact.
wp --path="$WP_PATH" rollsbar catalog import >/dev/null
second="$(wp --path="$WP_PATH" post list --post_type=product --post_status=publish --format=count)"
echo "products_after_second_import=$second"
[[ "$second" == "{EXPECTED_PRODUCTS}" ]]

echo "FULL STAGING CATALOG PROMOTION PASS"
'''
    exec_checked(client, "bash -lc " + shlex.quote(remote))
except (paramiko.SSHException, socket.error, OSError, RuntimeError) as exc:
    print(f"catalog_promotion=failed type={exc.__class__.__name__}")
    print(str(exc).replace(PASSWORD, "***"))
    raise SystemExit(1)
finally:
    if client is not None:
        client.close()

#!/usr/bin/env python3
"""Repair canonical WordPress core and tighten wp-config permissions on staging.

Safety invariants:
- staging only;
- create+verify a fresh server-side backup before mutation;
- reinstall the SAME pinned WordPress version with --skip-content --force;
- never update WooCommerce/plugins/themes here;
- verify official WordPress checksums after repair;
- tighten only wp-config.php to 0640 and automatically restore its previous
  mode if WordPress/HTTP health checks fail;
- preserve the 118-product live staging database/catalog.
"""
from __future__ import annotations

import os
import shlex
import socket
from pathlib import Path
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_STAGING_HARDENING", "")
DOMAIN = "staging.rollsbar.ru"
WP_VERSION = "7.1.3"
WC_VERSION = "11.1.2"
EXPECTED_PRODUCTS = "118"
REMOTE_BACKUP_SCRIPT = ".rollsbar-prehardening-backup.sh"
LOCAL_BACKUP_SCRIPT = Path(__file__).with_name("backup-staging.sh")


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


def upload_backup_script(client: paramiko.SSHClient) -> None:
    data = LOCAL_BACKUP_SCRIPT.read_bytes()
    sftp = client.open_sftp()
    try:
        with sftp.open(REMOTE_BACKUP_SCRIPT, "wb") as fh:
            fh.write(data)
        sftp.chmod(REMOTE_BACKUP_SCRIPT, 0o700)
    finally:
        sftp.close()


def remove_remote_script(client: paramiko.SSHClient) -> None:
    try:
        sftp = client.open_sftp()
        try:
            sftp.remove(REMOTE_BACKUP_SCRIPT)
        except FileNotFoundError:
            pass
        finally:
            sftp.close()
    except Exception:
        pass


def execute(client: paramiko.SSHClient) -> str:
    remote = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="$HOME/www/{DOMAIN}"
BACKUP_ROOT="$HOME/rollsbar-backups/staging"
BACKUP_SCRIPT="$HOME/{REMOTE_BACKUP_SCRIPT}"

if [[ ! -f "$WP_PATH/wp-load.php" ]]; then
  echo "HARDEN FAIL: WordPress staging missing"
  exit 2
fi
if ! command -v wp >/dev/null 2>&1; then
  echo "HARDEN FAIL: WP-CLI unavailable"
  exit 2
fi

export WP_PATH
export ROLLSBAR_BACKUP_ROOT="$BACKUP_ROOT"
export ROLLSBAR_BACKUP_RETENTION=5

echo "stage=pre_mutation_backup"
bash "$BACKUP_SCRIPT"

echo "stage=pre_mutation_assertions"
pre_core="$(wp --path="$WP_PATH" core version)"
pre_woo="$(wp --path="$WP_PATH" plugin get woocommerce --field=version)"
pre_products="$(wp --path="$WP_PATH" post list --post_type=product --post_status=publish --format=count)"
pre_blog_public="$(wp --path="$WP_PATH" option get blog_public)"
[[ "$pre_core" == "{WP_VERSION}" ]]
[[ "$pre_woo" == "{WC_VERSION}" ]]
[[ "$pre_products" == "{EXPECTED_PRODUCTS}" ]]
[[ "$pre_blog_public" == "0" ]]

echo "stage=repair_same_version_core"
wp core download --path="$WP_PATH" --version="{WP_VERSION}" --locale=en_US --skip-content --force
wp --path="$WP_PATH" core verify-checksums --version="{WP_VERSION}" --locale=en_US

echo "stage=tighten_wp_config"
old_mode="$(stat -c '%a' "$WP_PATH/wp-config.php")"
echo "wp_config_old_mode=$old_mode"
chmod 0640 "$WP_PATH/wp-config.php"
new_mode="$(stat -c '%a' "$WP_PATH/wp-config.php")"
echo "wp_config_new_mode=$new_mode"
[[ "$new_mode" == "640" ]]

rollback_mode() {{
  chmod "$old_mode" "$WP_PATH/wp-config.php" || true
  echo "wp_config_mode_rollback=$old_mode"
}}

# WP-CLI must still be able to bootstrap through wp-config.php under the tighter
# mode. If not, restore the old mode before failing.
if ! wp --path="$WP_PATH" core is-installed >/dev/null 2>&1; then
  rollback_mode
  echo "HARDEN FAIL: WordPress cannot read wp-config.php at 0640"
  exit 5
fi

# Public health must survive the permission change. Test several attempts to
# avoid treating one transient network response as a permission failure.
http_ok=0
http_code=000
for attempt in 1 2 3; do
  http_code="$(curl -L -sS --max-time 20 -o /tmp/rollsbar-harden-health -w '%{{http_code}}' "https://{DOMAIN}/" || true)"
  if [[ "$http_code" =~ ^[23][0-9][0-9]$ ]]; then
    http_ok=1
    break
  fi
  sleep 2
done
rm -f /tmp/rollsbar-harden-health
if [[ "$http_ok" != "1" ]]; then
  rollback_mode
  echo "HARDEN FAIL: site health after chmod returned HTTP $http_code"
  exit 6
fi
echo "home_http=$http_code"

# Final live invariants. No extension updates are allowed in this workflow.
post_core="$(wp --path="$WP_PATH" core version)"
post_woo="$(wp --path="$WP_PATH" plugin get woocommerce --field=version)"
post_products="$(wp --path="$WP_PATH" post list --post_type=product --post_status=publish --format=count)"
post_blog_public="$(wp --path="$WP_PATH" option get blog_public)"
wp --path="$WP_PATH" core verify-checksums --version="{WP_VERSION}" --locale=en_US >/dev/null
[[ "$post_core" == "{WP_VERSION}" ]]
[[ "$post_woo" == "{WC_VERSION}" ]]
[[ "$post_products" == "{EXPECTED_PRODUCTS}" ]]
[[ "$post_blog_public" == "0" ]]
[[ "$(stat -c '%a' "$WP_PATH/wp-config.php")" == "640" ]]

echo "assert_core=$post_core"
echo "assert_core_checksums=pass"
echo "assert_woocommerce=$post_woo"
echo "assert_products=$post_products"
echo "assert_blog_public=$post_blog_public"
echo "assert_wp_config_mode=640"
echo "extensions_updated=no"
echo "STAGING CORE HARDENING PASS"
'''
    _, stdout, stderr = client.exec_command("bash -lc " + q(remote), timeout=600)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    print(out, end="" if out.endswith("\n") or not out else "\n")
    if status != 0:
        safe_lines = [
            line
            for line in err.splitlines()
            if "password" not in line.lower() and "db_" not in line.lower()
        ]
        if safe_lines:
            print("remote_stderr=" + " | ".join(safe_lines[-12:])[:1800])
        raise RuntimeError(f"Remote hardening failed with exit status {status}")
    return out


if CONFIRM != "YES":
    raise SystemExit("Refusing staging mutation: set ROLLSBAR_CONFIRM_STAGING_HARDENING=YES")

client = None
try:
    client = connect()
    upload_backup_script(client)
    output = execute(client)
    if "STAGING CORE HARDENING PASS" not in output:
        raise RuntimeError("Hardening command returned without verification marker")
except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError) as exc:
    message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
    print(f"staging_hardening=failed type={exc.__class__.__name__}")
    print(message)
    raise SystemExit(1)
finally:
    if client is not None:
        remove_remote_script(client)
        client.close()

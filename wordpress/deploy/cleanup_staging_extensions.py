#!/usr/bin/env python3
"""Remove only known-unused WordPress extensions from RollsBar staging.

Safety:
- staging only;
- fresh verified backup before mutation;
- refuse if active plugin/theme assumptions do not match;
- delete only Akismet + Hello Dolly and two older bundled themes;
- keep Twenty Twenty-Five as one bundled fallback theme;
- never update WooCommerce here;
- explicitly disable WooCommerce per-plugin auto-update so the tested pinned
  version cannot drift outside the staging validation pipeline;
- verify core checksum, catalog, active project code and HTTP health afterward.
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
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_STAGING_EXTENSION_CLEANUP", "")
DOMAIN = "staging.rollsbar.ru"
WP_VERSION = "7.1.3"
WC_VERSION = "11.1.2"
EXPECTED_PRODUCTS = "118"
REMOTE_BACKUP_SCRIPT = ".rollsbar-precleanup-backup.sh"
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
    sftp = client.open_sftp()
    try:
        with sftp.open(REMOTE_BACKUP_SCRIPT, "wb") as fh:
            fh.write(LOCAL_BACKUP_SCRIPT.read_bytes())
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

wp_cmd() {{ wp --path="$WP_PATH" "$@"; }}

[[ -f "$WP_PATH/wp-load.php" ]]
command -v wp >/dev/null 2>&1

export WP_PATH
export ROLLSBAR_BACKUP_ROOT="$BACKUP_ROOT"
export ROLLSBAR_BACKUP_RETENTION=5

echo "stage=pre_cleanup_backup"
bash "$BACKUP_SCRIPT"

echo "stage=pre_cleanup_assertions"
[[ "$(wp_cmd core version)" == "{WP_VERSION}" ]]
[[ "$(wp_cmd plugin get woocommerce --field=version)" == "{WC_VERSION}" ]]
[[ "$(wp_cmd plugin get woocommerce --field=status)" == "active" ]]
[[ "$(wp_cmd plugin get rollsbar-core --field=status)" == "active" ]]
[[ "$(wp_cmd theme get rollsbar-theme --field=status)" == "active" ]]
[[ "$(wp_cmd post list --post_type=product --post_status=publish --format=count)" == "{EXPECTED_PRODUCTS}" ]]
wp_cmd core verify-checksums --version="{WP_VERSION}" --locale=en_US >/dev/null

for plugin in akismet hello; do
  if wp_cmd plugin is-installed "$plugin"; then
    if wp_cmd plugin is-active "$plugin"; then
      echo "CLEANUP FAIL: expected inactive plugin is active: $plugin"
      exit 4
    fi
  fi
done
for theme in twentytwentyfour twentytwentythree; do
  if wp_cmd theme is-installed "$theme"; then
    if wp_cmd theme is-active "$theme"; then
      echo "CLEANUP FAIL: expected inactive theme is active: $theme"
      exit 4
    fi
  fi
done
if ! wp_cmd theme is-installed twentytwentyfive; then
  echo "CLEANUP FAIL: fallback bundled theme twentytwentyfive missing"
  exit 4
fi
if wp_cmd theme is-active twentytwentyfive; then
  echo "CLEANUP FAIL: fallback theme unexpectedly active"
  exit 4
fi

woo_auto_before="$(wp_cmd plugin auto-updates status woocommerce --field=status 2>/dev/null || true)"
echo "woocommerce_auto_update_before=${{woo_auto_before:-unknown}}"
# The application deploy pins and validates WooCommerce 11.1.2. Explicitly keep
# its normal per-plugin auto-update off; version bumps must first pass staging.
wp_cmd plugin auto-updates disable woocommerce >/dev/null || true
woo_auto_after="$(wp_cmd plugin auto-updates status woocommerce --field=status 2>/dev/null || true)"
echo "woocommerce_auto_update_after=${{woo_auto_after:-unknown}}"

for plugin in akismet hello; do
  if wp_cmd plugin is-installed "$plugin"; then
    wp_cmd plugin delete "$plugin"
  fi
done
for theme in twentytwentyfour twentytwentythree; do
  if wp_cmd theme is-installed "$theme"; then
    wp_cmd theme delete "$theme"
  fi
done

echo "stage=post_cleanup_verify"
[[ "$(wp_cmd core version)" == "{WP_VERSION}" ]]
wp_cmd core verify-checksums --version="{WP_VERSION}" --locale=en_US >/dev/null
[[ "$(wp_cmd plugin get woocommerce --field=version)" == "{WC_VERSION}" ]]
[[ "$(wp_cmd plugin get woocommerce --field=status)" == "active" ]]
[[ "$(wp_cmd plugin get rollsbar-core --field=status)" == "active" ]]
[[ "$(wp_cmd theme get rollsbar-theme --field=status)" == "active" ]]
[[ "$(wp_cmd post list --post_type=product --post_status=publish --format=count)" == "{EXPECTED_PRODUCTS}" ]]
[[ "$(wp_cmd option get blog_public)" == "0" ]]
[[ "$(stat -c '%a' "$WP_PATH/wp-config.php")" == "640" ]]

for plugin in akismet hello; do
  if wp_cmd plugin is-installed "$plugin"; then
    echo "CLEANUP FAIL: plugin still installed: $plugin"
    exit 5
  fi
done
for theme in twentytwentyfour twentytwentythree; do
  if wp_cmd theme is-installed "$theme"; then
    echo "CLEANUP FAIL: theme still installed: $theme"
    exit 5
  fi
done
wp_cmd theme is-installed twentytwentyfive

inactive_plugins="$(wp_cmd plugin list --status=inactive --field=name | paste -sd, -)"
inactive_themes="$(wp_cmd theme list --status=inactive --field=name | paste -sd, -)"
echo "inactive_plugins=${{inactive_plugins:-none}}"
echo "inactive_themes=${{inactive_themes:-none}}"

http_code="$(curl -L -sS --max-time 20 -o /tmp/rollsbar-cleanup-health -w '%{{http_code}}' "https://{DOMAIN}/" || true)"
rm -f /tmp/rollsbar-cleanup-health
[[ "$http_code" =~ ^[23][0-9][0-9]$ ]]
echo "home_http=$http_code"
echo "assert_woocommerce={WC_VERSION}"
echo "assert_products={EXPECTED_PRODUCTS}"
echo "assert_core_checksums=pass"
echo "fallback_theme=twentytwentyfive"
echo "STAGING EXTENSION CLEANUP PASS"
'''
    _, stdout, stderr = client.exec_command("bash -lc " + q(remote), timeout=600)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    print(out, end="" if out.endswith("\n") or not out else "\n")
    if status != 0:
        safe_lines = [line for line in err.splitlines() if "password" not in line.lower()]
        if safe_lines:
            print("remote_stderr=" + " | ".join(safe_lines[-12:])[:1600])
        raise RuntimeError(f"Remote extension cleanup failed with exit status {status}")
    return out


if CONFIRM != "YES":
    raise SystemExit("Refusing staging mutation: set ROLLSBAR_CONFIRM_STAGING_EXTENSION_CLEANUP=YES")

client = None
try:
    client = connect()
    upload_backup_script(client)
    output = execute(client)
    if "STAGING EXTENSION CLEANUP PASS" not in output:
        raise RuntimeError("Cleanup returned without verification marker")
except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError) as exc:
    message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
    print(f"staging_extension_cleanup=failed type={exc.__class__.__name__}")
    print(message)
    raise SystemExit(1)
finally:
    if client is not None:
        remove_remote_script(client)
        client.close()

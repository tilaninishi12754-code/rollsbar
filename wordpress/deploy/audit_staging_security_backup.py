#!/usr/bin/env python3
"""Read-only security/backup-readiness audit for RollsBar REG.RU staging.

The audit intentionally does not create backups, chmod files, install updates,
or mutate WordPress. It only inspects the live staging host over SSH and emits
non-secret assertions that can be used to decide the smallest safe hardening
step.
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
DOMAIN = "staging.rollsbar.ru"


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


def run(client: paramiko.SSHClient, command: str) -> str:
    _, stdout, stderr = client.exec_command(command, timeout=240)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    if status != 0:
        safe_err = " | ".join(
            line for line in err.splitlines()
            if "password" not in line.lower() and "secret" not in line.lower()
        )[-1200:]
        raise RuntimeError(f"Remote audit failed status={status}: {safe_err}")
    print(out, end="" if out.endswith("\n") or not out else "\n")
    return out


remote = r'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="$HOME/www/staging.rollsbar.ru"

ok(){ printf 'PASS  %s\n' "$*"; }
warn(){ printf 'WARN  %s\n' "$*"; }
fail(){ printf 'FAIL  %s\n' "$*"; }

printf 'AUDIT staging_security_backup\n'
printf 'target=staging.rollsbar.ru\n'

if [[ ! -f "$WP_PATH/wp-load.php" ]]; then
  echo 'FAIL  WordPress installation missing'
  exit 2
fi
if ! command -v wp >/dev/null 2>&1; then
  echo 'FAIL  WP-CLI unavailable'
  exit 2
fi

wp --path="$WP_PATH" core is-installed
core_version="$(wp --path="$WP_PATH" core version)"
echo "core_version=$core_version"
if wp --path="$WP_PATH" core verify-checksums --version="$core_version" >/tmp/rollsbar-core-checksums.out 2>/tmp/rollsbar-core-checksums.err; then
  ok 'WordPress core checksums match official release'
else
  fail 'WordPress core checksum verification failed'
  sed -n '1,12p' /tmp/rollsbar-core-checksums.err | sed 's/^/checksum_detail=/'
fi
rm -f /tmp/rollsbar-core-checksums.out /tmp/rollsbar-core-checksums.err

config_bool(){
  local name="$1" expected="$2"
  local value
  value="$(wp --path="$WP_PATH" config get "$name" 2>/dev/null || true)"
  echo "config_${name}=${value:-unset}"
  if [[ "$value" == "$expected" ]]; then ok "$name=$expected"; else warn "$name expected $expected, got ${value:-unset}"; fi
}
config_bool DISALLOW_FILE_EDIT true
config_bool FORCE_SSL_ADMIN true

# Automatic updater is healthy when it has not been globally disabled.
auto_disabled="$(wp --path="$WP_PATH" config get AUTOMATIC_UPDATER_DISABLED 2>/dev/null || true)"
if [[ -z "$auto_disabled" || "$auto_disabled" == "false" || "$auto_disabled" == "0" ]]; then
  ok 'WordPress automatic updater is not globally disabled'
else
  warn "AUTOMATIC_UPDATER_DISABLED=$auto_disabled"
fi

# WP-Cron should be available unless an explicit real cron replacement exists.
cron_disabled="$(wp --path="$WP_PATH" config get DISABLE_WP_CRON 2>/dev/null || true)"
echo "config_DISABLE_WP_CRON=${cron_disabled:-unset}"
if [[ "$cron_disabled" == "true" || "$cron_disabled" == "1" ]]; then
  warn 'WP-Cron disabled; require proof of external system cron'
else
  ok 'WP-Cron is not disabled'
fi

# File permissions: report, do not modify. World-writable executable/config files
# are a hard failure. Group-writable files are surfaced for review only because
# shared hosting ownership models vary.
perm(){ stat -c '%a' "$1" 2>/dev/null || echo missing; }
wp_config_perm="$(perm "$WP_PATH/wp-config.php")"
htaccess_perm="$(perm "$WP_PATH/.htaccess")"
uploads_perm="$(perm "$WP_PATH/wp-content/uploads")"
echo "perm_wp_config=$wp_config_perm"
echo "perm_htaccess=$htaccess_perm"
echo "perm_uploads_dir=$uploads_perm"

case "$wp_config_perm" in
  400|440|600|640) ok "wp-config.php permission=$wp_config_perm" ;;
  missing) fail 'wp-config.php missing' ;;
  *) warn "wp-config.php permission is broader than preferred: $wp_config_perm" ;;
esac

world_writable="$(find "$WP_PATH" -xdev -type f -perm -0002 \( -name '*.php' -o -name '.htaccess' -o -name 'wp-config.php' \) -print 2>/dev/null | head -20)"
if [[ -z "$world_writable" ]]; then
  ok 'No world-writable PHP/config files found'
else
  fail 'World-writable PHP/config files found'
  printf '%s\n' "$world_writable" | sed "s#^$WP_PATH/#world_writable=#"
fi

group_writable_count="$(find "$WP_PATH" -xdev -type f -perm -0020 \( -name '*.php' -o -name '.htaccess' -o -name 'wp-config.php' \) -print 2>/dev/null | wc -l | tr -d ' ')"
echo "group_writable_php_config_count=$group_writable_count"

# Inventory only: inactive extensions expand attack surface if left installed.
active_plugins="$(wp --path="$WP_PATH" plugin list --status=active --field=name | wc -l | tr -d ' ')"
inactive_plugins="$(wp --path="$WP_PATH" plugin list --status=inactive --field=name | wc -l | tr -d ' ')"
inactive_themes="$(wp --path="$WP_PATH" theme list --status=inactive --field=name | wc -l | tr -d ' ')"
echo "active_plugins=$active_plugins"
echo "inactive_plugins=$inactive_plugins"
echo "inactive_themes=$inactive_themes"

# Update visibility. No update is installed by this audit.
core_updates="$(wp --path="$WP_PATH" core check-update --format=count 2>/dev/null || echo unknown)"
plugin_updates="$(wp --path="$WP_PATH" plugin list --update=available --field=name 2>/dev/null | wc -l | tr -d ' ')"
theme_updates="$(wp --path="$WP_PATH" theme list --update=available --field=name 2>/dev/null | wc -l | tr -d ' ')"
echo "core_updates_available=$core_updates"
echo "plugin_updates_available=$plugin_updates"
echo "theme_updates_available=$theme_updates"

# Recovery sizing: canonical project code is in Git, so the irreplaceable live
# state is primarily database + uploads. We measure both before choosing a
# retention policy. No dump is created here.
uploads_kb="$(du -sk "$WP_PATH/wp-content/uploads" 2>/dev/null | awk '{print $1}' || echo 0)"
db_bytes="$(wp --path="$WP_PATH" db size --format=bytes 2>/dev/null || echo unknown)"
echo "uploads_kb=$uploads_kb"
echo "database_bytes=$db_bytes"

df -Pk "$HOME" | awk 'NR==2 {print "home_fs_kb_total="$2"\nhome_fs_kb_used="$3"\nhome_fs_kb_available="$4"\nhome_fs_percent_used="$5}'

# Backups must live outside the public document root. Merely verify that the
# hosting home is writable; do not create the backup directory in this audit.
if [[ -w "$HOME" ]]; then
  ok 'hosting home is writable for a future backup directory outside web-root'
else
  fail 'hosting home is not writable; server-side backup path unavailable'
fi

# Probe HTTP exposure of sensitive paths. We do not require one exact status as
# PHP/server stacks vary, but response bodies must never disclose config/source.
for path in wp-config.php .git/config; do
  code="$(curl -L -sS -o /tmp/rollsbar-sensitive-probe -w '%{http_code}' "https://staging.rollsbar.ru/$path" || true)"
  bytes="$(wc -c </tmp/rollsbar-sensitive-probe 2>/dev/null || echo 0)"
  echo "sensitive_probe_${path//\//_}_http=$code bytes=$bytes"
done
rm -f /tmp/rollsbar-sensitive-probe

echo 'AUDIT COMPLETE — NO STAGING MUTATION PERFORMED'
'''

client = None
try:
    client = connect()
    run(client, "bash -lc " + q(remote))
except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError) as exc:
    message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
    print(f"audit=failed type={exc.__class__.__name__}")
    print(message)
    raise SystemExit(1)
finally:
    if client is not None:
        client.close()

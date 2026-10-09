#!/usr/bin/env python3
"""Restore the latest staging snapshot into a temporary REG.RU database.

No live staging/production database or document-root data is modified. The
one-off database/user and temporary extracted files are removed before success.
"""
from __future__ import annotations

import os
import secrets
import shlex
import socket
import ssl
import string
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip().rstrip("/")
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_RECOVERY_DRILL", "")
ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"
CTX = ssl.create_default_context()
DOMAIN = "staging.rollsbar.ru"


def mask(value: str) -> None:
    if value:
        print(f"::add-mask::{value}", flush=True)


def random_password(length: int = 40) -> str:
    alphabet = string.ascii_letters + string.digits + "-_!@%+"
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in value) and any(c.isupper() for c in value) and any(c.isdigit() for c in value):
            return value


def api_call(params: dict[str, str]) -> ET.Element:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-recovery-drill/1.1"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as response:
        root = ET.fromstring(response.read())
    err = root.find(".//error")
    if err is not None:
        safe = {
            k: v for k, v in err.attrib.items()
            if not any(x in k.lower() for x in ("pass", "auth", "secret", "token"))
        }
        raise RuntimeError(f"ISPmanager error func={params.get('func')}: {safe}")
    return root


def api_auth() -> str:
    root = api_call({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    node = root.find(".//auth")
    sid = node.attrib.get("id", "") if node is not None else ""
    if not sid:
        raise RuntimeError("ISPmanager authentication failed")
    mask(sid)
    return sid


def rows(root: ET.Element) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for elem in root.findall(".//elem"):
        row = {c.tag: (c.text or "").strip() for c in list(elem) if len(list(c)) == 0}
        if row.get("name"):
            result.append(row)
    return result


def find_named(items: list[dict[str, str]], requested: str) -> dict[str, str] | None:
    for row in items:
        name = row.get("name", "")
        if name == requested or name.endswith("_" + requested):
            return row
    return None


def connect_ssh() -> paramiko.SSHClient:
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


def remote(client: paramiko.SSHClient, command: str, timeout: int = 600) -> tuple[int, str, str]:
    _, stdout, stderr = client.exec_command("bash -lc " + shlex.quote(command), timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    return status, out.strip(), err.strip()


def create_temp_db(sid: str, requested: str, password: str) -> tuple[str, str, str, str]:
    if find_named(rows(api_call({"out": "xml", "func": "db", "auth": sid})), requested):
        raise RuntimeError("Recovery drill database name collision")

    api_call(
        {
            "out": "xml",
            "func": "db.edit",
            "auth": sid,
            "sok": "ok",
            "name": requested,
            "owner": USER,
            "server": "MySQL8",
            "charset": "utf8mb4",
            "user": "*",
            "username": requested,
            "password": password,
            "confirm": password,
            "remote_access": "off",
            "comment": "RollsBar temporary recovery drill",
        }
    )

    target = find_named(rows(api_call({"out": "xml", "func": "db", "auth": sid})), requested)
    if target is None:
        raise RuntimeError("Temporary recovery database is not observable after creation")
    actual_db = target.get("name", "")
    pair = target.get("pair", "")
    db_key = target.get("key", "")
    if not actual_db or not pair or not db_key:
        raise RuntimeError("Temporary recovery database metadata is incomplete")

    db_users = rows(api_call({"out": "xml", "func": "db.users", "auth": sid, "elid": pair}))
    actual_user = ""
    for row in db_users:
        name = row.get("name", "")
        if name == requested or name.endswith("_" + requested):
            actual_user = name
            break
    if not actual_user and len(db_users) == 1:
        actual_user = db_users[0].get("name", "")
    if not actual_user:
        raise RuntimeError("Temporary recovery database user was not found")
    return actual_db, actual_user, pair, db_key


def cleanup_temp_db(sid: str, actual_user: str, pair: str, db_key: str, requested: str) -> list[str]:
    errors: list[str] = []
    if actual_user:
        try:
            params = {"out": "xml", "func": "db.users.delete", "auth": sid, "elid": actual_user}
            if pair:
                params["plid"] = pair
            api_call(params)
        except Exception as exc:
            errors.append(f"db_user_delete={exc.__class__.__name__}")
    if db_key:
        try:
            api_call({"out": "xml", "func": "db.delete", "auth": sid, "elid": db_key})
        except Exception as exc:
            errors.append(f"db_delete={exc.__class__.__name__}")
    try:
        if find_named(rows(api_call({"out": "xml", "func": "db", "auth": sid})), requested):
            errors.append("db_still_present=yes")
    except Exception as exc:
        errors.append(f"db_cleanup_verify={exc.__class__.__name__}")
    return errors


def write_client_config(client: paramiko.SSHClient, relpath: str, db_user: str, db_password: str) -> None:
    body = f"[client]\nhost=localhost\nuser={db_user}\npassword={db_password}\n"
    sftp = client.open_sftp()
    try:
        with sftp.open(relpath, "w") as fh:
            fh.write(body.encode("utf-8"))
        sftp.chmod(relpath, 0o600)
    finally:
        sftp.close()


def restore_and_verify(client: paramiko.SSHClient, actual_db: str, config_relpath: str) -> str:
    db_literal = shlex.quote(actual_db)
    config_literal = shlex.quote(config_relpath)
    script = f'''
set -euo pipefail
BACKUP_ROOT="$HOME/rollsbar-backups/staging"
PROJECT_ROOT="$HOME/.rollsbar-deploy"
DB_NAME={db_literal}
CFG="$HOME/{config_literal}"
LATEST="$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -printf '%f\n' | sort | tail -n 1)"
[[ -n "$LATEST" ]]
SNAPSHOT="$BACKUP_ROOT/$LATEST"
WORK="$HOME/.rollsbar-recovery-drill-work-$$"
cleanup() {{ rm -rf "$WORK" "$CFG"; }}
trap cleanup EXIT
umask 077
mkdir -p "$WORK"

printf 'recovery_snapshot=%s\n' "$LATEST"
(cd "$SNAPSHOT" && sha256sum -c SHA256SUMS >/dev/null)
echo 'snapshot_checksums=pass'
gzip -t "$SNAPSHOT/database.sql.gz"
tar -tzf "$SNAPSHOT/uploads.tar.gz" >/dev/null
echo 'snapshot_archives=pass'

manifest_value() {{ awk -F= -v k="$1" '$1==k {{sub(/^[^=]*=/, ""); print; exit}}' "$SNAPSHOT/manifest.txt"; }}
format="$(manifest_value rollsbar_backup_format)"
commit="$(manifest_value project_code_commit)"
site_url="$(manifest_value site_url)"
wp_version="$(manifest_value wordpress_version)"
woo_version="$(manifest_value woocommerce_version)"
products_manifest="$(manifest_value published_products)"
blog_public_manifest="$(manifest_value blog_public)"
wp_config_included="$(manifest_value wp_config_included)"
[[ "$format" == '2' ]]
[[ "$commit" =~ ^[0-9a-f]{{40}}$ ]]
[[ "$site_url" == 'https://{DOMAIN}' ]]
[[ "$wp_version" == '7.1.3' ]]
[[ "$woo_version" == '11.1.2' ]]
[[ "$products_manifest" == '118' ]]
[[ "$blog_public_manifest" == '0' ]]
[[ "$wp_config_included" == 'no' ]]
git -C "$PROJECT_ROOT" cat-file -e "$commit^{{commit}}"
printf 'manifest_format=%s\n' "$format"
printf 'manifest_project_commit=%s\n' "$commit"
echo 'manifest_invariants=pass'

if ! tar -tzf "$SNAPSHOT/uploads.tar.gz" | awk 'BEGIN{{bad=0}} /^\// || /(^|\/)\.\.(\/|$)/ {{bad=1}} END{{exit bad}}'; then
  echo 'unsafe_upload_archive_paths=yes' >&2
  exit 31
fi

gzip -dc "$SNAPSHOT/database.sql.gz" > "$WORK/database.sql"
chmod 600 "$WORK/database.sql"
sql_bytes="$(stat -c '%s' "$WORK/database.sql")"
create_tables="$(grep -c '^CREATE TABLE' "$WORK/database.sql" || true)"
[[ "$sql_bytes" -gt 100000 ]]
[[ "$create_tables" -ge 10 ]]
printf 'sql_uncompressed_bytes=%s\n' "$sql_bytes"
printf 'sql_create_table_statements=%s\n' "$create_tables"

mkdir -p "$WORK/uploads-restore"
tar -xzf "$SNAPSHOT/uploads.tar.gz" -C "$WORK/uploads-restore"
[[ -d "$WORK/uploads-restore/uploads" ]]
tar_files="$(tar -tzf "$SNAPSHOT/uploads.tar.gz" | grep -vc '/$' || true)"
restored_files="$(find "$WORK/uploads-restore/uploads" -type f | wc -l | tr -d ' ')"
[[ "$tar_files" == "$restored_files" ]]
printf 'uploads_restored_files=%s\n' "$restored_files"
echo 'uploads_restore_to_temp=pass'

MYSQL_BIN="$(command -v mysql || command -v mariadb || true)"
[[ -n "$MYSQL_BIN" ]]
"$MYSQL_BIN" --defaults-extra-file="$CFG" "$DB_NAME" < "$WORK/database.sql"
echo 'database_import_to_isolated_temp=pass'

table_count="$("$MYSQL_BIN" --defaults-extra-file="$CFG" -N -B "$DB_NAME" -e 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE();')"
[[ "$table_count" -ge 10 ]]
options_table="$("$MYSQL_BIN" --defaults-extra-file="$CFG" -N -B "$DB_NAME" -e 'SHOW TABLES;' | grep '_options$' | head -n 1)"
[[ "$options_table" =~ ^[A-Za-z0-9_]+$ ]]
prefix="${{options_table%options}}"
posts_table="${{prefix}}posts"
[[ "$posts_table" =~ ^[A-Za-z0-9_]+$ ]]
exists="$("$MYSQL_BIN" --defaults-extra-file="$CFG" -N -B "$DB_NAME" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='${{posts_table}}';")"
[[ "$exists" == '1' ]]
blog_public="$("$MYSQL_BIN" --defaults-extra-file="$CFG" -N -B "$DB_NAME" -e "SELECT option_value FROM ${{options_table}} WHERE option_name='blog_public' LIMIT 1;")"
home_url="$("$MYSQL_BIN" --defaults-extra-file="$CFG" -N -B "$DB_NAME" -e "SELECT option_value FROM ${{options_table}} WHERE option_name='home' LIMIT 1;")"
products="$("$MYSQL_BIN" --defaults-extra-file="$CFG" -N -B "$DB_NAME" -e "SELECT COUNT(*) FROM ${{posts_table}} WHERE post_type='product' AND post_status='publish';")"
[[ "$blog_public" == '0' ]]
[[ "$home_url" == 'https://{DOMAIN}' ]]
[[ "$products" == '118' ]]
printf 'restored_table_count=%s\n' "$table_count"
printf 'restored_blog_public=%s\n' "$blog_public"
printf 'restored_products=%s\n' "$products"
echo 'RESTORE CONTENT INVARIANTS PASS'
'''
    status, out, err = remote(client, script)
    if status != 0:
        safe = " | ".join(line for line in err.splitlines() if "password" not in line.lower())[-1600:]
        raise RuntimeError(f"remote restore verification failed exit={status}: {safe}")
    return out


def main() -> int:
    if CONFIRM != "YES":
        print("Refusing mutation: set ROLLSBAR_CONFIRM_RECOVERY_DRILL=YES")
        return 2
    if not BASE.startswith("https://"):
        print("ISP_MANAGER_URL must use https://")
        return 2

    requested = f"rbdrill_{int(time.time()) % 100000000:08d}"
    temp_password = random_password()
    mask(PASSWORD)
    mask(temp_password)

    sid = actual_db = actual_user = pair = db_key = ""
    client: paramiko.SSHClient | None = None
    config_relpath = f".rollsbar-recovery-drill-{secrets.token_hex(8)}.cnf"
    primary_error: Exception | None = None
    cleanup_errors: list[str] = []

    try:
        sid = api_auth()
        print("stage=create_isolated_temp_database")
        actual_db, actual_user, pair, db_key = create_temp_db(sid, requested, temp_password)
        print("temporary_database=created")
        print("temporary_remote_access=disabled")

        client = connect_ssh()
        write_client_config(client, config_relpath, actual_user, temp_password)
        print("stage=restore_latest_snapshot")
        print(restore_and_verify(client, actual_db, config_relpath))
    except Exception as exc:
        primary_error = exc
    finally:
        if client is not None:
            try:
                sftp = client.open_sftp()
                try:
                    sftp.remove(config_relpath)
                except FileNotFoundError:
                    pass
                finally:
                    sftp.close()
            except Exception:
                pass
            client.close()
        if sid and (actual_user or db_key):
            print("stage=cleanup_isolated_temp_database")
            cleanup_errors = cleanup_temp_db(sid, actual_user, pair, db_key, requested)
            print("temporary_database_cleanup=" + ("pass" if not cleanup_errors else "failed:" + ",".join(cleanup_errors)))

    if primary_error is not None:
        message = str(primary_error).replace(PASSWORD, "***").replace(temp_password, "***")
        print(f"RECOVERY DRILL FAIL type={primary_error.__class__.__name__} detail={message}")
        if cleanup_errors:
            print("OBJECTIVE BLOCKER: temporary recovery resources may require manual cleanup")
        return 1
    if cleanup_errors:
        print("RECOVERY DRILL FAIL: restore passed but cleanup did not fully verify")
        return 1

    print("RECOVERY DRILL PASS — latest snapshot restored into isolated temporary DB, verified, and removed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError) as exc:
        message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
        print(f"RECOVERY DRILL FAIL type={exc.__class__.__name__} detail={message}")
        sys.exit(1)

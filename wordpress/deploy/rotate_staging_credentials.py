#!/usr/bin/env python3
"""Rotate staging-only DB and WordPress admin credentials safely.

This is a recovery tool for generated staging credentials. New values are
persisted to a mode-0600 pending file before mutation, so an interrupted run can
resume without losing the new DB password. No credential value is printed.
"""
from __future__ import annotations

import json
import os
import secrets
import shlex
import socket
import ssl
import string
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip().rstrip("/")
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_ROTATE_STAGING_CREDENTIALS", "")
ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"
CTX = ssl.create_default_context()
MAIN_FILE = ".rollsbar-staging-secrets.json"
PENDING_FILE = ".rollsbar-staging-secrets.pending.json"
RUNTIME_FILE = ".rollsbar-staging-rotate.env"
WP_PATH = "$HOME/www/staging.rollsbar.ru"


def random_password(length: int = 40) -> str:
    alphabet = string.ascii_letters + string.digits + "-_!@%+"
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in value) and any(c.isupper() for c in value) and any(c.isdigit() for c in value):
            return value


def api_call(params: dict[str, str]) -> ET.Element:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-rotate-staging-secrets/1.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as response:
        body = response.read()
    root = ET.fromstring(body)
    err = root.find(".//error")
    if err is not None:
        safe = {k: v for k, v in err.attrib.items() if not any(x in k.lower() for x in ("pass", "auth", "secret", "token"))}
        raise RuntimeError(f"ISPmanager error func={params.get('func')}: {safe}")
    return root


def auth() -> str:
    root = api_call({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    node = root.find(".//auth")
    sid = node.attrib.get("id", "") if node is not None else ""
    if not sid:
        raise RuntimeError("ISPmanager authentication failed")
    return sid


def xml_rows(root: ET.Element) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for elem in root.findall(".//elem"):
        row = {child.tag: (child.text or "").strip() for child in list(elem) if len(list(child)) == 0}
        if row:
            rows.append(row)
    return rows


def connect() -> paramiko.SSHClient:
    host = urlsplit(BASE).hostname or ""
    if not host:
        raise RuntimeError("Could not derive hosting hostname")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, port=22, username=USER, password=PASSWORD,
                   timeout=15, auth_timeout=15, banner_timeout=15,
                   look_for_keys=False, allow_agent=False)
    return client


def read_json(sftp: paramiko.SFTPClient, path: str) -> dict[str, str]:
    with sftp.open(path, "r") as fh:
        return json.loads(fh.read().decode("utf-8"))


def write_json(sftp: paramiko.SFTPClient, path: str, data: dict[str, str]) -> None:
    with sftp.open(path, "w") as fh:
        fh.write((json.dumps(data, sort_keys=True) + "\n").encode("utf-8"))
    sftp.chmod(path, 0o600)


def mask(value: str) -> None:
    if value:
        print(f"::add-mask::{value}", flush=True)


def safe_exec(client: paramiko.SSHClient, command: str) -> None:
    _, stdout, stderr = client.exec_command(command, timeout=120)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    if out:
        print(out, end="" if out.endswith("\n") else "\n")
    if status != 0:
        safe_err = [line for line in err.splitlines() if "pass" not in line.lower() and "db_" not in line.lower()]
        if safe_err:
            print("remote_stderr=" + " | ".join(safe_err[-8:])[:1000])
        raise RuntimeError(f"Remote credential rotation failed with exit status {status}")


if CONFIRM != "YES":
    raise SystemExit("Refusing mutation: set ROLLSBAR_CONFIRM_ROTATE_STAGING_CREDENTIALS=YES")

client = None
sftp = None
try:
    client = connect()
    sftp = client.open_sftp()
    current = read_json(sftp, MAIN_FILE)
    for key in ("db_password", "wp_admin_password"):
        mask(current.get(key, ""))

    try:
        pending = read_json(sftp, PENDING_FILE)
    except FileNotFoundError:
        pending = dict(current)
        pending["db_password"] = random_password()
        pending["wp_admin_password"] = random_password()
        write_json(sftp, PENDING_FILE, pending)

    for key in ("db_password", "wp_admin_password"):
        mask(pending.get(key, ""))

    db_name = current["db_name"]
    db_user = current["db_user"]
    sid = auth()
    db_root = api_call({"out": "xml", "func": "db", "auth": sid})
    db_row = next((row for row in xml_rows(db_root) if row.get("name") == db_name), None)
    if db_row is None:
        raise RuntimeError("Staging database not found during credential rotation")

    plid_candidates = [db_row.get("key", ""), db_row.get("pair", ""), db_row.get("id", ""), db_name]
    plid = ""
    for candidate in [x for x in plid_candidates if x]:
        try:
            api_call({"out": "xml", "func": "db.users.edit", "auth": sid, "plid": candidate, "elid": db_user})
            plid = candidate
            break
        except RuntimeError:
            continue
    if not plid:
        raise RuntimeError("Could not resolve ISPmanager database-user parent identifier")

    api_call({
        "out": "xml",
        "func": "db.users.edit",
        "auth": sid,
        "sok": "ok",
        "plid": plid,
        "elid": db_user,
        "name": db_user,
        "username": db_user,
        "password": pending["db_password"],
        "confirm": pending["db_password"],
        "remote_access": "off",
    })
    print("database_password=rotated")

    runtime = (
        "export NEW_DB_PASSWORD=" + shlex.quote(pending["db_password"]) + "\n" +
        "export NEW_WP_ADMIN_PASSWORD=" + shlex.quote(pending["wp_admin_password"]) + "\n"
    )
    with sftp.open(RUNTIME_FILE, "w") as fh:
        fh.write(runtime.encode("utf-8"))
    sftp.chmod(RUNTIME_FILE, 0o600)

    remote = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
RUNTIME="$HOME/{RUNTIME_FILE}"
cleanup() {{ rm -f "$RUNTIME"; }}
trap cleanup EXIT
source "$RUNTIME"
WP_PATH={WP_PATH}
wp --path="$WP_PATH" config set DB_PASSWORD "$NEW_DB_PASSWORD" --type=constant
wp --path="$WP_PATH" db check >/dev/null
wp --path="$WP_PATH" user update rollsbar_staging_admin --user_pass="$NEW_WP_ADMIN_PASSWORD" >/dev/null
wp --path="$WP_PATH" core is-installed
printf 'wordpress_admin_password=rotated\n'
printf 'database_connectivity=pass\n'
printf 'wordpress_core=pass\n'
'''
    safe_exec(client, "bash -lc " + shlex.quote(remote))

    write_json(sftp, MAIN_FILE, pending)
    try:
        sftp.remove(PENDING_FILE)
    except FileNotFoundError:
        pass
    print("secret_file=updated mode=0600")
    print("ROTATE STAGING CREDENTIALS PASS")
except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError, KeyError) as exc:
    print(f"staging_rotation=failed type={exc.__class__.__name__}")
    print(str(exc).replace(PASSWORD, "***"))
    raise SystemExit(1)
finally:
    if sftp is not None:
        try:
            sftp.remove(RUNTIME_FILE)
        except Exception:
            pass
        sftp.close()
    if client is not None:
        client.close()

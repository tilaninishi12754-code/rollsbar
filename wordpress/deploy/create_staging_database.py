#!/usr/bin/env python3
"""Create an isolated RollsBar staging database in ISPmanager.

The database password is generated once and persisted only in the hosting
account home directory with mode 0600. Nothing secret is printed or committed.
The operation is idempotent and never edits/deletes unrelated databases.
"""
from __future__ import annotations

import json
import os
import secrets
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
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_CREATE_STAGING_DB", "")
ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"
CTX = ssl.create_default_context()
TARGET_DB = "rollsbar_staging"
TARGET_DB_USER = "rollsbar_staging"
SECRET_FILE = ".rollsbar-staging-secrets.json"


def call(params: dict[str, str]) -> tuple[ET.Element, bytes]:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-create-staging-db/1.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as response:
        body = response.read()
    root = ET.fromstring(body)
    err = root.find(".//error")
    if err is not None:
        safe = {k: v for k, v in err.attrib.items() if not any(x in k.lower() for x in ("pass", "auth", "secret", "token"))}
        raise RuntimeError(f"ISPmanager error func={params.get('func')}: {safe}")
    return root, body


def auth() -> str:
    root, _ = call({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    node = root.find(".//auth")
    sid = node.attrib.get("id", "") if node is not None else ""
    if not sid:
        raise RuntimeError("ISPmanager authentication failed")
    return sid


def db_rows(root: ET.Element) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for elem in root.findall(".//elem"):
        row = {child.tag: (child.text or "").strip() for child in list(elem) if len(list(child)) == 0}
        if row.get("name"):
            rows.append(row)
    return rows


def find_target(rows: list[dict[str, str]]) -> dict[str, str] | None:
    for row in rows:
        name = row.get("name", "")
        if name == TARGET_DB or name.endswith("_" + TARGET_DB):
            return row
    return None


def random_password(length: int = 36) -> str:
    alphabet = string.ascii_letters + string.digits + "-_!@%+"
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in value) and any(c.isupper() for c in value) and any(c.isdigit() for c in value):
            return value


def ssh_client() -> paramiko.SSHClient:
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
        timeout=12,
        auth_timeout=12,
        banner_timeout=12,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def read_or_create_secret() -> tuple[paramiko.SSHClient, dict[str, str]]:
    client = ssh_client()
    sftp = client.open_sftp()
    try:
        try:
            with sftp.open(SECRET_FILE, "r") as fh:
                data = json.loads(fh.read().decode("utf-8"))
        except FileNotFoundError:
            data = {
                "db_password": random_password(),
                "wp_admin_password": random_password(),
                "db_name": TARGET_DB,
                "db_user": TARGET_DB_USER,
            }
            payload = (json.dumps(data, sort_keys=True) + "\n").encode("utf-8")
            with sftp.open(SECRET_FILE, "w") as fh:
                fh.write(payload)
            sftp.chmod(SECRET_FILE, 0o600)
        required = {"db_password", "wp_admin_password"}
        if not required.issubset(data) or not all(data.get(k) for k in required):
            raise RuntimeError("Existing staging secret file is incomplete")
        return client, data
    finally:
        sftp.close()


def persist_actual(client: paramiko.SSHClient, data: dict[str, str]) -> None:
    sftp = client.open_sftp()
    try:
        with sftp.open(SECRET_FILE, "w") as fh:
            fh.write((json.dumps(data, sort_keys=True) + "\n").encode("utf-8"))
        sftp.chmod(SECRET_FILE, 0o600)
    finally:
        sftp.close()


if CONFIRM != "YES":
    raise SystemExit("Refusing mutation: set ROLLSBAR_CONFIRM_CREATE_STAGING_DB=YES")
if not BASE.startswith("https://"):
    raise SystemExit("ISP_MANAGER_URL must use https://")

client = None
try:
    client, secret_data = read_or_create_secret()
    sid = auth()
    root, _ = call({"out": "xml", "func": "db", "auth": sid})
    rows = db_rows(root)
    target = find_target(rows)

    if target is None:
        params = {
            "out": "xml",
            "func": "db.edit",
            "auth": sid,
            "sok": "ok",
            "name": TARGET_DB,
            "owner": USER,
            "server": "MySQL8",
            "charset": "utf8mb4",
            "user": "*",
            "username": TARGET_DB_USER,
            "password": secret_data["db_password"],
            "confirm": secret_data["db_password"],
            "remote_access": "off",
            "comment": "RollsBar isolated staging",
        }
        call(params)
        root, _ = call({"out": "xml", "func": "db", "auth": sid})
        rows = db_rows(root)
        target = find_target(rows)
        if target is None:
            raise RuntimeError("Database create returned without error, but target DB was not found")
        state = "created"
    else:
        state = "already_exists"

    actual_db = target.get("name", TARGET_DB)
    pair = target.get("pair", "")
    actual_user = secret_data.get("db_user", TARGET_DB_USER)
    if pair:
        users_root, _ = call({"out": "xml", "func": "db.users", "auth": sid, "elid": pair})
        users = db_rows(users_root)
        candidate_users = [row.get("name", "") for row in users if row.get("name")]
        preferred = [name for name in candidate_users if name == TARGET_DB_USER or name.endswith("_" + TARGET_DB_USER)]
        if preferred:
            actual_user = preferred[0]
        elif len(candidate_users) == 1:
            actual_user = candidate_users[0]

    secret_data["db_name"] = actual_db
    secret_data["db_user"] = actual_user
    secret_data["db_host"] = "localhost"
    persist_actual(client, secret_data)

    print(f"staging_database={state}")
    print(f"database_name={actual_db}")
    print(f"database_user={actual_user}")
    print("database_host=localhost")
    print(f"secret_file={SECRET_FILE} mode=0600")
    print("remote_access=disabled")
    print("CREATE STAGING DATABASE PASS")
except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError) as exc:
    print(f"staging_database=failed type={exc.__class__.__name__}")
    print(str(exc).replace(PASSWORD, "***"))
    raise SystemExit(1)
finally:
    if client is not None:
        client.close()

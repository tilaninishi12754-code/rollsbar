#!/usr/bin/env python3
"""Read-only ISPmanager probe for values needed to create RollsBar staging.

Reads the current site/database lists and blank create forms. It never sends
`sok`, so it cannot create or modify objects. Secrets are masked/omitted.
"""
from __future__ import annotations

import os
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = os.environ["ISP_MANAGER_URL"].strip().rstrip("/")
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"
CTX = ssl.create_default_context()

SAFE_TAGS = {
    "name", "id", "key", "pair", "owner", "site_name", "site_home",
    "site_ipaddrs", "site_php_mode", "site_php_fpm_version", "site_ssl_cert",
    "lp_db_source", "lp_edit_db_server", "lp_edit_db_server_info",
    "db_server", "db_server_info", "type", "server", "server_host",
    "server_hostandport", "charset", "php_mode", "php_version", "home",
    "docroot", "ipaddr", "ipaddrs", "ssl", "active", "status", "version"
}
DENY = ("pass", "secret", "token", "auth", "session")


def request(params: dict[str, str]) -> ET.Element:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-staging-plan-probe/1.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=20) as response:
        body = response.read()
    root = ET.fromstring(body)
    err = root.find(".//error")
    if err is not None:
        details = {k: v for k, v in err.attrib.items() if not any(x in k.lower() for x in DENY)}
        raise SystemExit(f"API error func={params.get('func')}: {details}")
    return root


def auth_params() -> dict[str, str]:
    root = request({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    auth = root.find(".//auth")
    sid = auth.attrib.get("id", "") if auth is not None else ""
    if not sid:
        raise SystemExit("Session authentication failed")
    return {"auth": sid}


def clean(text: str) -> str:
    text = text.replace(PASSWORD, "***").replace(USER, "<account-user>")
    return " ".join(text.split())[:240]


def scalar_children(node: ET.Element) -> dict[str, str]:
    row: dict[str, str] = {}
    for child in list(node):
        tag = child.tag.lower()
        if any(x in tag for x in DENY):
            continue
        if len(list(child)):
            continue
        text = clean(child.text or "")
        if text and tag in SAFE_TAGS:
            row[tag] = text
    return row


def print_rows(label: str, root: ET.Element) -> None:
    rows: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for node in root.iter():
        row = scalar_children(node)
        if row:
            sig = tuple(sorted(row.items()))
            if sig not in seen:
                seen.add(sig)
                rows.append(row)
    print(f"## {label}: {len(rows)} safe row(s)")
    for i, row in enumerate(rows[:60], 1):
        print(f"{i}. " + ", ".join(f"{k}={v}" for k, v in sorted(row.items())))


def probe(func: str, auth: dict[str, str]) -> None:
    root = request({**auth, "out": "xml", "func": func})
    print_rows(func, root)


if not BASE.startswith("https://"):
    raise SystemExit("ISP_MANAGER_URL must use https://")

auth = auth_params()
print("ISPmanager RollsBar staging plan probe")
print(f"endpoint={urllib.parse.urlsplit(ENDPOINT).hostname}")
for fn in ("site", "site.edit", "db", "db.edit"):
    probe(fn, auth)
print("mutation=not attempted")
print("STAGING PLAN PROBE PASS")

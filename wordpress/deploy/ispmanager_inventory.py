#!/usr/bin/env python3
"""Read-only ISPmanager inventory for staging deployment planning.

Prints only non-secret metadata for websites and databases. Never mutates state.
Required env: ISP_MANAGER_URL, ISP_MANAGER_USER, ISP_MANAGER_PASSWORD.
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

ctx = ssl.create_default_context()

DENY = ("pass", "password", "secret", "token", "key", "auth", "session")
ALLOW = {
    "id", "name", "domain", "docroot", "path", "homedir", "home", "owner",
    "user", "ip", "php", "php_mode", "ssl", "ssl_redirect", "status", "type",
    "host", "server", "charset", "comment", "active", "enabled", "preset"
}


def call(params: dict[str, str]) -> ET.Element:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-ispmanager-inventory/1.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=20) as response:
        body = response.read()
    root = ET.fromstring(body)
    err = root.find(".//error")
    if err is not None:
        raise SystemExit(f"ISPmanager API error for func={params.get('func')}: {err.attrib}")
    return root


def auth_params() -> dict[str, str]:
    root = call({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    auth = root.find(".//auth")
    sid = auth.attrib.get("id", "") if auth is not None else ""
    if not sid:
        raise SystemExit("ISPmanager session authentication failed")
    return {"auth": sid}


def safe_rows(root: ET.Element) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    # ISPmanager list responses commonly expose objects as <elem> children.
    candidates = root.findall(".//elem")
    if not candidates:
        # Fall back to direct children that themselves contain scalar fields.
        candidates = [node for node in root.iter() if len(list(node)) and node.tag not in {"doc", "metadata"}]
    seen: set[tuple[tuple[str, str], ...]] = set()
    for node in candidates:
        row: dict[str, str] = {}
        for child in list(node):
            tag = child.tag.lower()
            if any(bad in tag for bad in DENY):
                continue
            text = " ".join("".join(child.itertext()).split())
            if not text:
                continue
            if tag in ALLOW or len(text) <= 180:
                row[tag] = text[:180]
        if row:
            sig = tuple(sorted(row.items()))
            if sig not in seen:
                seen.add(sig)
                rows.append(row)
    return rows


def print_inventory(label: str, func: str, auth: dict[str, str]) -> None:
    root = call({**auth, "out": "xml", "func": func})
    rows = safe_rows(root)
    print(f"## {label}: {len(rows)} row(s)")
    if not rows:
        print("(none)")
        return
    for idx, row in enumerate(rows[:50], 1):
        compact = ", ".join(f"{k}={v}" for k, v in sorted(row.items()))
        print(f"{idx}. {compact}")


if not BASE.startswith("https://"):
    raise SystemExit("ISP_MANAGER_URL must use https://")

auth = auth_params()
print("ISPmanager read-only inventory")
print(f"endpoint={urllib.parse.urlsplit(ENDPOINT).hostname}")
print_inventory("webdomains", "webdomain", auth)
print_inventory("databases", "db", auth)
print("mutation=not attempted")

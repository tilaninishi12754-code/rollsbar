#!/usr/bin/env python3
"""Read-only ISPmanager inventory for staging deployment planning.

Prints only non-secret metadata for websites and databases. Never mutates state.
Required env: ISP_MANAGER_URL, ISP_MANAGER_USER, ISP_MANAGER_PASSWORD.
"""
from __future__ import annotations

import json
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
KEEP = {
    "id", "name", "domain", "docroot", "path", "homedir", "home", "owner",
    "user", "ip", "ipaddr", "ipaddrs", "php", "php_mode", "php_version",
    "ssl", "ssl_redirect", "status", "type", "host", "server", "server_host",
    "server_hostandport", "charset", "comment", "active", "enabled", "preset",
    "item", "pair", "version", "size"
}


def request_bytes(params: dict[str, str]) -> bytes:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-ispmanager-inventory/1.1"})
    with urllib.request.urlopen(req, context=ctx, timeout=20) as response:
        return response.read()


def auth_params() -> dict[str, str]:
    body = request_bytes({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    root = ET.fromstring(body)
    err = root.find(".//error")
    if err is not None:
        raise SystemExit(f"ISPmanager auth error: {err.attrib}")
    auth = root.find(".//auth")
    sid = auth.attrib.get("id", "") if auth is not None else ""
    if not sid:
        raise SystemExit("ISPmanager session authentication failed")
    return {"auth": sid}


def sanitize_mapping(row: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in row.items():
        k = str(key).lower()
        if any(bad in k for bad in DENY):
            continue
        if isinstance(value, (dict, list)):
            continue
        text = str(value).strip()
        if not text:
            continue
        if k in KEEP:
            out[k] = text[:240]
    return out


def walk_json(value):
    if isinstance(value, dict):
        safe = sanitize_mapping(value)
        if safe:
            yield safe
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def inventory(func: str, auth: dict[str, str]) -> list[dict[str, str]]:
    body = request_bytes({**auth, "out": "json", "func": func})
    try:
        payload = json.loads(body.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise SystemExit(f"Could not parse JSON for {func}: {exc.__class__.__name__}")
    rows: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for row in walk_json(payload):
        sig = tuple(sorted(row.items()))
        if sig not in seen:
            seen.add(sig)
            rows.append(row)
    return rows


def print_inventory(label: str, func: str, auth: dict[str, str]) -> None:
    rows = inventory(func, auth)
    print(f"## {label}: {len(rows)} candidate row(s)")
    if not rows:
        print("(none)")
        return
    for idx, row in enumerate(rows[:80], 1):
        print(f"{idx}. " + ", ".join(f"{k}={v}" for k, v in sorted(row.items())))


if not BASE.startswith("https://"):
    raise SystemExit("ISP_MANAGER_URL must use https://")

auth = auth_params()
print("ISPmanager read-only inventory")
print(f"endpoint={urllib.parse.urlsplit(ENDPOINT).hostname}")
print_inventory("webdomains", "webdomain", auth)
print_inventory("databases", "db", auth)
print("mutation=not attempted")

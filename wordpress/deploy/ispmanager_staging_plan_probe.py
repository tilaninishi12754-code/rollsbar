#!/usr/bin/env python3
"""Read-only ISPmanager probe for RollsBar staging and SSL parameters.

Reads current website/database/SSL lists, Let's Encrypt form and event logs. It
never sends `sok`, so it cannot create or modify objects. Secrets are masked.
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
STAGING_DOMAIN = "staging.rollsbar.ru"

SAFE_TAGS = {
    "name", "id", "key", "pair", "owner", "site_name", "site_home",
    "site_ipaddrs", "site_php_mode", "site_php_fpm_version", "site_ssl_cert",
    "lp_db_source", "lp_edit_db_server", "lp_edit_db_server_info",
    "db_server", "db_server_info", "type", "server", "server_host",
    "server_hostandport", "charset", "php_mode", "php_version", "home",
    "docroot", "ipaddr", "ipaddrs", "ssl", "secure", "sslcert", "ssl_cert",
    "active", "status", "state", "version", "valid_after", "valid_before",
    "aliases", "email", "domains", "domain", "domain_name", "crtname",
    "username", "keylen", "enable_cert", "wildcard", "dns_check", "date",
    "message", "description", "code", "city", "org", "department"
}
DENY = ("pass", "secret", "token", "auth", "session", "keydata", "private", "crt", "cacrt")


def raw_request(params: dict[str, str]) -> tuple[ET.Element, dict[str, str] | None]:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-staging-plan-probe/1.4"})
    with urllib.request.urlopen(req, context=CTX, timeout=20) as response:
        body = response.read()
    root = ET.fromstring(body)
    err = root.find(".//error")
    details = None
    if err is not None:
        details = {k: v for k, v in err.attrib.items() if not any(x in k.lower() for x in DENY)}
    return root, details


def request(params: dict[str, str]) -> ET.Element:
    root, error = raw_request(params)
    if error is not None:
        raise RuntimeError(str(error))
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
    return " ".join(text.split())[:300]


def scalar_children(node: ET.Element) -> dict[str, str]:
    row: dict[str, str] = {}
    for child in list(node):
        tag = child.tag.lower()
        if any(x in tag for x in DENY) or len(list(child)):
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
    for i, row in enumerate(rows[:100], 1):
        print(f"{i}. " + ", ".join(f"{k}={v}" for k, v in sorted(row.items())))


def print_form_metadata(label: str, root: ET.Element) -> None:
    print(f"## {label} form metadata")
    emitted: set[str] = set()
    count = 0
    for node in root.iter():
        attrs = {k.lower(): clean(v) for k, v in node.attrib.items()}
        joined = " ".join(attrs.values()).lower()
        if any(x in joined for x in DENY):
            continue
        parts: list[str] = []
        for key in ("name", "id", "key", "type", "value"):
            val = attrs.get(key)
            if val and not any(x in key for x in DENY):
                parts.append(f"{key}={val}")
        tag = node.tag.lower()
        text = clean(node.text or "")
        if tag in {"field", "select", "option", "item", "value", "msg"} and text and not any(x in tag for x in DENY):
            if len(text) <= 160:
                parts.append(f"text={text}")
        if parts:
            line = f"{tag}:" + ",".join(parts)
            if line not in emitted:
                emitted.add(line)
                print(line)
                count += 1
                if count >= 200:
                    break


def probe(func: str, auth: dict[str, str], extra: dict[str, str] | None = None, metadata: bool = False) -> None:
    params = {**auth, "out": "xml", "func": func, **(extra or {})}
    root, error = raw_request(params)
    if error is not None:
        print(f"## {func}: unsupported/error {error}")
        return
    print_rows(func, root)
    if metadata:
        print_form_metadata(func, root)


if not BASE.startswith("https://"):
    raise SystemExit("ISP_MANAGER_URL must use https://")

auth = auth_params()
print("ISPmanager RollsBar staging plan probe")
print(f"endpoint={urllib.parse.urlsplit(ENDPOINT).hostname}")
probe("webdomain", auth)
probe("webdomain.edit", auth, {"elid": STAGING_DOMAIN}, metadata=True)
probe("sslcert", auth)
probe("letsencrypt.generate", auth, {"elid": STAGING_DOMAIN}, metadata=True)
probe("letsencrypt.logs", auth)
probe("db", auth)
probe("db.edit", auth, metadata=True)
print("mutation=not attempted")
print("STAGING PLAN PROBE PASS")

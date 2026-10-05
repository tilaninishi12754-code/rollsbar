#!/usr/bin/env python3
"""Read-only ISPmanager DNS inventory for rollsbar.ru."""
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
ZONE = "rollsbar.ru"


def call(params: dict[str, str]) -> tuple[ET.Element, dict[str, str] | None]:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-dns-probe/1.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=20) as response:
        body = response.read()
    root = ET.fromstring(body)
    err = root.find(".//error")
    return root, (dict(err.attrib) if err is not None else None)


def auth() -> str:
    root, err = call({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    if err:
        raise SystemExit(f"auth_error={err}")
    node = root.find(".//auth")
    sid = node.attrib.get("id", "") if node is not None else ""
    if not sid:
        raise SystemExit("auth_failed")
    return sid


def text_rows(root: ET.Element) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for elem in root.findall(".//elem"):
        row: dict[str, str] = {}
        for child in list(elem):
            if len(list(child)):
                continue
            tag = child.tag.lower()
            if any(x in tag for x in ("pass", "auth", "secret", "token")):
                continue
            value = " ".join((child.text or "").split())
            if value:
                row[tag] = value[:240]
        if row:
            rows.append(row)
    return rows

sid = auth()
root, err = call({"out": "xml", "func": "domain", "auth": sid})
if err:
    print(f"domain_function=unsupported error={err}")
    raise SystemExit(0)
rows = text_rows(root)
print(f"dns_zones={len(rows)}")
for row in rows:
    name = row.get("name") or row.get("displayname") or ""
    print("zone=" + name)

zone_names = {(row.get("name") or row.get("displayname") or "").rstrip(".") for row in rows}
if ZONE not in zone_names:
    print(f"target_zone={ZONE} present=no")
    print("mutation=not attempted")
    raise SystemExit(0)

records_root, rec_err = call({"out": "xml", "func": "domain.record", "auth": sid, "plid": ZONE})
if rec_err:
    print(f"domain_record_error={rec_err}")
    raise SystemExit(0)
records = text_rows(records_root)
print(f"target_zone={ZONE} present=yes records={len(records)}")
for row in records:
    print("record=" + ",".join(f"{k}:{v}" for k, v in sorted(row.items())))
print("mutation=not attempted")

#!/usr/bin/env python3
"""Delete only orphaned RollsBar recovery-drill databases from ISPmanager.

Safety boundary: only DB rows whose visible name is exactly rbdrill_######## or
ends with _rbdrill_######## are eligible. No staging/production DB can match.
"""
from __future__ import annotations

import os
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = os.environ["ISP_MANAGER_URL"].strip().rstrip("/")
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_RECOVERY_ORPHAN_CLEANUP", "")
ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"
CTX = ssl.create_default_context()
DRILL_SUFFIX_RE = re.compile(r"(?:^|_)rbdrill_([0-9]{8})$")


def mask(value: str) -> None:
    if value:
        print(f"::add-mask::{value}", flush=True)


def api_call(params: dict[str, str]) -> ET.Element:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-recovery-cleanup/1.1"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as response:
        root = ET.fromstring(response.read())
    err = root.find(".//error")
    if err is not None:
        safe = {
            k: v
            for k, v in err.attrib.items()
            if not any(x in k.lower() for x in ("pass", "auth", "secret", "token"))
        }
        raise RuntimeError(f"ISPmanager error func={params.get('func')}: {safe}")
    return root


def auth() -> str:
    root = api_call({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    node = root.find(".//auth")
    sid = node.attrib.get("id", "") if node is not None else ""
    if not sid:
        raise RuntimeError("ISPmanager authentication failed")
    mask(sid)
    return sid


def elem_row(elem: ET.Element) -> dict[str, str]:
    row: dict[str, str] = {}
    for key, value in elem.attrib.items():
        if not any(x in key.lower() for x in ("pass", "auth", "secret", "token")):
            row[key] = (value or "").strip()
    for child in elem.iter():
        if child is elem or list(child):
            continue
        tag = child.tag
        if any(x in tag.lower() for x in ("pass", "auth", "secret", "token")):
            continue
        value = (child.text or "").strip()
        if value and tag not in row:
            row[tag] = value
    return row


def db_rows(root: ET.Element) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for elem in root.findall(".//elem"):
        row = elem_row(elem)
        if row.get("name"):
            result.append(row)
    return result


def eligible(row: dict[str, str]) -> bool:
    return bool(DRILL_SUFFIX_RE.search(row.get("name", "")))


def enrich_db(sid: str, row: dict[str, str]) -> dict[str, str]:
    enriched = dict(row)
    pair = enriched.get("pair", "")
    if pair:
        try:
            detail = api_call({"out": "xml", "func": "db.edit", "auth": sid, "elid": pair})
            for elem in detail.findall(".//elem"):
                enriched.update({k: v for k, v in elem_row(elem).items() if v})
            for child in detail.iter():
                if list(child):
                    continue
                tag = child.tag
                if any(x in tag.lower() for x in ("pass", "auth", "secret", "token")):
                    continue
                value = (child.text or "").strip()
                if value and tag not in enriched:
                    enriched[tag] = value
        except Exception:
            pass
    return enriched


def delete_one(sid: str, row: dict[str, str]) -> None:
    row = enrich_db(sid, row)
    name = row.get("name", "")
    if not eligible(row):
        raise RuntimeError("Refusing cleanup for non-rbdrill database")

    pair = row.get("pair", "")
    documented_key = row.get("key", "")
    panel_elid = row.get("elid", "")
    delete_id = documented_key or panel_elid
    print(
        "orphan_candidate="
        + name
        + f" pair_present={'yes' if pair else 'no'} key_present={'yes' if documented_key else 'no'} elid_present={'yes' if panel_elid else 'no'}"
    )

    if not delete_id:
        safe_fields = ",".join(sorted(k for k in row if k not in {"password", "passwd"}))
        raise RuntimeError(f"rbdrill database delete identifier unavailable; safe_fields={safe_fields}")

    if pair:
        try:
            users = db_rows(api_call({"out": "xml", "func": "db.users", "auth": sid, "elid": pair}))
            for user in users:
                user_name = user.get("name", "")
                if DRILL_SUFFIX_RE.search(user_name):
                    api_call(
                        {
                            "out": "xml",
                            "func": "db.users.delete",
                            "auth": sid,
                            "plid": pair,
                            "elid": user_name,
                        }
                    )
                    print("orphan_user_deleted=yes")
        except Exception as exc:
            print(f"orphan_user_cleanup_warning={exc.__class__.__name__}")

    api_call({"out": "xml", "func": "db.delete", "auth": sid, "elid": delete_id})
    print("orphan_database_deleted=" + name)


def main() -> int:
    if CONFIRM != "YES":
        print("Refusing mutation: set ROLLSBAR_CONFIRM_RECOVERY_ORPHAN_CLEANUP=YES")
        return 2
    if not BASE.startswith("https://"):
        print("ISP_MANAGER_URL must use https://")
        return 2

    mask(PASSWORD)
    sid = auth()
    all_rows = db_rows(api_call({"out": "xml", "func": "db", "auth": sid}))
    targets = [row for row in all_rows if eligible(row)]
    print(f"rbdrill_orphans_found={len(targets)}")
    for row in targets:
        delete_one(sid, row)

    remaining_rows = db_rows(api_call({"out": "xml", "func": "db", "auth": sid}))
    remaining = [row.get("name", "") for row in remaining_rows if eligible(row)]
    print(f"rbdrill_orphans_remaining={len(remaining)}")
    if remaining:
        print("RECOVERY ORPHAN CLEANUP FAIL remaining=" + ",".join(remaining))
        return 1
    print("RECOVERY ORPHAN CLEANUP PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
        print(f"RECOVERY ORPHAN CLEANUP FAIL type={exc.__class__.__name__} detail={message}")
        raise SystemExit(1)

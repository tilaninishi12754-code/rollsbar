#!/usr/bin/env python3
"""Read-only ISPmanager Let's Encrypt log probe for staging.rollsbar.ru."""
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
DOMAIN = "staging.rollsbar.ru"
CERTS = ("staging.rollsbar.ru_le2", "staging.rollsbar.ru_le1")
DENY = ("pass", "secret", "token", "auth", "session", "keydata", "private")


def call(params: dict[str, str]) -> tuple[ET.Element, dict[str, str] | None]:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-letsencrypt-log-probe/1.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=20) as response:
        body = response.read()
    root = ET.fromstring(body)
    err = root.find(".//error")
    if err is None:
        return root, None
    safe = {k: v for k, v in err.attrib.items() if not any(x in k.lower() for x in DENY)}
    return root, safe


def auth() -> str:
    root, error = call({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    if error:
        raise SystemExit(f"auth_error={error}")
    node = root.find(".//auth")
    sid = node.attrib.get("id", "") if node is not None else ""
    if not sid:
        raise SystemExit("auth_failed")
    return sid


def clean(text: str) -> str:
    return " ".join(text.replace(PASSWORD, "***").replace(USER, "<account-user>").split())[:1000]


def dump(root: ET.Element) -> None:
    found = 0
    for elem in root.iter():
        row: list[str] = []
        for child in list(elem):
            if len(list(child)):
                continue
            tag = child.tag.lower()
            if any(x in tag for x in DENY):
                continue
            text = clean(child.text or "")
            if text:
                row.append(f"{tag}={text}")
        if row:
            print(" | ".join(row))
            found += 1
            if found >= 100:
                break
    if not found:
        # Some ISPmanager log responses use attributes or plain nested text.
        for elem in root.iter():
            attrs = {k: clean(v) for k, v in elem.attrib.items() if not any(x in k.lower() for x in DENY)}
            text = clean(elem.text or "")
            if attrs or text:
                print(f"tag={elem.tag} attrs={attrs} text={text}")
                found += 1
                if found >= 100:
                    break
    print(f"rows={found}")


sid = auth()
print("LETSENCRYPT LOG PROBE")
for cert in CERTS:
    print(f"## cert={cert}")
    attempts = (
        {"elid": DOMAIN, "sslcert": cert},
        {"elid": cert, "sslcert": cert},
    )
    for i, extra in enumerate(attempts, 1):
        root, error = call({"out": "xml", "func": "letsencrypt.logs", "auth": sid, **extra})
        if error:
            print(f"attempt={i} error={error}")
            continue
        print(f"attempt={i} success")
        dump(root)
        break
print("mutation=not attempted")
print("LETSENCRYPT LOG PROBE COMPLETE")

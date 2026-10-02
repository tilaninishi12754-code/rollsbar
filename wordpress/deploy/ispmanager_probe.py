#!/usr/bin/env python3
"""Read-only ISPmanager API capability probe.

Required environment variables:
  ISP_MANAGER_URL
  ISP_MANAGER_USER
  ISP_MANAGER_PASSWORD

The script authenticates, masks nothing itself because secrets are never printed,
then checks whether the current account can read the website and database lists.
It performs no create/update/delete operations.
"""
from __future__ import annotations

import os
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = os.environ["ISP_MANAGER_URL"].rstrip("/")
USER = os.environ["ISP_MANAGER_USER"]
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"]
VERIFY_TLS = os.environ.get("ISP_TLS_VERIFY", "1").lower() not in {"0", "false", "no"}

if not BASE.startswith("https://"):
    raise SystemExit("ISP_MANAGER_URL must use https://")

context = ssl.create_default_context()
if not VERIFY_TLS:
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

def call(params: dict[str, str]) -> bytes:
    url = BASE + "/ispmgr?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-ispmanager-probe/1.0"})
    with urllib.request.urlopen(req, context=context, timeout=20) as response:
        return response.read()

auth_xml = call(
    {
        "out": "xml",
        "func": "auth",
        "username": USER,
        "password": PASSWORD,
    }
)

root = ET.fromstring(auth_xml)
auth = root.find("auth")
if auth is None or not auth.attrib.get("id"):
    raise SystemExit("ISPmanager authentication failed or returned no session id")

session_id = auth.attrib["id"]

checks = {}
for func in ("webdomain", "db"):
    try:
        payload = call({"auth": session_id, "out": "xml", "func": func})
        parsed = ET.fromstring(payload)
        error = parsed.find("error")
        checks[func] = "error" if error is not None else "ok"
    except Exception as exc:
        checks[func] = f"failed:{exc.__class__.__name__}"

print("ISPmanager read-only probe")
print(f"- auth: ok")
print(f"- websites API: {checks['webdomain']}")
print(f"- databases API: {checks['db']}")

if checks["webdomain"] != "ok" or checks["db"] != "ok":
    raise SystemExit("Required read-only ISPmanager API capabilities are not available for this account")

print("- mutation: not attempted")
print("PROBE PASS")

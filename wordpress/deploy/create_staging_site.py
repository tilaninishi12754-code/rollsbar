#!/usr/bin/env python3
"""Create the isolated RollsBar staging WWW domain in ISPmanager.

Idempotent and deliberately narrow: creates only staging.rollsbar.ru, with
PHP enabled, no SSL yet, no aliases and no mail account. It never edits or
deletes an existing WWW domain.
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
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_CREATE_STAGING", "")
DOMAIN = "staging.rollsbar.ru"
HOME = "www/staging.rollsbar.ru"
IP = "37.140.192.67"
ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"
CTX = ssl.create_default_context()


def call(params: dict[str, str]) -> tuple[ET.Element, bytes]:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-create-staging/1.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as response:
        body = response.read()
    root = ET.fromstring(body)
    err = root.find(".//error")
    if err is not None:
        safe = {k: v for k, v in err.attrib.items() if "pass" not in k.lower() and "auth" not in k.lower()}
        raise SystemExit(f"ISPmanager error func={params.get('func')}: {safe}")
    return root, body


def auth() -> str:
    root, _ = call({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    node = root.find(".//auth")
    sid = node.attrib.get("id", "") if node is not None else ""
    if not sid:
        raise SystemExit("ISPmanager authentication failed")
    return sid


if CONFIRM != "YES":
    raise SystemExit("Refusing mutation: set ROLLSBAR_CONFIRM_CREATE_STAGING=YES")
if not BASE.startswith("https://"):
    raise SystemExit("ISP_MANAGER_URL must use https://")

sid = auth()
_, before = call({"out": "xml", "func": "webdomain", "auth": sid})
if DOMAIN.encode() in before:
    print(f"staging_site=already_exists domain={DOMAIN}")
    print("mutation=skipped")
    raise SystemExit(0)

params = {
    "out": "xml",
    "func": "webdomain.edit",
    "auth": sid,
    "sok": "ok",
    "name": DOMAIN,
    "aliases": "",
    "home": HOME,
    "owner": USER,
    "ipaddrs": IP,
    "charset": "off",
    "dirindex": "index.php index.html",
    "php": "on",
    "php_mode": "php_mode_fcgi_apache",
    "log_access": "on",
    "log_error": "on",
    "secure": "off",
    "comment": "RollsBar isolated staging",
}
call(params)
_, after = call({"out": "xml", "func": "webdomain", "auth": sid})
if DOMAIN.encode() not in after:
    raise SystemExit("Create request returned without error but staging domain is not in webdomain list")
print(f"staging_site=created domain={DOMAIN}")
print(f"docroot_relative={HOME}")
print(f"ip={IP}")
print("ssl=deferred_until_dns_check")
print("CREATE STAGING SITE PASS")

#!/usr/bin/env python3
"""Enable trusted Let's Encrypt TLS for the isolated RollsBar staging site.

Narrow, idempotent mutation: only staging.rollsbar.ru is touched. DNS is checked
first. ISPmanager's explicit `letsencrypt.generate` function is used; a temporary
self-signed placeholder does not count as success. After public HTTPS verifies,
WordPress home/siteurl are switched to HTTPS over SSH. No credentials are printed.
"""
from __future__ import annotations

import os
import shlex
import socket
import ssl
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip().rstrip("/")
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_ENABLE_STAGING_SSL", "")
DOMAIN = "staging.rollsbar.ru"
EMAIL = "webmaster@staging.rollsbar.ru"
EXPECTED_IP = "37.140.192.67"
ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"
CTX = ssl.create_default_context()


def api(params: dict[str, str]) -> ET.Element:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-enable-staging-ssl/1.1"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as response:
        body = response.read()
    root = ET.fromstring(body)
    err = root.find(".//error")
    if err is not None:
        safe = {k: v for k, v in err.attrib.items() if not any(x in k.lower() for x in ("pass", "auth", "secret", "token"))}
        raise RuntimeError(f"ISPmanager error func={params.get('func')}: {safe}")
    return root


def auth() -> str:
    root = api({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    node = root.find(".//auth")
    sid = node.attrib.get("id", "") if node is not None else ""
    if not sid:
        raise RuntimeError("ISPmanager authentication failed")
    return sid


def scalar_values(root: ET.Element) -> dict[str, str]:
    data: dict[str, str] = {}
    for elem in root.iter():
        for child in list(elem):
            if len(list(child)) == 0 and child.text and child.tag not in data:
                data[child.tag] = child.text.strip()
    return data


def list_rows(root: ET.Element) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for elem in root.findall(".//elem"):
        row = {child.tag: (child.text or "").strip() for child in list(elem) if len(list(child)) == 0}
        if row:
            rows.append(row)
    return rows


def trusted_cert(sid: str) -> dict[str, str] | None:
    root = api({"out": "xml", "func": "sslcert", "auth": sid})
    candidates = [row for row in list_rows(root) if DOMAIN in row.get("name", "") or DOMAIN in row.get("key", "")]
    for row in reversed(candidates):
        cert_type = row.get("type", "").lower()
        if cert_type and cert_type != "ssl_selfsigned":
            return row
    return None


def wait_trusted_cert(sid: str, timeout: int = 180) -> dict[str, str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        row = trusted_cert(sid)
        if row:
            return row
        time.sleep(5)
    raise RuntimeError("ISPmanager did not expose a non-self-signed certificate in time")


def wait_https(timeout: int = 90) -> int:
    deadline = time.time() + timeout
    last = "unavailable"
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"https://{DOMAIN}/", method="HEAD", headers={"User-Agent": "rollsbar-ssl-verify/1.1"})
            with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=12) as response:
                return response.status
        except Exception as exc:
            last = exc.__class__.__name__
            time.sleep(5)
    raise RuntimeError(f"Trusted HTTPS did not become available in time; last={last}")


def attach_cert_if_needed(sid: str, cert_name: str) -> None:
    root = api({"out": "xml", "func": "webdomain.edit", "auth": sid, "elid": DOMAIN})
    current = scalar_values(root)
    if current.get("name") != DOMAIN:
        raise RuntimeError("ISPmanager edit form did not resolve expected staging domain")
    if current.get("secure") == "on" and current.get("ssl_cert") == cert_name:
        print("certificate_attachment=already_correct")
        return
    api({
        "out": "xml",
        "func": "webdomain.edit",
        "auth": sid,
        "sok": "ok",
        "elid": DOMAIN,
        "name": DOMAIN,
        "aliases": current.get("aliases", ""),
        "home": current.get("home") or "www/staging.rollsbar.ru",
        "owner": USER,
        "ipaddrs": EXPECTED_IP,
        "email": current.get("email") or EMAIL,
        "charset": current.get("charset") or "off",
        "dirindex": current.get("dirindex") or "index.php index.html",
        "php": "on",
        "php_mode": current.get("php_mode") or "php_mode_fcgi_apache",
        "log_access": current.get("log_access") or "on",
        "log_error": current.get("log_error") or "on",
        "secure": "on",
        "ssl_cert": cert_name,
        "comment": current.get("comment") or "RollsBar isolated staging",
    })
    print("certificate_attachment=updated")


def update_wordpress_https() -> None:
    host = urlsplit(BASE).hostname or ""
    if not host:
        raise RuntimeError("Could not derive hosting hostname")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=22,
            username=USER,
            password=PASSWORD,
            timeout=15,
            auth_timeout=15,
            banner_timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )
        command = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="$HOME/www/{DOMAIN}"
wp --path="$WP_PATH" option update home "https://{DOMAIN}" >/dev/null
wp --path="$WP_PATH" option update siteurl "https://{DOMAIN}" >/dev/null
wp --path="$WP_PATH" config set FORCE_SSL_ADMIN true --raw >/dev/null
home="$(wp --path="$WP_PATH" option get home)"
siteurl="$(wp --path="$WP_PATH" option get siteurl)"
[[ "$home" == "https://{DOMAIN}" ]]
[[ "$siteurl" == "https://{DOMAIN}" ]]
echo "wordpress_https_urls=pass"
'''
        _, stdout, stderr = client.exec_command("bash -lc " + shlex.quote(command), timeout=60)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        status = stdout.channel.recv_exit_status()
        if out:
            print(out.strip())
        if status != 0:
            safe_err = [line for line in err.splitlines() if "pass" not in line.lower() and "secret" not in line.lower()]
            raise RuntimeError("WordPress HTTPS switch failed: " + " | ".join(safe_err[-6:])[:600])
    finally:
        client.close()


if CONFIRM != "YES":
    raise SystemExit("Refusing mutation: set ROLLSBAR_CONFIRM_ENABLE_STAGING_SSL=YES")
if not BASE.startswith("https://"):
    raise SystemExit("ISP_MANAGER_URL must use https://")

resolved = {item[4][0] for item in socket.getaddrinfo(DOMAIN, 443, type=socket.SOCK_STREAM) if item[0] == socket.AF_INET}
if EXPECTED_IP not in resolved:
    raise SystemExit(f"DNS safety gate failed: {DOMAIN} does not resolve to expected IPv4")
print("dns_gate=pass")

sid = auth()
cert = trusted_cert(sid)
if cert:
    print("letsencrypt_state=trusted_certificate_already_present")
else:
    # ISPmanager documentation: letsencrypt.generate with sok=ok creates the certificate;
    # these are the exact defaults returned by this panel's read-only form.
    api({
        "out": "xml",
        "func": "letsencrypt.generate",
        "auth": sid,
        "sok": "ok",
        "domain_name": DOMAIN,
        "domain": DOMAIN,
        "email": EMAIL,
        "keylen": "2048",
        "enable_cert": "on",
        "wildcard": "off",
        "dns_check": "off",
    })
    print("letsencrypt_generate=submitted")
    cert = wait_trusted_cert(sid)

cert_name = cert.get("name") or cert.get("key") or ""
if not cert_name:
    raise RuntimeError("Trusted certificate exists but its ISPmanager name is unavailable")
print(f"trusted_certificate={cert_name}")
attach_cert_if_needed(sid, cert_name)

status = wait_https()
print(f"https_pre_wp_status={status}")
update_wordpress_https()
status2 = wait_https(timeout=45)
print(f"https_final_status={status2}")
print("ENABLE STAGING SSL PASS")

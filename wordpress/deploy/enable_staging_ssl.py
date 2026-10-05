#!/usr/bin/env python3
"""Enable Let's Encrypt TLS for the isolated RollsBar staging site.

Narrow, idempotent mutation: only staging.rollsbar.ru is edited. DNS is checked
first. After ISPmanager provisions the certificate, WordPress home/siteurl are
switched to HTTPS over SSH. No credentials are printed.
"""
from __future__ import annotations

import os
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
EXPECTED_IP = "37.140.192.67"
ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"
CTX = ssl.create_default_context()


def api(params: dict[str, str]) -> ET.Element:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-enable-staging-ssl/1.0"})
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


def values(root: ET.Element) -> dict[str, str]:
    data: dict[str, str] = {}
    for child in root:
        if len(list(child)) == 0 and child.text:
            data[child.tag] = child.text.strip()
    # Edit forms often wrap scalar fields one level deeper.
    for elem in root.iter():
        for child in list(elem):
            if len(list(child)) == 0 and child.text and child.tag not in data:
                data[child.tag] = child.text.strip()
    return data


def wait_https(timeout: int = 150) -> int:
    deadline = time.time() + timeout
    last = "unavailable"
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"https://{DOMAIN}/", method="HEAD", headers={"User-Agent": "rollsbar-ssl-verify/1.0"})
            with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=12) as response:
                return response.status
        except Exception as exc:  # expected while certificate/vhost reload is pending
            last = exc.__class__.__name__
            time.sleep(5)
    raise RuntimeError(f"HTTPS did not become available in time; last={last}")


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
        _, stdout, stderr = client.exec_command("bash -lc " + repr(command), timeout=60)
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
current_root = api({"out": "xml", "func": "webdomain.edit", "auth": sid, "elid": DOMAIN})
current = values(current_root)
if current.get("name") != DOMAIN:
    raise RuntimeError("ISPmanager edit form did not resolve the expected staging domain")

if current.get("secure") == "on" and current.get("ssl_cert") not in {"", "ssl_not_used", "selfsigned"}:
    print("ssl_state=already_enabled")
else:
    params = {
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
        "email": current.get("email") or "webmaster@staging.rollsbar.ru",
        "charset": current.get("charset") or "off",
        "dirindex": current.get("dirindex") or "index.php index.html",
        "php": "on",
        "php_mode": current.get("php_mode") or "php_mode_fcgi_apache",
        "log_access": current.get("log_access") or "on",
        "log_error": current.get("log_error") or "on",
        "secure": "on",
        "ssl_cert": "letsencrypt",
        "comment": current.get("comment") or "RollsBar isolated staging",
    }
    api(params)
    print("ssl_request=submitted letsencrypt")

status = wait_https()
print(f"https_pre_wp_status={status}")
update_wordpress_https()
status2 = wait_https(timeout=45)
print(f"https_final_status={status2}")
print("ENABLE STAGING SSL PASS")

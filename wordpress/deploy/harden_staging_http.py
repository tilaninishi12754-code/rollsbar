#!/usr/bin/env python3
"""Apply minimal reversible HTTP hardening to RollsBar staging .htaccess.

Changes only the staging .htaccess managed block. It preserves the WordPress
rewrite block, verifies public behavior after the write, and restores the exact
previous bytes if the redirect check fails.
"""
from __future__ import annotations

import os
import re
import shlex
import socket
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_HTTP_HARDENING", "")
DOMAIN = "staging.rollsbar.ru"
HTACCESS = f"www/{DOMAIN}/.htaccess"
START = "# BEGIN RollsBar HTTP Security"
END = "# END RollsBar HTTP Security"
BLOCK = f'''{START}
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteCond %{{HTTPS}} !=on
RewriteCond %{{HTTP:X-Forwarded-Proto}} !https [NC]
RewriteRule ^ https://%{{HTTP_HOST}}%{{REQUEST_URI}} [R=301,L,NE]
</IfModule>
<IfModule mod_headers.c>
Header always set X-Content-Type-Options "nosniff"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set X-Frame-Options "SAMEORIGIN"
</IfModule>
{END}
'''


def connect() -> paramiko.SSHClient:
    host = urlsplit(BASE).hostname or ""
    if not host:
        raise RuntimeError("Could not derive hosting hostname")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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
    return client


def no_redirect_request(url: str):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(url, headers={"User-Agent": "RollsBar-Hardening-Verify/1.0"})
    try:
        resp = opener.open(req, timeout=20)
        return resp.getcode(), dict(resp.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items())


def get_header(headers: dict[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def verify_public() -> tuple[bool, str]:
    code, headers = no_redirect_request(f"http://{DOMAIN}/")
    location = get_header(headers, "Location")
    redirect_ok = code in {301, 302, 307, 308} and location.startswith(f"https://{DOMAIN}")

    req = urllib.request.Request(f"https://{DOMAIN}/", headers={"User-Agent": "RollsBar-Hardening-Verify/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        https_code = resp.getcode()
        https_headers = dict(resp.headers.items())
        resp.read(1024)

    xcto = get_header(https_headers, "X-Content-Type-Options")
    referrer = get_header(https_headers, "Referrer-Policy")
    xfo = get_header(https_headers, "X-Frame-Options")
    headers_ok = xcto.lower() == "nosniff" and bool(referrer) and bool(xfo)
    detail = (
        f"http={code} location={location or 'none'} https={https_code} "
        f"xcto={xcto or 'none'} referrer={referrer or 'none'} xfo={xfo or 'none'}"
    )
    return redirect_ok and https_code == 200 and headers_ok, detail


def main() -> int:
    if CONFIRM != "YES":
        print("Refusing mutation: set ROLLSBAR_CONFIRM_HTTP_HARDENING=YES")
        return 2

    client = connect()
    sftp = client.open_sftp()
    original: bytes
    try:
        try:
            with sftp.open(HTACCESS, "rb") as fh:
                original = fh.read()
        except FileNotFoundError:
            raise RuntimeError("staging .htaccess does not exist")

        text = original.decode("utf-8")
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
        if pattern.search(text):
            new_text = pattern.sub(BLOCK, text, count=1)
        else:
            marker = "# BEGIN WordPress"
            if marker in text:
                new_text = text.replace(marker, BLOCK + "\n" + marker, 1)
            else:
                new_text = BLOCK + "\n" + text

        if new_text.encode("utf-8") == original:
            print("http_hardening=already_current")
        else:
            tmp = HTACCESS + ".rollsbar-new"
            with sftp.open(tmp, "wb") as fh:
                fh.write(new_text.encode("utf-8"))
            sftp.chmod(tmp, 0o644)
            sftp.rename(tmp, HTACCESS)
            print("http_hardening=written")
    finally:
        sftp.close()
        client.close()

    # Give Apache a moment to observe the atomic replacement.
    time.sleep(1)
    ok, detail = verify_public()
    print("verify=" + detail)
    if ok:
        print("STAGING HTTP HARDENING PASS")
        return 0

    # Roll back exact prior bytes if verification fails.
    client = connect()
    sftp = client.open_sftp()
    try:
        tmp = HTACCESS + ".rollsbar-rollback"
        with sftp.open(tmp, "wb") as fh:
            fh.write(original)
        sftp.chmod(tmp, 0o644)
        sftp.rename(tmp, HTACCESS)
    finally:
        sftp.close()
        client.close()
    print("STAGING HTTP HARDENING FAILED — exact previous .htaccess restored")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError) as exc:
        message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
        print(f"http_hardening=failed type={exc.__class__.__name__} detail={message}")
        sys.exit(1)

#!/usr/bin/env python3
"""Read-only final acceptance audit for the real RollsBar staging environment.

This script intentionally does not change WordPress, the database, plugins, themes,
or server configuration. It combines public HTTP/TLS checks with WP-CLI read-only
checks over SSH. Missing hardening headers are reported as WARN instead of being
blindly enabled because an aggressive CSP can break WooCommerce checkout.
"""
from __future__ import annotations

import base64
import json
import os
import shlex
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
DOMAIN = "staging.rollsbar.ru"
BASE_HTTPS = f"https://{DOMAIN}"
WP_PATH = f"$HOME/www/{DOMAIN}"
UA = "RollsBar-Final-Acceptance/1.0"


@dataclass
class Finding:
    level: str
    name: str
    detail: str


findings: list[Finding] = []


def record(level: str, name: str, detail: str) -> None:
    findings.append(Finding(level, name, detail))
    print(f"{level:<4} {name}: {detail}")


def request(url: str, *, follow_redirects: bool = True, timeout: int = 20):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
            return None

    handlers: list[urllib.request.BaseHandler] = []
    if not follow_redirects:
        handlers.append(NoRedirect())
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        resp = opener.open(req, timeout=timeout)
        body = resp.read(512 * 1024)
        return resp.getcode(), dict(resp.headers.items()), body, resp.geturl()
    except urllib.error.HTTPError as exc:
        body = exc.read(512 * 1024)
        return exc.code, dict(exc.headers.items()), body, exc.geturl()


def header_ci(headers: dict[str, str], name: str) -> str:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value
    return ""


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


def remote(client: paramiko.SSHClient, command: str, timeout: int = 180) -> tuple[int, str, str]:
    _, stdout, stderr = client.exec_command("bash -lc " + shlex.quote(command), timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    return status, out.strip(), err.strip()


def hard_http_checks() -> None:
    # HTTP must redirect to HTTPS.
    code, headers, _, final_url = request(f"http://{DOMAIN}/", follow_redirects=False)
    location = header_ci(headers, "Location")
    if code in {301, 302, 307, 308} and location.startswith(BASE_HTTPS):
        record("PASS", "http_to_https", f"{code} -> {location}")
    else:
        record("FAIL", "http_to_https", f"status={code} location={location or 'none'} final={final_url}")

    # TLS certificate must verify and have useful lifetime left.
    context = ssl.create_default_context()
    with socket.create_connection((DOMAIN, 443), timeout=15) as raw:
        with context.wrap_socket(raw, server_hostname=DOMAIN) as tls:
            cert = tls.getpeercert()
            protocol = tls.version() or "unknown"
    not_after_raw = cert.get("notAfter")
    if not not_after_raw:
        record("FAIL", "tls_certificate", "certificate has no notAfter")
    else:
        expires = datetime.strptime(not_after_raw, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days = (expires - datetime.now(timezone.utc)).total_seconds() / 86400
        level = "PASS" if days >= 14 else "FAIL"
        record(level, "tls_certificate", f"verified protocol={protocol} expires={expires.isoformat()} days_left={days:.1f}")

    # Public routes that must work for launch-readiness.
    routes = [
        "/",
        "/cart/",
        "/checkout/",
        "/otzyvy/",
        "/pravovaya-informaciya/",
        "/publichnaya-oferta/",
        "/dostavka-i-oplata/",
        "/oplata-i-vozvrat/",
        "/politika-konfidencialnosti/",
        "/soglasie-na-obrabotku-personalnyh-dannyh/",
        "/cookies/",
    ]
    root_headers: dict[str, str] = {}
    for route in routes:
        code, headers, body, final_url = request(BASE_HTTPS + route)
        if route == "/":
            root_headers = headers
        if code == 200 and len(body) > 100:
            record("PASS", f"route {route}", f"HTTP 200 bytes={len(body)} final={final_url}")
        else:
            record("FAIL", f"route {route}", f"HTTP {code} bytes={len(body)} final={final_url}")

    # REST API must be reachable and return JSON.
    code, _, body, _ = request(BASE_HTTPS + "/wp-json/")
    rest_ok = False
    if code == 200:
        try:
            payload = json.loads(body.decode("utf-8", errors="replace"))
            rest_ok = isinstance(payload, dict) and bool(payload.get("namespaces"))
        except json.JSONDecodeError:
            rest_ok = False
    record("PASS" if rest_ok else "FAIL", "rest_api", f"HTTP {code} namespaces={'yes' if rest_ok else 'no'}")

    # Sensitive resources/directories must not be directly retrievable/listed.
    for path in ("/wp-config.php", "/.git/config", "/wp-content/plugins/", "/wp-content/themes/"):
        code, _, body, _ = request(BASE_HTTPS + path, follow_redirects=False)
        if code in {401, 403, 404} or (code == 200 and path.endswith("/") and b"Index of" not in body):
            # A blank 200 directory response is tolerated only when it is not a directory listing.
            record("PASS", f"protected {path}", f"HTTP {code} directory_listing=no")
        else:
            record("FAIL", f"protected {path}", f"HTTP {code} bytes={len(body)}")

    # Header inventory. These are defense-in-depth warnings, not automatic blockers.
    recommended = {
        "Strict-Transport-Security": "HSTS",
        "X-Content-Type-Options": "MIME sniffing protection",
        "Referrer-Policy": "referrer minimization",
        "Permissions-Policy": "browser feature policy",
    }
    for header_name, purpose in recommended.items():
        value = header_ci(root_headers, header_name)
        record("PASS" if value else "WARN", f"header {header_name}", value or f"missing ({purpose})")

    xfo = header_ci(root_headers, "X-Frame-Options")
    csp = header_ci(root_headers, "Content-Security-Policy")
    frame_protected = bool(xfo) or "frame-ancestors" in csp.lower()
    record(
        "PASS" if frame_protected else "WARN",
        "clickjacking_header",
        f"X-Frame-Options={xfo or 'none'} CSP_frame_ancestors={'yes' if 'frame-ancestors' in csp.lower() else 'no'}",
    )
    record("PASS" if csp else "WARN", "header Content-Security-Policy", csp or "missing; do not add blindly without checkout QA")

    # XML-RPC is not required by this project. Exposure is informational until an explicit decision.
    code, _, _, _ = request(BASE_HTTPS + "/xmlrpc.php", follow_redirects=False)
    if code in {403, 404}:
        record("PASS", "xmlrpc_surface", f"HTTP {code} disabled/unavailable")
    else:
        record("WARN", "xmlrpc_surface", f"HTTP {code}; endpoint exists, confirm whether any integration needs it")


def wordpress_checks(client: paramiko.SSHClient) -> None:
    status, out, err = remote(client, f'export PATH="$HOME/.local/bin:$PATH"; wp --path="{WP_PATH}" core is-installed')
    record("PASS" if status == 0 else "FAIL", "wordpress_installed", out or err or f"exit={status}")

    # Database consistency check is read-only.
    status, out, err = remote(client, f'export PATH="$HOME/.local/bin:$PATH"; wp --path="{WP_PATH}" db check')
    db_detail = (out or err or f"exit={status}").splitlines()[-1][:300]
    record("PASS" if status == 0 else "FAIL", "database_check", db_detail)

    # WP-Cron spawning/loopback transport.
    status, out, err = remote(client, f'export PATH="$HOME/.local/bin:$PATH"; wp --path="{WP_PATH}" cron test')
    cron_detail = (out or err or f"exit={status}").replace("\n", " | ")[-600:]
    record("PASS" if status == 0 else "FAIL", "wp_cron_spawn", cron_detail)

    # Current due cron count is informational; a non-zero count can be normal during traffic gaps.
    status, out, err = remote(
        client,
        f'export PATH="$HOME/.local/bin:$PATH"; wp --path="{WP_PATH}" cron event list --due-now --format=count',
    )
    record("PASS" if status == 0 else "WARN", "cron_due_now", out or err or f"exit={status}")

    # WordPress Site Health tests that directly cover infrastructure readiness.
    php = r'''
require_once ABSPATH . 'wp-admin/includes/class-wp-site-health.php';
$h = WP_Site_Health::get_instance();
$methods = array(
  'get_test_https_status',
  'get_test_ssl_support',
  'get_test_rest_availability',
  'get_test_loopback_requests',
  'get_test_scheduled_events',
  'get_test_dotorg_communication',
  'get_test_background_updates',
  'get_test_php_default_timezone',
  'get_test_file_uploads'
);
$out = array();
foreach ($methods as $method) {
  if (!method_exists($h, $method)) {
    $out[$method] = array('status' => 'skip', 'label' => 'method unavailable');
    continue;
  }
  try {
    $r = $h->$method();
    $out[$method] = array(
      'status' => isset($r['status']) ? (string) $r['status'] : 'unknown',
      'label' => isset($r['label']) ? wp_strip_all_tags((string) $r['label']) : ''
    );
  } catch (Throwable $e) {
    $out[$method] = array('status' => 'error', 'label' => get_class($e) . ': ' . $e->getMessage());
  }
}
echo wp_json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
'''.strip()
    encoded = base64.b64encode(php.encode("utf-8")).decode("ascii")
    cmd = (
        f'export PATH="$HOME/.local/bin:$PATH"; '
        f'CODE="$(printf %s {shlex.quote(encoded)} | base64 -d)"; '
        f'wp --path="{WP_PATH}" eval "$CODE"'
    )
    status, out, err = remote(client, cmd, timeout=240)
    if status != 0:
        record("FAIL", "site_health", (err or out or f"exit={status}")[-1000:])
    else:
        try:
            health = json.loads(out)
        except json.JSONDecodeError:
            record("FAIL", "site_health", f"invalid JSON: {out[-1000:]}")
            health = {}
        for method, result in health.items():
            state = str(result.get("status", "unknown"))
            label = str(result.get("label", ""))[:500]
            if state == "good":
                level = "PASS"
            elif state in {"recommended", "skip"}:
                level = "WARN"
            else:
                level = "FAIL"
            record(level, f"site_health {method}", f"status={state} {label}")

    # Confirm launch invariants again without mutating anything.
    invariant_php = r'''
$products = wp_count_posts('product');
$out = array(
  'home' => home_url('/'),
  'siteurl' => site_url('/'),
  'blog_public' => (string) get_option('blog_public'),
  'products_publish' => isset($products->publish) ? (int) $products->publish : 0,
  'woo_version' => defined('WC_VERSION') ? WC_VERSION : '',
  'theme' => wp_get_theme()->get_stylesheet(),
  'dadata' => defined('ROLLSBAR_DADATA_API_KEY') && strlen((string) ROLLSBAR_DADATA_API_KEY) >= 10 ? 'yes' : 'no'
);
echo wp_json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
'''.strip()
    encoded = base64.b64encode(invariant_php.encode("utf-8")).decode("ascii")
    cmd = (
        f'export PATH="$HOME/.local/bin:$PATH"; '
        f'CODE="$(printf %s {shlex.quote(encoded)} | base64 -d)"; '
        f'wp --path="{WP_PATH}" eval "$CODE"'
    )
    status, out, err = remote(client, cmd)
    if status != 0:
        record("FAIL", "launch_invariants", err or out or f"exit={status}")
    else:
        try:
            inv = json.loads(out)
            checks = [
                (inv.get("blog_public") == "0", "blog_public=0"),
                (int(inv.get("products_publish", -1)) == 118, f"products={inv.get('products_publish')}"),
                (inv.get("woo_version") == "11.1.2", f"WooCommerce={inv.get('woo_version')}"),
                (inv.get("theme") == "rollsbar-theme", f"theme={inv.get('theme')}"),
                (inv.get("dadata") == "yes", f"DaData={inv.get('dadata')}"),
            ]
            for ok, detail in checks:
                record("PASS" if ok else "FAIL", "launch_invariant", detail)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            record("FAIL", "launch_invariants", f"parse_error={exc} raw={out[-800:]}")

    # Staging debug log: report recent fatal/parse/uncaught signals without deleting/truncating it.
    debug_cmd = f'''
LOG="{WP_PATH}/wp-content/debug.log"
if [[ ! -f "$LOG" ]]; then
  echo "debug_log=absent"
  exit 0
fi
now=$(date +%s)
mtime=$(stat -c %Y "$LOG")
age=$((now-mtime))
echo "debug_log_age_seconds=$age"
if [[ "$age" -le 3600 ]]; then
  count=$(tail -n 400 "$LOG" | grep -Eic 'PHP (Fatal error|Parse error)|Uncaught (Error|Exception)|Allowed memory size.*exhausted' || true)
  echo "recent_tail_fatal_signals=$count"
  if [[ "$count" -gt 0 ]]; then
    tail -n 400 "$LOG" | grep -Ei 'PHP (Fatal error|Parse error)|Uncaught (Error|Exception)|Allowed memory size.*exhausted' | tail -n 5 | sed -E 's#(/var/www/)[^/]+/#\1***/#g'
  fi
else
  echo "recent_tail_fatal_signals=0"
fi
'''
    status, out, err = remote(client, debug_cmd)
    if status != 0:
        record("WARN", "debug_log", err or out or f"exit={status}")
    else:
        fatal_count = 0
        for line in out.splitlines():
            if line.startswith("recent_tail_fatal_signals="):
                try:
                    fatal_count = int(line.split("=", 1)[1])
                except ValueError:
                    fatal_count = -1
        level = "PASS" if fatal_count == 0 else "WARN"
        record(level, "debug_log", out.replace("\n", " | ")[-1800:])


def summarize() -> int:
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for f in findings:
        counts[f.level] = counts.get(f.level, 0) + 1
    print("\nFINAL ACCEPTANCE SUMMARY")
    print(f"pass={counts.get('PASS', 0)} warn={counts.get('WARN', 0)} fail={counts.get('FAIL', 0)}")
    if counts.get("FAIL", 0):
        print("FINAL STAGING ACCEPTANCE: FAIL")
        return 1
    print("FINAL STAGING ACCEPTANCE: PASS WITH WARNINGS" if counts.get("WARN", 0) else "FINAL STAGING ACCEPTANCE: PASS")
    return 0


def main() -> int:
    print(f"FINAL STAGING ACCEPTANCE AUDIT target={DOMAIN}")
    try:
        hard_http_checks()
    except Exception as exc:  # keep collecting server-side evidence when possible
        record("FAIL", "public_http_audit", f"{exc.__class__.__name__}: {exc}")

    client = None
    try:
        client = connect()
        wordpress_checks(client)
    except Exception as exc:
        message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
        record("FAIL", "ssh_wordpress_audit", f"{exc.__class__.__name__}: {message}")
    finally:
        if client is not None:
            client.close()

    return summarize()


if __name__ == "__main__":
    sys.exit(main())

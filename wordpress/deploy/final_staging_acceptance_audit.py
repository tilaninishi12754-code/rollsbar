#!/usr/bin/env python3
"""Read-only final acceptance audit for real RollsBar staging."""
from __future__ import annotations

import base64
import json
import os
import shlex
import socket
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
DOMAIN = "staging.rollsbar.ru"
BASE_HTTPS = f"https://{DOMAIN}"
WP_PATH = f"$HOME/www/{DOMAIN}"
UA = "RollsBar-Final-Acceptance/1.2"


@dataclass
class Finding:
    level: str
    name: str
    detail: str


findings: list[Finding] = []


def record(level: str, name: str, detail: str) -> None:
    findings.append(Finding(level, name, detail))
    print(f"{level:<4} {name}: {detail}")


def request(url: str, *, follow_redirects: bool = True, timeout: int = 20, max_bytes: int = 512 * 1024):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    handlers: list[urllib.request.BaseHandler] = []
    if not follow_redirects:
        handlers.append(NoRedirect())
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        resp = opener.open(req, timeout=timeout)
        return resp.getcode(), dict(resp.headers.items()), resp.read(max_bytes), resp.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read(max_bytes), exc.geturl()


def header_ci(headers: dict[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
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


def public_checks() -> None:
    code, headers, _, final_url = request(f"http://{DOMAIN}/", follow_redirects=False)
    location = header_ci(headers, "Location")
    record(
        "PASS" if code in {301, 302, 307, 308} and location.startswith(BASE_HTTPS) else "FAIL",
        "http_to_https",
        f"status={code} location={location or 'none'} final={final_url}",
    )

    context = ssl.create_default_context()
    with socket.create_connection((DOMAIN, 443), timeout=15) as raw:
        with context.wrap_socket(raw, server_hostname=DOMAIN) as tls:
            cert = tls.getpeercert()
            protocol = tls.version() or "unknown"
    expiry = cert.get("notAfter")
    if expiry:
        dt = datetime.strptime(expiry, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days = (dt - datetime.now(timezone.utc)).total_seconds() / 86400
        record("PASS" if days >= 14 else "FAIL", "tls_certificate", f"protocol={protocol} expires={dt.isoformat()} days_left={days:.1f}")
    else:
        record("FAIL", "tls_certificate", "missing notAfter")

    routes = [
        "/", "/cart/", "/checkout/", "/otzyvy/", "/pravovaya-informaciya/",
        "/publichnaya-oferta/", "/dostavka-i-oplata/", "/oplata-i-vozvrat/",
        "/politika-konfidencialnosti/", "/soglasie-na-obrabotku-personalnyh-dannyh/", "/cookies/",
    ]
    root_headers: dict[str, str] = {}
    for route in routes:
        code, headers, body, final_url = request(BASE_HTTPS + route)
        if route == "/":
            root_headers = headers
        ok = code == 200 and len(body) > 100
        record("PASS" if ok else "FAIL", f"route {route}", f"HTTP {code} bytes={len(body)} final={final_url}")

    # Use a bounded public REST endpoint rather than the very large REST index.
    # The root index is >512 KiB on this WooCommerce install and truncating it
    # before json.loads created a false negative in the first acceptance run.
    rest_path = "/wp-json/wp/v2/types"
    code, rest_headers, body, final_url = request(BASE_HTTPS + rest_path, max_bytes=2 * 1024 * 1024)
    rest_ok = False
    payload = None
    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
        rest_ok = code == 200 and isinstance(payload, dict) and "post" in payload and "page" in payload
    except json.JSONDecodeError:
        pass
    if rest_ok:
        record("PASS", "rest_api", f"HTTP {code} endpoint={rest_path} types={len(payload)}")
    else:
        snippet = body[:350].decode("utf-8", errors="replace").replace("\n", " ").replace("\r", " ")
        record(
            "FAIL",
            "rest_api",
            f"HTTP {code} endpoint={rest_path} final={final_url} content_type={header_ci(rest_headers, 'Content-Type') or 'none'} body_prefix={snippet!r}",
        )

    for path in ("/wp-config.php", "/.git/config", "/wp-content/plugins/", "/wp-content/themes/"):
        code, _, body, _ = request(BASE_HTTPS + path, follow_redirects=False)
        ok = code in {401, 403, 404} or (code == 200 and path.endswith("/") and b"Index of" not in body)
        record("PASS" if ok else "FAIL", f"protected {path}", f"HTTP {code} directory_listing={'no' if ok else 'possible'}")

    for name, purpose in {
        "Strict-Transport-Security": "HSTS",
        "X-Content-Type-Options": "MIME sniffing protection",
        "Referrer-Policy": "referrer minimization",
        "Permissions-Policy": "browser feature policy",
    }.items():
        value = header_ci(root_headers, name)
        record("PASS" if value else "WARN", f"header {name}", value or f"missing ({purpose})")

    xfo = header_ci(root_headers, "X-Frame-Options")
    csp = header_ci(root_headers, "Content-Security-Policy")
    frame_ok = bool(xfo) or "frame-ancestors" in csp.lower()
    record("PASS" if frame_ok else "WARN", "clickjacking_header", f"X-Frame-Options={xfo or 'none'} CSP_frame_ancestors={'yes' if 'frame-ancestors' in csp.lower() else 'no'}")
    record("PASS" if csp else "WARN", "header Content-Security-Policy", csp or "missing; do not add blindly without checkout QA")

    try:
        code, _, _, _ = request(BASE_HTTPS + "/xmlrpc.php", follow_redirects=False)
        record("PASS" if code in {403, 404} else "WARN", "xmlrpc_surface", f"HTTP {code}")
    except Exception as exc:
        record("WARN", "xmlrpc_surface", f"connection closed/reset: {exc.__class__.__name__}")


def run_wp_eval(client: paramiko.SSHClient, php: str, timeout: int = 240) -> tuple[int, str, str]:
    encoded = base64.b64encode(php.strip().encode("utf-8")).decode("ascii")
    cmd = (
        f'export PATH="$HOME/.local/bin:$PATH"; '
        f'CODE="$(printf %s {shlex.quote(encoded)} | base64 -d)"; '
        f'wp --path="{WP_PATH}" eval "$CODE"'
    )
    return remote(client, cmd, timeout=timeout)


def wordpress_checks(client: paramiko.SSHClient) -> None:
    base_env = 'export PATH="$HOME/.local/bin:$PATH"; '

    status, out, err = remote(client, base_env + f'wp --path="{WP_PATH}" core is-installed')
    record("PASS" if status == 0 else "FAIL", "wordpress_installed", out or err or f"exit={status}")

    status, out, err = remote(client, base_env + f'wp --path="{WP_PATH}" db check')
    record("PASS" if status == 0 else "FAIL", "database_check", (out or err or f"exit={status}").splitlines()[-1][:400])

    status, out, err = remote(client, base_env + f'wp --path="{WP_PATH}" cron test')
    record("PASS" if status == 0 else "FAIL", "wp_cron_spawn", (out or err or f"exit={status}").replace("\n", " | ")[-700:])

    status, out, err = remote(client, base_env + f'wp --path="{WP_PATH}" cron event list --due-now --format=count')
    record("PASS" if status == 0 else "WARN", "cron_due_now", out or err or f"exit={status}")

    health_php = r'''
require_once ABSPATH . 'wp-admin/includes/class-wp-site-health.php';
$h = WP_Site_Health::get_instance();
$methods = array('get_test_https_status','get_test_ssl_support','get_test_rest_availability','get_test_loopback_requests','get_test_scheduled_events','get_test_dotorg_communication','get_test_background_updates','get_test_php_default_timezone','get_test_file_uploads');
$out = array();
foreach ($methods as $method) {
  if (!method_exists($h, $method)) { $out[$method] = array('status'=>'skip','label'=>'method unavailable','description'=>''); continue; }
  try {
    $r = $h->$method();
    $out[$method] = array(
      'status'=>(string)($r['status'] ?? 'unknown'),
      'label'=>wp_strip_all_tags((string)($r['label'] ?? '')),
      'description'=>preg_replace('/\s+/', ' ', wp_strip_all_tags((string)($r['description'] ?? '')))
    );
  } catch (Throwable $e) { $out[$method] = array('status'=>'error','label'=>get_class($e).': '.$e->getMessage(),'description'=>''); }
}
echo wp_json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
'''
    status, out, err = run_wp_eval(client, health_php)
    if status != 0:
        record("FAIL", "site_health", (err or out or f"exit={status}")[-1000:])
    else:
        try:
            health = json.loads(out)
        except json.JSONDecodeError:
            health = {}
            record("FAIL", "site_health", f"invalid JSON: {out[-1000:]}")
        for method, result in health.items():
            state = str(result.get("status", "unknown"))
            level = "PASS" if state == "good" else ("WARN" if state in {"recommended", "skip"} else "FAIL")
            label = str(result.get("label", ""))[:500]
            description = str(result.get("description", ""))[:900]
            detail = f"status={state} {label}"
            if description:
                detail += f" | {description}"
            record(level, f"site_health {method}", detail)

    rest_internal_php = r'''
$server = rest_get_server();
$routes = $server->get_routes();
$r = new WP_REST_Request('GET', '/');
$response = rest_do_request($r);
$data = $response->get_data();
echo wp_json_encode(array(
  'registered_routes'=>count($routes),
  'status'=>$response->get_status(),
  'has_namespaces'=>is_array($data) && !empty($data['namespaces']),
  'rest_url'=>rest_url(),
  'permalink_structure'=>(string)get_option('permalink_structure')
), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
'''
    status, out, err = run_wp_eval(client, rest_internal_php)
    record("PASS" if status == 0 else "FAIL", "rest_internal", out or err or f"exit={status}")

    invariant_php = r'''
$products = wp_count_posts('product');
echo wp_json_encode(array(
 'blog_public'=>(string)get_option('blog_public'),
 'products_publish'=>isset($products->publish)?(int)$products->publish:0,
 'woo_version'=>defined('WC_VERSION')?WC_VERSION:'',
 'theme'=>wp_get_theme()->get_stylesheet(),
 'dadata'=>defined('ROLLSBAR_DADATA_API_KEY') && strlen((string)ROLLSBAR_DADATA_API_KEY)>=10?'yes':'no'
), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
'''
    status, out, err = run_wp_eval(client, invariant_php)
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
        except Exception as exc:
            record("FAIL", "launch_invariants", f"parse_error={exc} raw={out[-800:]}")

    htaccess_cmd = f'''
HT="{WP_PATH}/.htaccess"
if [[ -f "$HT" ]]; then
  echo "htaccess_present=yes"
  grep -nE 'RewriteEngine|RewriteCond|RewriteRule|Header (always )?(set|append)' "$HT" || true
else
  echo "htaccess_present=no"
fi
'''
    status, out, err = remote(client, htaccess_cmd)
    record("PASS" if status == 0 else "WARN", "htaccess_rewrite_summary", (out or err or f"exit={status}").replace("\n", " | ")[-1800:])

    debug_cmd = f'''
LOG="{WP_PATH}/wp-content/debug.log"
if [[ ! -f "$LOG" ]]; then echo "debug_log=absent"; exit 0; fi
now=$(date +%s); mtime=$(stat -c %Y "$LOG"); age=$((now-mtime)); echo "debug_log_age_seconds=$age"
if [[ "$age" -le 3600 ]]; then
  count=$(tail -n 400 "$LOG" | grep -Eic 'PHP (Fatal error|Parse error)|Uncaught (Error|Exception)|Allowed memory size.*exhausted' || true)
  echo "recent_tail_fatal_signals=$count"
else
  echo "recent_tail_fatal_signals=0"
fi
'''
    status, out, err = remote(client, debug_cmd)
    fatal = -1
    for line in out.splitlines():
        if line.startswith("recent_tail_fatal_signals="):
            try:
                fatal = int(line.split("=", 1)[1])
            except ValueError:
                fatal = -1
    record("PASS" if status == 0 and fatal == 0 else "WARN", "debug_log", (out or err or f"exit={status}").replace("\n", " | ")[-1200:])


def summarize() -> int:
    counts = {key: sum(1 for f in findings if f.level == key) for key in ("PASS", "WARN", "FAIL")}
    print("\nFINAL ACCEPTANCE SUMMARY")
    print(f"pass={counts['PASS']} warn={counts['WARN']} fail={counts['FAIL']}")
    if counts["FAIL"]:
        print("FINAL STAGING ACCEPTANCE: FAIL")
        return 1
    print("FINAL STAGING ACCEPTANCE: PASS WITH WARNINGS" if counts["WARN"] else "FINAL STAGING ACCEPTANCE: PASS")
    return 0


def main() -> int:
    print(f"FINAL STAGING ACCEPTANCE AUDIT target={DOMAIN}")
    try:
        public_checks()
    except Exception as exc:
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

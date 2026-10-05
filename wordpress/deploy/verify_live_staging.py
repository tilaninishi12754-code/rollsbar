#!/usr/bin/env python3
"""Run server-side Gate B checks against the real REG.RU staging install."""
from __future__ import annotations

import os
import shlex
import socket
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
VERIFY_SHA = os.environ["ROLLSBAR_VERIFY_SHA"].strip()
DOMAIN = "staging.rollsbar.ru"
REPO = "https://github.com/tilaninishi12754-code/rollsbar.git"


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


def run(client: paramiko.SSHClient, command: str) -> None:
    _, stdout, stderr = client.exec_command("bash -lc " + shlex.quote(command), timeout=240)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    if out:
        print(out, end="" if out.endswith("\n") else "\n")
    if status != 0:
        safe = [line for line in err.splitlines() if "pass" not in line.lower() and "secret" not in line.lower()]
        if safe:
            print("remote_stderr=" + " | ".join(safe[-10:])[:1400])
        raise RuntimeError(f"Gate B server verification failed with exit status {status}")


if len(VERIFY_SHA) < 7:
    raise SystemExit("ROLLSBAR_VERIFY_SHA is missing")

client = None
try:
    client = connect()
    command = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="$HOME/www/{DOMAIN}"
PROJECT_ROOT="$HOME/.rollsbar-deploy"
STAGING_URL="https://{DOMAIN}"
if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
  git clone --filter=blob:none --no-checkout {shlex.quote(REPO)} "$PROJECT_ROOT"
fi
git -C "$PROJECT_ROOT" fetch --depth=1 origin {shlex.quote(VERIFY_SHA)}
git -C "$PROJECT_ROOT" checkout --detach --force {shlex.quote(VERIFY_SHA)}
export WP_PATH STAGING_URL
bash "$PROJECT_ROOT/wordpress/deploy/verify-staging.sh"

# Additional live business/runtime assertions.
wp --path="$WP_PATH" eval '
$rows = RollsBar_Delivery_Rules::all();
if (count($rows) !== 7) {{ fwrite(STDERR, "delivery tier count mismatch\\n"); exit(1); }}
if ((int) $rows[0]["min_order"] !== 1200 || (int) $rows[6]["min_order"] !== 4000) {{ fwrite(STDERR, "delivery tier endpoints mismatch\\n"); exit(1); }}
$product_id = wc_get_product_id_by_sku("RB-ROLLS-FILADELFIYA");
$product = wc_get_product($product_id);
if (!$product) {{ fwrite(STDERR, "smoke product missing\\n"); exit(1); }}
if (trim((string) $product->get_meta("_rollsbar_weight_display", true)) !== "250 г") {{ fwrite(STDERR, "weight seed mismatch\\n"); exit(1); }}
$columns = RollsBar_Order_Details::add_order_list_columns(array("order_number" => "Order", "order_status" => "Status", "order_total" => "Total"));
foreach (array("rollsbar_customer","rollsbar_phone","rollsbar_address","rollsbar_zone","rollsbar_time") as $required) {{ if (!array_key_exists($required, $columns)) {{ fwrite(STDERR, "missing operator column\\n"); exit(1); }} }}
echo "LIVE BUSINESS RUNTIME PASS\\n";
'

home="$(wp --path="$WP_PATH" option get home)"
siteurl="$(wp --path="$WP_PATH" option get siteurl)"
blog_public="$(wp --path="$WP_PATH" option get blog_public)"
force_ssl="$(wp --path="$WP_PATH" config get FORCE_SSL_ADMIN)"
[[ "$home" == "$STAGING_URL" ]]
[[ "$siteurl" == "$STAGING_URL" ]]
[[ "$blog_public" == "0" ]]
[[ "$force_ssl" == "true" || "$force_ssl" == "1" ]]
printf 'LIVE HTTPS CONFIG PASS\n'
printf 'REG.RU SERVER GATE B PASS\n'
'''
    run(client, command)
except (paramiko.SSHException, socket.error, OSError, RuntimeError) as exc:
    print(f"gate_b_server=failed type={exc.__class__.__name__}")
    print(str(exc).replace(PASSWORD, "***"))
    raise SystemExit(1)
finally:
    if client is not None:
        client.close()

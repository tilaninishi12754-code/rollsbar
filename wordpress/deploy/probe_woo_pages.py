#!/usr/bin/env python3
"""Read-only probe of WooCommerce page IDs, slugs and resolved URLs on staging."""
from __future__ import annotations

import os
import shlex
import socket
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
DOMAIN = "staging.rollsbar.ru"


def connect() -> paramiko.SSHClient:
    host = urlsplit(BASE).hostname or ""
    if not host:
        raise RuntimeError("Could not derive hosting hostname")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, port=22, username=USER, password=PASSWORD,
                   timeout=15, auth_timeout=15, banner_timeout=15,
                   look_for_keys=False, allow_agent=False)
    return client


def run(client: paramiko.SSHClient, command: str) -> str:
    _, stdout, stderr = client.exec_command("bash -lc " + shlex.quote(command), timeout=90)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    if out:
        print(out, end="" if out.endswith("\n") else "\n")
    if status != 0:
        safe = [line for line in err.splitlines() if "pass" not in line.lower() and "secret" not in line.lower()]
        if safe:
            print("remote_stderr=" + " | ".join(safe[-8:])[:1200])
        raise RuntimeError(f"Woo page probe failed with exit status {status}")
    return out


client = None
try:
    client = connect()
    php = r'''
$keys = array(
  "cart" => "woocommerce_cart_page_id",
  "checkout" => "woocommerce_checkout_page_id",
  "myaccount" => "woocommerce_myaccount_page_id",
);
foreach ($keys as $label => $opt) {
  $id = (int) get_option($opt);
  $post = $id ? get_post($id) : null;
  $slug = $post ? $post->post_name : "";
  $status = $post ? $post->post_status : "missing";
  $url = $id ? get_permalink($id) : "";
  echo $label . "_id=" . $id . "\n";
  echo $label . "_slug=" . $slug . "\n";
  echo $label . "_status=" . $status . "\n";
  echo $label . "_url=" . $url . "\n";
}
echo "wc_cart_url=" . wc_get_cart_url() . "\n";
echo "wc_checkout_url=" . wc_get_checkout_url() . "\n";
echo "home=" . home_url("/") . "\n";
'''
    command = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="$HOME/www/{DOMAIN}"
wp --path="$WP_PATH" eval {shlex.quote(php)}
printf 'mutation=not attempted\n'
printf 'WOO PAGE PROBE PASS\n'
'''
    run(client, command)
except (paramiko.SSHException, socket.error, OSError, RuntimeError) as exc:
    print(f"woo_page_probe=failed type={exc.__class__.__name__}")
    print(str(exc).replace(PASSWORD, "***"))
    raise SystemExit(1)
finally:
    if client is not None:
        client.close()

#!/usr/bin/env python3
"""Read-only WooCommerce New order email readiness audit for REG.RU staging.

The audit does NOT create orders, call wp_mail(), mutate WordPress options, or
send network mail. It only inspects the current WooCommerce email settings and
the local PHP/sendmail capability. Email addresses are masked in output.
"""
from __future__ import annotations

import base64
import os
import shlex
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
WP_PATH = "$HOME/www/staging.rollsbar.ru"

PHP_AUDIT = r'''<?php
if ( ! defined( 'ABSPATH' ) ) { exit(1); }

function rb_mask_email( string $email ): string {
    $email = sanitize_email( trim( $email ) );
    if ( ! $email || false === strpos( $email, '@' ) ) {
        return 'invalid';
    }
    [$local, $domain] = explode( '@', $email, 2 );
    return '***@' . strtolower( $domain );
}

function rb_split_recipients( string $value ): array {
    $items = preg_split( '/[,;]+/', $value ) ?: array();
    $out = array();
    foreach ( $items as $item ) {
        $item = sanitize_email( trim( $item ) );
        if ( $item && is_email( $item ) ) { $out[] = strtolower( $item ); }
    }
    return array_values( array_unique( $out ) );
}

if ( ! class_exists( 'WooCommerce' ) || ! function_exists( 'WC' ) ) {
    fwrite( STDERR, "WooCommerce unavailable.\n" );
    exit( 2 );
}

$new_order = null;
foreach ( WC()->mailer()->get_emails() as $email ) {
    if ( is_object( $email ) && isset( $email->id ) && 'new_order' === (string) $email->id ) {
        $new_order = $email;
        break;
    }
}
if ( ! $new_order ) {
    fwrite( STDERR, "WooCommerce New order email class unavailable.\n" );
    exit( 3 );
}

$settings = get_option( 'woocommerce_new_order_settings', array() );
$settings = is_array( $settings ) ? $settings : array();
$raw_recipient = trim( (string) ( $settings['recipient'] ?? '' ) );
$effective_recipient = trim( (string) $new_order->get_recipient() );
$recipients = rb_split_recipients( $effective_recipient );
$admin_email = sanitize_email( (string) get_option( 'admin_email', '' ) );
$from_address = sanitize_email( (string) get_option( 'woocommerce_email_from_address', '' ) );
if ( ! $from_address ) { $from_address = $admin_email; }
$from_name = trim( (string) get_option( 'woocommerce_email_from_name', '' ) );
if ( '' === $from_name ) { $from_name = (string) get_bloginfo( 'name' ); }

$all_match_admin = count( $recipients ) === 1 && $admin_email && strtolower( $admin_email ) === $recipients[0];
$valid_recipient_count = count( $recipients );

echo "MAIL READINESS WORDPRESS\n";
echo 'new_order_enabled=' . ( $new_order->is_enabled() ? 'yes' : 'no' ) . "\n";
echo 'recipient_source=' . ( '' !== $raw_recipient ? 'explicit_woocommerce_setting' : 'woocommerce_default_or_filter' ) . "\n";
echo 'recipient_count=' . $valid_recipient_count . "\n";
foreach ( $recipients as $index => $recipient ) {
    echo 'recipient_' . ( $index + 1 ) . '_masked=' . rb_mask_email( $recipient ) . "\n";
}
echo 'recipient_matches_admin_email=' . ( $all_match_admin ? 'yes' : 'no' ) . "\n";
echo 'admin_email_masked=' . rb_mask_email( $admin_email ) . "\n";
echo 'from_address_masked=' . rb_mask_email( $from_address ) . "\n";
echo 'from_name_configured=' . ( '' !== $from_name ? 'yes' : 'no' ) . "\n";
echo 'php_mail_function=' . ( function_exists( 'mail' ) ? 'available' : 'missing' ) . "\n";
echo 'phpmailer_init_hook_count=' . (int) has_action( 'phpmailer_init' ) . "\n";
echo 'wp_mail_from_filter=' . ( has_filter( 'wp_mail_from' ) ? 'present' : 'none' ) . "\n";
echo 'wp_mail_from_name_filter=' . ( has_filter( 'wp_mail_from_name' ) ? 'present' : 'none' ) . "\n";
echo 'wp_environment=' . ( function_exists( 'wp_get_environment_type' ) ? wp_get_environment_type() : 'unknown' ) . "\n";

echo 'assert_new_order_enabled=' . ( $new_order->is_enabled() ? 'pass' : 'fail' ) . "\n";
echo 'assert_valid_recipient_present=' . ( $valid_recipient_count > 0 ? 'pass' : 'fail' ) . "\n";
echo 'assert_from_address_valid=' . ( $from_address && is_email( $from_address ) ? 'pass' : 'fail' ) . "\n";
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


def run(client: paramiko.SSHClient, command: str) -> str:
    _, stdout, stderr = client.exec_command("bash -lc " + shlex.quote(command), timeout=180)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    if status != 0:
        safe = " | ".join(
            line for line in err.splitlines()
            if not any(term in line.lower() for term in ("password", "secret", "token"))
        )[-1200:]
        raise RuntimeError(f"Remote mail audit failed status={status}: {safe}")
    print(out, end="" if out.endswith("\n") or not out else "\n")
    return out


def main() -> int:
    payload = base64.b64encode(PHP_AUDIT.encode("utf-8")).decode("ascii")
    client = connect()
    try:
        command = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="{WP_PATH}"
tmp="$(mktemp "$HOME/.rollsbar-mail-audit.XXXXXX.php")"
cleanup() {{ rm -f "$tmp"; }}
trap cleanup EXIT
printf %s {shlex.quote(payload)} | base64 -d > "$tmp"
chmod 600 "$tmp"
wp --path="$WP_PATH" eval-file "$tmp"

mail_disabled="$(php -r 'echo in_array("mail", array_map("trim", explode(",", (string) ini_get("disable_functions"))), true) ? "yes" : "no";')"
sendmail_path="$(php -r 'echo (string) ini_get("sendmail_path");')"
sendmail_binary="$(printf '%s' "$sendmail_path" | awk '{{print $1}}')"
active_plugins="$(wp --path="$WP_PATH" plugin list --status=active --field=name | paste -sd, -)"

echo 'MAIL READINESS TRANSPORT'
echo "php_os_family=$(php -r 'echo PHP_OS_FAMILY;')"
echo "mail_disabled_by_php=$mail_disabled"
if [[ -n "$sendmail_path" ]]; then
  echo 'sendmail_path_configured=yes'
else
  echo 'sendmail_path_configured=no'
fi
if [[ -n "$sendmail_binary" && -x "$sendmail_binary" ]]; then
  echo 'sendmail_binary_executable=yes'
else
  echo 'sendmail_binary_executable=no'
fi
if command -v sendmail >/dev/null 2>&1; then
  echo 'sendmail_command_available=yes'
else
  echo 'sendmail_command_available=no'
fi
echo "active_plugins=$active_plugins"

# This is intentionally capability-only: no test message is sent.
if [[ "$mail_disabled" == 'no' && ( -x "$sendmail_binary" || "$(command -v sendmail >/dev/null 2>&1; echo $?)" == '0' ) ]]; then
  echo 'local_mail_transport_candidate=yes'
else
  echo 'local_mail_transport_candidate=no'
fi
echo 'real_message_sent=no'
echo 'end_to_end_delivery_proven=no'
'''
        out = run(client, command)
    finally:
        client.close()

    required = (
        "assert_new_order_enabled=pass",
        "assert_valid_recipient_present=pass",
        "assert_from_address_valid=pass",
        "real_message_sent=no",
        "end_to_end_delivery_proven=no",
    )
    missing = [needle for needle in required if needle not in out]
    if missing:
        print("MAIL READINESS AUDIT FAIL: " + ",".join(missing))
        return 1

    print("MAIL READINESS READ-ONLY AUDIT PASS")
    print("recipient_approval=external_confirmation_required")
    print("delivery_receipt=external_proof_required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

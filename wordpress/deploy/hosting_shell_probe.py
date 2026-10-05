#!/usr/bin/env python3
"""Read-only SSH shell capability probe for REG.RU staging hosting.

Uses the same staging secrets as the existing SFTP probe. Runs only harmless
read-only commands and prints capability booleans, never credentials or paths.
"""
from __future__ import annotations

import os
import socket
from urllib.parse import urlsplit

import paramiko

base = os.environ["ISP_MANAGER_URL"].strip()
user = os.environ["ISP_MANAGER_USER"].strip()
password = os.environ["ISP_MANAGER_PASSWORD"].strip()
host = urlsplit(base).hostname or ""
if not host:
    raise SystemExit("Could not derive hosting hostname")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(
        hostname=host,
        port=22,
        username=user,
        password=password,
        timeout=12,
        auth_timeout=12,
        banner_timeout=12,
        look_for_keys=False,
        allow_agent=False,
    )
    command = r'''set -eu
printf 'shell=ok\n'
printf 'php='; if command -v php >/dev/null 2>&1; then php -r 'echo PHP_VERSION;' 2>/dev/null || true; else printf 'missing'; fi; printf '\n'
printf 'wp_cli='; if command -v wp >/dev/null 2>&1; then printf 'yes'; else printf 'no'; fi; printf '\n'
printf 'git='; if command -v git >/dev/null 2>&1; then printf 'yes'; else printf 'no'; fi; printf '\n'
printf 'curl='; if command -v curl >/dev/null 2>&1; then printf 'yes'; else printf 'no'; fi; printf '\n'
printf 'unzip='; if command -v unzip >/dev/null 2>&1; then printf 'yes'; else printf 'no'; fi; printf '\n'
printf 'home_writable='; if test -w "$HOME"; then printf 'yes'; else printf 'no'; fi; printf '\n'
'''
    _, stdout, stderr = client.exec_command(command, timeout=20)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    print("REG.RU SSH shell read-only probe")
    print(out.strip())
    print("mutation=not attempted")
    if status != 0:
        print(f"exit_status={status}")
        if err:
            print("stderr_present=yes")
        raise SystemExit("SSH SHELL PROBE FAILED")
    print("SSH SHELL PROBE PASS")
except (paramiko.SSHException, socket.error, OSError) as exc:
    print("REG.RU SSH shell read-only probe")
    print(f"shell=failed type={exc.__class__.__name__}")
    print("mutation=not attempted")
    raise SystemExit("SSH SHELL PROBE FAILED")
finally:
    client.close()

#!/usr/bin/env python3
"""Run the canonical RollsBar staging backup over SSH without exposing secrets."""
from __future__ import annotations

import os
import shlex
import socket
from pathlib import Path
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
DOMAIN = "staging.rollsbar.ru"
REMOTE_SCRIPT = ".rollsbar-backup-run.sh"
LOCAL_SCRIPT = Path(__file__).with_name("backup-staging.sh")


def q(value: str) -> str:
    return shlex.quote(value)


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


def upload_script(client: paramiko.SSHClient) -> None:
    body = LOCAL_SCRIPT.read_bytes()
    sftp = client.open_sftp()
    try:
        with sftp.open(REMOTE_SCRIPT, "wb") as fh:
            fh.write(body)
        sftp.chmod(REMOTE_SCRIPT, 0o700)
    finally:
        sftp.close()


def remove_script(client: paramiko.SSHClient) -> None:
    try:
        sftp = client.open_sftp()
        try:
            sftp.remove(REMOTE_SCRIPT)
        except FileNotFoundError:
            pass
        finally:
            sftp.close()
    except Exception:
        pass


def run(client: paramiko.SSHClient) -> str:
    remote = f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export WP_PATH="$HOME/www/{DOMAIN}"
export ROLLSBAR_BACKUP_ROOT="$HOME/rollsbar-backups/staging"
export ROLLSBAR_BACKUP_RETENTION=5
bash "$HOME/{REMOTE_SCRIPT}"
'''
    _, stdout, stderr = client.exec_command("bash -lc " + q(remote), timeout=420)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    print(out, end="" if out.endswith("\n") or not out else "\n")
    if status != 0:
        safe_lines = [
            line for line in err.splitlines()
            if "password" not in line.lower() and "db_" not in line.lower()
        ]
        if safe_lines:
            print("remote_stderr=" + " | ".join(safe_lines[-10:])[:1600])
        raise RuntimeError(f"Remote backup failed with exit status {status}")
    return out


client = None
try:
    client = connect()
    upload_script(client)
    output = run(client)
    if "BACKUP VERIFIED PASS" not in output:
        raise RuntimeError("Backup command returned success without verification marker")
except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError) as exc:
    message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
    print(f"staging_backup=failed type={exc.__class__.__name__}")
    print(message)
    raise SystemExit(1)
finally:
    if client is not None:
        remove_script(client)
        client.close()

#!/usr/bin/env python3
"""Read-only REG.RU hosting access probe.

Uses existing staging secrets to distinguish invalid credentials from an
ISPmanager remote-API restriction. Performs directory listing only; no writes.
"""
from __future__ import annotations

import ftplib
import os
import socket
import ssl
import sys
from urllib.parse import urlparse

PANEL_URL = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()

host = urlparse(PANEL_URL).hostname
if not host:
    raise SystemExit("Could not derive hosting host from ISP_MANAGER_URL")

results: list[str] = []

# SFTP over SSH. REG.RU documents SFTP for the primary hosting account on all
# virtual-hosting plans except Host-Lite.
try:
    import paramiko  # type: ignore

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=22,
        username=USER,
        password=PASSWORD,
        timeout=12,
        banner_timeout=12,
        auth_timeout=12,
        allow_agent=False,
        look_for_keys=False,
    )
    sftp = client.open_sftp()
    entries = sftp.listdir(".")
    results.append(f"sftp=ok entries={len(entries)}")
    sftp.close()
    client.close()
except Exception as exc:
    results.append(f"sftp=failed type={exc.__class__.__name__}")

# Explicit FTPS (FTP over TLS), read-only LIST/NLST.
try:
    context = ssl.create_default_context()
    ftp = ftplib.FTP_TLS(context=context, timeout=12)
    ftp.connect(host=host, port=21, timeout=12)
    ftp.auth()
    ftp.login(USER, PASSWORD)
    ftp.prot_p()
    entries = ftp.nlst()
    results.append(f"ftps=ok entries={len(entries)}")
    ftp.quit()
except Exception as exc:
    results.append(f"ftps=failed type={exc.__class__.__name__}")

print("REG.RU hosting read-only access probe")
print(f"- endpoint host: {host}")
for result in results:
    print(f"- {result}")
print("- mutation: not attempted")

if not any(item.startswith(("sftp=ok", "ftps=ok")) for item in results):
    raise SystemExit("HOSTING ACCESS PROBE FAILED")

print("HOSTING ACCESS PROBE PASS")

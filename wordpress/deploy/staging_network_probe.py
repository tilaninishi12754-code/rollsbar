#!/usr/bin/env python3
"""Read-only DNS/HTTP readiness probe for RollsBar staging."""
from __future__ import annotations

import socket
import ssl
import urllib.error
import urllib.request

DOMAIN = "staging.rollsbar.ru"
EXPECTED_IPV4 = "37.140.192.67"

print(f"domain={DOMAIN}")
try:
    infos = socket.getaddrinfo(DOMAIN, 80, type=socket.SOCK_STREAM)
    ipv4 = sorted({item[4][0] for item in infos if item[0] == socket.AF_INET})
    ipv6 = sorted({item[4][0] for item in infos if item[0] == socket.AF_INET6})
except socket.gaierror as exc:
    print(f"dns=unresolved type={exc.__class__.__name__}")
    raise SystemExit(2)

print("ipv4=" + (",".join(ipv4) if ipv4 else "none"))
print("ipv6=" + (",".join(ipv6) if ipv6 else "none"))
print(f"expected_ipv4={EXPECTED_IPV4}")
print(f"dns_expected={'yes' if EXPECTED_IPV4 in ipv4 else 'no'}")

for scheme in ("http", "https"):
    url = f"{scheme}://{DOMAIN}/"
    try:
        ctx = ssl.create_default_context() if scheme == "https" else None
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "rollsbar-staging-network-probe/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=12) as response:
            print(f"{scheme}_status={response.status}")
    except urllib.error.HTTPError as exc:
        print(f"{scheme}_status={exc.code}")
    except Exception as exc:
        print(f"{scheme}_status=unavailable type={exc.__class__.__name__}")

if EXPECTED_IPV4 not in ipv4:
    raise SystemExit(3)
print("STAGING NETWORK PROBE PASS")

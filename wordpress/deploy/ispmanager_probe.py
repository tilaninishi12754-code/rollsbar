#!/usr/bin/env python3
"""Read-only ISPmanager API capability probe.

Required environment variables:
  ISP_MANAGER_URL
  ISP_MANAGER_USER
  ISP_MANAGER_PASSWORD

The probe never creates, updates, or deletes ISPmanager objects. It first tries
session authentication documented by ISPmanager, then falls back to the
official authinfo method used for remote API calls. Secrets are never printed.
"""
from __future__ import annotations

import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = os.environ["ISP_MANAGER_URL"].strip().rstrip("/")
USER = os.environ["ISP_MANAGER_USER"]
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"]
VERIFY_TLS = os.environ.get("ISP_TLS_VERIFY", "1").lower() not in {"0", "false", "no"}

if not BASE.startswith("https://"):
    raise SystemExit("ISP_MANAGER_URL must use https://")

ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"

context = ssl.create_default_context()
if not VERIFY_TLS:
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE


def redact(value: str) -> str:
    value = value.replace(PASSWORD, "***")
    value = value.replace(USER, "***")
    return value[:500]


def call(params: dict[str, str]) -> tuple[int, str, bytes]:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "rollsbar-ispmanager-probe/1.1"},
    )
    try:
        with urllib.request.urlopen(req, context=context, timeout=20) as response:
            return (
                int(getattr(response, "status", 200)),
                response.headers.get("Content-Type", ""),
                response.read(),
            )
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read()


def parse_xml(body: bytes) -> ET.Element | None:
    try:
        return ET.fromstring(body)
    except ET.ParseError:
        return None


def describe_response(status: int, content_type: str, body: bytes) -> str:
    root = parse_xml(body)
    if root is None:
        return f"http={status}, content_type={content_type or 'unknown'}, body=non-xml"

    error = root.find(".//error")
    if error is not None:
        attrs = ", ".join(f"{k}={v}" for k, v in sorted(error.attrib.items()))
        text = " ".join("".join(error.itertext()).split())
        details = "; ".join(part for part in (attrs, text) if part)
        return redact(f"http={status}, api_error={details or 'present'}")

    return f"http={status}, xml_root={root.tag}"


def check_functions(auth_params: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    checks: dict[str, str] = {}
    diagnostics: list[str] = []

    for func in ("webdomain", "db"):
        status, content_type, payload = call({**auth_params, "out": "xml", "func": func})
        root = parse_xml(payload)
        error = root.find(".//error") if root is not None else None
        ok = status < 400 and root is not None and error is None
        checks[func] = "ok" if ok else "error"
        if not ok:
            diagnostics.append(f"{func}: {describe_response(status, content_type, payload)}")

    return checks, diagnostics


# 1) Official session-ID authentication.
status, content_type, auth_body = call(
    {
        "out": "xml",
        "func": "auth",
        "username": USER,
        "password": PASSWORD,
    }
)
root = parse_xml(auth_body)
auth = root.find(".//auth") if root is not None else None
session_id = auth.attrib.get("id", "") if auth is not None else ""

checks: dict[str, str]
diagnostics: list[str] = []
auth_mode = ""

if session_id:
    auth_mode = "session"
    checks, diagnostics = check_functions({"auth": session_id})
else:
    diagnostics.append("session auth: " + describe_response(status, content_type, auth_body))

    # 2) Official authinfo authentication for remote API calls.
    auth_mode = "authinfo"
    checks, authinfo_diagnostics = check_functions({"authinfo": f"{USER}:{PASSWORD}"})
    diagnostics.extend(authinfo_diagnostics)

print("ISPmanager read-only probe")
print(f"- endpoint host: {urllib.parse.urlsplit(ENDPOINT).hostname}")
print(f"- auth mode attempted/final: {auth_mode}")
print(f"- websites API: {checks['webdomain']}")
print(f"- databases API: {checks['db']}")
print("- mutation: not attempted")

if checks["webdomain"] != "ok" or checks["db"] != "ok":
    for item in diagnostics:
        print("- diagnostic: " + item)
    raise SystemExit("PROBE FAILED: read-only ISPmanager API capabilities were not confirmed")

print("PROBE PASS")

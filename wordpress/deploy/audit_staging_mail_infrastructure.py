#!/usr/bin/env python3
"""Read-only REG.RU/ISPmanager + DNS mail infrastructure audit.

No mail domains, mailboxes, DNS records or WordPress options are modified.
Mailbox addresses are masked before output. The audit exists to determine the
smallest real external input required for Rolls Bar transactional email.
"""
from __future__ import annotations

import os
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Iterable

import dns.resolver

BASE = os.environ["ISP_MANAGER_URL"].strip().rstrip("/")
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
ENDPOINT = BASE if BASE.endswith("/ispmgr") else BASE + "/ispmgr"
CTX = ssl.create_default_context()
TARGETS = ("rollsbar.ru", "staging.rollsbar.ru")


def call(params: dict[str, str]) -> ET.Element:
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "rollsbar-mail-infra-audit/1.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as response:
        root = ET.fromstring(response.read())
    err = root.find(".//error")
    if err is not None:
        safe = {
            key: value
            for key, value in err.attrib.items()
            if not any(term in key.lower() for term in ("pass", "auth", "secret", "token"))
        }
        raise RuntimeError(f"ISPmanager error func={params.get('func')}: {safe}")
    return root


def auth() -> str:
    root = call({"out": "xml", "func": "auth", "username": USER, "password": PASSWORD})
    node = root.find(".//auth")
    sid = node.attrib.get("id", "") if node is not None else ""
    if not sid:
        raise RuntimeError("ISPmanager authentication failed")
    return sid


def rows(root: ET.Element) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for elem in root.findall(".//elem"):
        row: dict[str, str] = {}
        for child in list(elem):
            if len(list(child)) == 0:
                row[child.tag] = (child.text or "").strip()
        if row:
            result.append(row)
    return result


def mask_mailbox(value: str, domain_hint: str = "") -> str:
    value = value.strip().lower()
    if "@" in value:
        _, domain = value.rsplit("@", 1)
        return "***@" + domain
    if domain_hint:
        return "***@" + domain_hint.lower()
    return "***"


def relevant_mailbox(row: dict[str, str]) -> tuple[bool, str]:
    name = row.get("name", "").strip().lower()
    domain = row.get("domain", "").strip().lower()
    combined = name if "@" in name else (f"{name}@{domain}" if name and domain else name)
    for target in TARGETS:
        if combined.endswith("@" + target) or domain == target:
            return True, mask_mailbox(name, domain)
    return False, ""


def resolve(name: str, record_type: str) -> list[str]:
    try:
        answer = dns.resolver.resolve(name, record_type, lifetime=8)
    except Exception:
        return []
    return sorted(str(item).strip().strip('"') for item in answer)


def has_prefix(records: Iterable[str], prefix: str) -> bool:
    p = prefix.lower()
    return any(record.lower().startswith(p) for record in records)


def main() -> int:
    print("MAIL INFRASTRUCTURE READ-ONLY AUDIT")
    print("mutation=no")

    sid = auth()
    domain_rows = rows(call({"out": "xml", "func": "emaildomain", "auth": sid}))
    mailbox_rows = rows(call({"out": "xml", "func": "email", "auth": sid}))

    domains = sorted({row.get("name", "").strip().lower() for row in domain_rows if row.get("name")})
    print(f"ispmanager_mail_domain_count={len(domains)}")
    for target in TARGETS:
        print(f"ispmanager_mail_domain_{target.replace('.', '_')}={'yes' if target in domains else 'no'}")

    relevant: list[str] = []
    for row in mailbox_rows:
        is_relevant, masked = relevant_mailbox(row)
        if is_relevant:
            relevant.append(masked)
    relevant = sorted(set(relevant))
    print(f"ispmanager_mailbox_total_count={len(mailbox_rows)}")
    print(f"rollsbar_relevant_mailbox_count={len(relevant)}")
    for index, masked in enumerate(relevant, 1):
        print(f"rollsbar_mailbox_{index}_masked={masked}")

    for domain in TARGETS:
        mx = resolve(domain, "MX")
        txt = resolve(domain, "TXT")
        dmarc = resolve("_dmarc." + domain, "TXT")
        print(f"dns_{domain.replace('.', '_')}_mx_count={len(mx)}")
        for index, record in enumerate(mx, 1):
            print(f"dns_{domain.replace('.', '_')}_mx_{index}={record}")
        print(f"dns_{domain.replace('.', '_')}_spf={'yes' if has_prefix(txt, 'v=spf1') else 'no'}")
        print(f"dns_{domain.replace('.', '_')}_dmarc={'yes' if has_prefix(dmarc, 'v=dmarc1') else 'no'}")

    rollsbar_domain_present = "rollsbar.ru" in domains
    rollsbar_mailbox_present = any(item.endswith("@rollsbar.ru") for item in relevant)
    rollsbar_mx_present = bool(resolve("rollsbar.ru", "MX"))

    print(f"assert_rollsbar_mail_domain_present={'pass' if rollsbar_domain_present else 'pending'}")
    print(f"assert_rollsbar_mailbox_present={'pass' if rollsbar_mailbox_present else 'pending'}")
    print(f"assert_rollsbar_mx_present={'pass' if rollsbar_mx_present else 'pending'}")
    print("real_message_sent=no")

    # This audit intentionally does not fail when infrastructure is absent: an
    # absent mailbox/DNS setup is exactly the external-input fact we are trying
    # to discover without mutating the hosting account.
    print("MAIL INFRASTRUCTURE READ-ONLY AUDIT COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

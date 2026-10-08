#!/usr/bin/env python3
"""Runtime smoke for the staging-only DaData checkout address flow."""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

BASE = "https://staging.rollsbar.ru"
SUGGEST = BASE + "/wp-json/rollsbar/v1/address-suggestions"
RESOLVE = BASE + "/wp-json/rollsbar/v1/address-resolve"
CHECKOUT = BASE + "/checkout/"


def request_json(url: str, *, data: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json", "User-Agent": "RollsBar-Staging-Smoke/1.0"}
    method = "GET"
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return json.loads(response.read().decode("utf-8"))


def suggest(query: str) -> dict:
    payload = request_json(SUGGEST + "?" + urllib.parse.urlencode({"query": query}))
    items = payload.get("suggestions")
    if not isinstance(items, list) or not items:
        raise AssertionError(f"No suggestions for {query!r}")
    first = items[0]
    if not isinstance(first, dict) or not first.get("display") or not first.get("token"):
        raise AssertionError(f"Malformed suggestion for {query!r}: {first!r}")
    forbidden = {"country", "country_iso", "country_iso_code", "value", "unrestricted_value"}
    leaked = forbidden.intersection(first)
    if leaked:
        raise AssertionError(f"Provider geography/raw fields leaked in suggestion: {sorted(leaked)}")
    if "Укра" in first["display"] or "Россия" in first["display"]:
        raise AssertionError(f"Country label leaked into customer display: {first['display']!r}")
    return first


def resolve(item: dict) -> dict:
    payload = request_json(RESOLVE, data={"token": item["token"]})
    forbidden = {"country", "country_iso", "country_iso_code", "value", "unrestricted_value"}
    leaked = forbidden.intersection(payload)
    if leaked:
        raise AssertionError(f"Provider geography/raw fields leaked in resolve: {sorted(leaked)}")
    if "Укра" in str(payload.get("display", "")) or "Россия" in str(payload.get("display", "")):
        raise AssertionError(f"Country label leaked into resolved display: {payload.get('display')!r}")
    if payload.get("lat") is None or payload.get("lon") is None:
        raise AssertionError(f"Coordinates missing: {payload!r}")
    if not isinstance(payload.get("precision"), dict):
        raise AssertionError(f"Precision policy missing: {payload!r}")
    return payload


def checkout_config_present() -> None:
    req = urllib.request.Request(CHECKOUT, headers={"User-Agent": "RollsBar-Staging-Smoke/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        html = response.read().decode("utf-8", errors="replace")
    if "rollsBarCheckoutConfig" not in html:
        raise AssertionError("Checkout config is not rendered")
    if '"enabled":true' not in html:
        raise AssertionError("Address suggestions are not enabled on staging checkout")
    if "/wp-json/rollsbar/v1/address-suggestions" not in html:
        raise AssertionError("Suggestion endpoint missing from checkout config")


def main() -> int:
    exact_item = suggest("Симферополь Гагарина 17")
    exact = resolve(exact_item)
    if exact.get("qc_geo") != 0:
        raise AssertionError(f"Expected qc_geo=0 for exact-house probe, got {exact.get('qc_geo')!r}: {exact.get('display')}")
    if exact["precision"].get("allow_auto_zone") is not True:
        raise AssertionError("Exact-house probe must allow future automatic zone lookup")

    low_item = suggest("Дубки Раздерина 12")
    low = resolve(low_item)
    if low.get("qc_geo") not in (1, 2, 3, 4, 5):
        raise AssertionError(f"Expected non-exact qc_geo for low-precision probe, got {low.get('qc_geo')!r}: {low.get('display')}")
    if low["precision"].get("allow_auto_zone") is not False:
        raise AssertionError("Low-precision probe must fail closed")

    checkout_config_present()

    print("STAGING ADDRESS SUGGESTIONS PASS")
    print(f"exact={exact.get('display')} qc_geo={exact.get('qc_geo')} allow_auto_zone={exact['precision'].get('allow_auto_zone')}")
    print(f"low_precision={low.get('display')} qc_geo={low.get('qc_geo')} allow_auto_zone={low['precision'].get('allow_auto_zone')}")
    print("country_labels_exposed=no")
    print("checkout_suggestions_enabled=yes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"STAGING ADDRESS SUGGESTIONS FAIL: {exc}", file=sys.stderr)
        raise

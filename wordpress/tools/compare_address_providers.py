#!/usr/bin/env python3
"""Evaluate RollsBar address providers without coupling checkout to one vendor.

DaData is the preferred low-cost candidate. Yandex/2GIS remain optional fallback
comparators only when credentials are present. Results are evidence-only and
never alter checkout or delivery enforcement.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

TIMEOUT_SECONDS = 15
USER_AGENT = "RollsBar-Provider-Evaluation/1.1"


@dataclass
class Result:
    provider: str
    input_address: str
    ok: bool
    lat: float | None = None
    lon: float | None = None
    normalized_address: str | None = None
    precision: str | None = None
    country: str | None = None
    country_iso: str | None = None
    country_mismatch: bool = False
    error: str | None = None
    elapsed_ms: int | None = None


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        payload = response.read().decode("utf-8")
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("API response is not a JSON object")
    return parsed


def _timed(provider: str, address: str, fn: Callable[[], Result]) -> Result:
    started = time.perf_counter()
    try:
        result = fn()
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        result = Result(provider=provider, input_address=address, ok=False, error=str(exc))
    result.elapsed_ms = round((time.perf_counter() - started) * 1000)
    return result


def geocode_yandex(address: str, key: str) -> Result:
    provider = "yandex"

    def call() -> Result:
        query = urllib.parse.urlencode({"apikey": key, "geocode": address, "format": "json", "results": 1, "lang": "ru_RU"})
        data = _request_json(f"https://geocode-maps.yandex.ru/1.x/?{query}")
        members = data["response"]["GeoObjectCollection"]["featureMember"]
        if not members:
            return Result(provider=provider, input_address=address, ok=False, error="no results")
        geo = members[0]["GeoObject"]
        lon_text, lat_text = geo["Point"]["pos"].split()
        metadata = geo.get("metaDataProperty", {}).get("GeocoderMetaData", {})
        normalized = metadata.get("text") or geo.get("name")
        precision = metadata.get("precision")
        return Result(provider=provider, input_address=address, ok=True, lat=float(lat_text), lon=float(lon_text), normalized_address=str(normalized) if normalized else None, precision=str(precision) if precision else None)

    return _timed(provider, address, call)


def geocode_2gis(address: str, key: str) -> Result:
    provider = "2gis"

    def call() -> Result:
        query = urllib.parse.urlencode({"q": address, "fields": "items.point,items.geometry.centroid,items.address", "key": key})
        data = _request_json(f"https://catalog.api.2gis.com/3.0/items/geocode?{query}")
        items = data.get("result", {}).get("items", [])
        if not items:
            return Result(provider=provider, input_address=address, ok=False, error="no results")
        item = items[0]
        point = item.get("point") or item.get("geometry", {}).get("centroid") or {}
        lat, lon = point.get("lat"), point.get("lon")
        if lat is None or lon is None:
            return Result(provider=provider, input_address=address, ok=False, error="result has no coordinates")
        normalized = item.get("full_name") or item.get("address_name") or item.get("name")
        precision = item.get("type") or item.get("purpose_name")
        return Result(provider=provider, input_address=address, ok=True, lat=float(lat), lon=float(lon), normalized_address=str(normalized) if normalized else None, precision=str(precision) if precision else None)

    return _timed(provider, address, call)


def geocode_dadata(address: str, key: str) -> Result:
    provider = "dadata"

    def call() -> Result:
        data = _request_json(
            "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address",
            method="POST",
            headers={"Authorization": f"Token {key}"},
            body={"query": address, "count": 1, "language": "ru"},
        )
        suggestions = data.get("suggestions", [])
        if not suggestions:
            return Result(provider=provider, input_address=address, ok=False, error="no results")
        suggestion = suggestions[0]
        details = suggestion.get("data", {})
        lat, lon = details.get("geo_lat"), details.get("geo_lon")
        if lat in (None, "") or lon in (None, ""):
            return Result(provider=provider, input_address=address, ok=False, error="result has no coordinates")
        qc_geo = details.get("qc_geo")
        country = details.get("country")
        country_iso = details.get("country_iso_code")
        return Result(
            provider=provider,
            input_address=address,
            ok=True,
            lat=float(lat),
            lon=float(lon),
            normalized_address=str(suggestion.get("value") or "") or None,
            precision=f"qc_geo={qc_geo}" if qc_geo not in (None, "") else None,
            country=str(country) if country else None,
            country_iso=str(country_iso) if country_iso else None,
            country_mismatch=bool(country_iso and str(country_iso).upper() != "RU"),
        )

    return _timed(provider, address, call)


def haversine_m(a: Result, b: Result) -> float | None:
    if not (a.ok and b.ok) or None in (a.lat, a.lon, b.lat, b.lon):
        return None
    radius = 6_371_000.0
    lat1 = math.radians(float(a.lat))
    lat2 = math.radians(float(b.lat))
    dlat = lat2 - lat1
    dlon = math.radians(float(b.lon) - float(a.lon))
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(radius * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x)), 1)


def load_addresses() -> list[str]:
    raw = os.getenv("ROLLSBAR_TEST_ADDRESSES_JSON", "").strip()
    if not raw:
        raise SystemExit("ROLLSBAR_TEST_ADDRESSES_JSON is empty")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ROLLSBAR_TEST_ADDRESSES_JSON is invalid JSON: {exc}") from exc
    if not isinstance(value, list):
        raise SystemExit("ROLLSBAR_TEST_ADDRESSES_JSON must be a JSON array")
    addresses = [str(item).strip() for item in value if str(item).strip()]
    if not addresses:
        raise SystemExit("Address list is empty")
    if len(addresses) > 50:
        raise SystemExit("Maximum 50 addresses per evaluation run")
    return addresses


def main() -> int:
    addresses = load_addresses()
    provider_keys = {
        "dadata": os.getenv("ROLLSBAR_DADATA_API_KEY", "").strip(),
        "yandex": os.getenv("ROLLSBAR_YANDEX_GEOCODER_KEY", "").strip(),
        "2gis": os.getenv("ROLLSBAR_2GIS_API_KEY", "").strip(),
    }
    provider_fns: dict[str, Callable[[str, str], Result]] = {"dadata": geocode_dadata, "yandex": geocode_yandex, "2gis": geocode_2gis}
    enabled = [name for name, key in provider_keys.items() if key]
    if not enabled:
        raise SystemExit("No provider credentials configured. DaData alone is sufficient for the preferred-path evaluation.")

    rows: list[dict[str, Any]] = []
    for address in addresses:
        by_provider: dict[str, Result] = {provider: provider_fns[provider](address, provider_keys[provider]) for provider in enabled}
        distances: dict[str, float | None] = {}
        for left, right in [("yandex", "2gis"), ("yandex", "dadata"), ("2gis", "dadata")]:
            if left in by_provider and right in by_provider:
                distances[f"{left}_vs_{right}_m"] = haversine_m(by_provider[left], by_provider[right])
        rows.append({"address": address, "providers": {name: asdict(result) for name, result in by_provider.items()}, "distances": distances})

    output = {"preferred_provider": "dadata", "providers_enabled": enabled, "address_count": len(addresses), "rows": rows}
    Path("address-provider-comparison.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# RollsBar address-provider evaluation",
        "",
        "Preferred path: DaData Suggestions free tier -> coordinates -> RollsBar polygon resolver.",
        f"Providers tested: {', '.join(enabled)}",
        f"Addresses: {len(addresses)}",
        "",
        "Country fields are diagnostic only. Production UI must not render provider country labels; it should render only the approved local address components.",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        lines.extend([f"## {index}. {row['address']}", ""])
        for provider in enabled:
            result = row["providers"].get(provider, {})
            if not result.get("ok"):
                lines.append(f"- **{provider}**: ERROR — {result.get('error', 'unknown error')}")
                continue
            country_note = ""
            if provider == "dadata":
                country_note = f" | country: {result.get('country') or 'n/a'} ({result.get('country_iso') or 'n/a'})"
                if result.get("country_mismatch"):
                    country_note += " | **COUNTRY_MISMATCH**"
            lines.append(
                f"- **{provider}**: {result.get('lat')}, {result.get('lon')} | precision: {result.get('precision') or 'n/a'} | "
                f"{result.get('elapsed_ms')} ms{country_note} | {result.get('normalized_address') or ''}"
            )
        if row["distances"]:
            formatted = ", ".join(f"{name.replace('_m', '')}: {distance} m" if distance is not None else f"{name.replace('_m', '')}: n/a" for name, distance in row["distances"].items())
            lines.append(f"- Pairwise coordinate deltas: {formatted}")
        lines.append("")

    if "dadata" in enabled:
        mismatches = [row["address"] for row in rows if row["providers"].get("dadata", {}).get("country_mismatch")]
        lines.extend(["## DaData country-label diagnostic", ""])
        if mismatches:
            lines.append(f"Non-RU country code returned for {len(mismatches)} address(es). Review before integration.")
            lines.extend(f"- {address}" for address in mismatches)
        else:
            lines.append("No non-RU country codes returned in this run.")
        lines.append("")

    Path("address-provider-comparison.md").write_text("\n".join(lines), encoding="utf-8")
    success_counts = {provider: sum(1 for row in rows if row["providers"].get(provider, {}).get("ok")) for provider in enabled}
    print(f"Evaluated {len(addresses)} addresses with providers: {', '.join(enabled)}")
    print("Success counts: " + ", ".join(f"{name}={count}/{len(addresses)}" for name, count in success_counts.items()))
    if "dadata" in enabled:
        mismatch_count = sum(1 for row in rows if row["providers"].get("dadata", {}).get("country_mismatch"))
        print(f"DaData non-RU country-code results: {mismatch_count}/{len(addresses)}")
    print("Wrote address-provider-comparison.md and address-provider-comparison.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

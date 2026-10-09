#!/usr/bin/env python3
"""Read-only SEO/indexability audit for RollsBar staging.

No WordPress settings, plugins, files, database rows, robots rules or sitemaps
are modified. After the verified SEO rollout this audit treats the selected SEO
owner, canonical output, sitemap and schema ownership as hard invariants. Missing
home description/social copy or image remains a content input, not an invented
technical fix.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import ssl
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
SITE = "https://staging.rollsbar.ru"
WP_PATH = "$HOME/www/staging.rollsbar.ru"
EXPECTED_SEOPRESS_VERSION = "10.3"
CTX = ssl.create_default_context()


class HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.canonicals: list[str] = []
        self.meta: list[dict[str, str]] = []
        self.jsonld: list[str] = []
        self._jsonld = False
        self._jsonld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "link" and data.get("rel", "").lower() == "canonical":
            self.canonicals.append(data.get("href", ""))
        if tag.lower() == "meta":
            self.meta.append(data)
        if tag.lower() == "script" and data.get("type", "").lower() == "application/ld+json":
            self._jsonld = True
            self._jsonld_parts = []

    def handle_data(self, data: str) -> None:
        if self._jsonld:
            self._jsonld_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._jsonld:
            self.jsonld.append("".join(self._jsonld_parts).strip())
            self._jsonld = False
            self._jsonld_parts = []


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


def remote(client: paramiko.SSHClient, command: str) -> str:
    wrapped = "bash -lc " + shlex.quote(command)
    _, stdout, stderr = client.exec_command(wrapped, timeout=180)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    status = stdout.channel.recv_exit_status()
    if status != 0:
        safe = " | ".join(
            line for line in err.splitlines()
            if not any(x in line.lower() for x in ("password", "secret", "token"))
        )[-1200:]
        raise RuntimeError(f"remote command failed status={status}: {safe}")
    return out


def fetch(url: str) -> tuple[int, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "RollsBar-SEO-Audit/2.0"})
    try:
        with urllib.request.urlopen(request, context=CTX, timeout=30) as response:
            body = response.read(3_000_000).decode("utf-8", errors="replace")
            return int(response.status), response.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        body = exc.read(1_000_000).decode("utf-8", errors="replace")
        return int(exc.code), exc.headers.get("Content-Type", ""), body


def metas(parser: HeadParser, key: str, value: str) -> list[str]:
    return [
        meta.get("content", "")
        for meta in parser.meta
        if meta.get(key, "").lower() == value.lower()
    ]


def jsonld_types(parser: HeadParser) -> list[str]:
    found: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            typ = value.get("@type")
            if isinstance(typ, str):
                found.append(typ)
            elif isinstance(typ, list):
                found.extend(str(item) for item in typ)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for raw in parser.jsonld:
        try:
            walk(json.loads(raw))
        except Exception:
            continue
    return found


def inspect_html(label: str, url: str) -> dict[str, object]:
    status, content_type, body = fetch(url)
    parser = HeadParser()
    parser.feed(body)
    description = metas(parser, "name", "description")
    robots = metas(parser, "name", "robots")
    og_title = metas(parser, "property", "og:title")
    og_description = metas(parser, "property", "og:description")
    og_image = metas(parser, "property", "og:image")
    types = jsonld_types(parser)
    print(f"{label}_status={status}")
    print(f"{label}_content_type={content_type}")
    print(f"{label}_canonical_count={len(parser.canonicals)}")
    print(f"{label}_meta_description_count={len(description)}")
    print(f"{label}_robots_meta={('|'.join(robots) if robots else 'none')}")
    print(f"{label}_og_title_count={len(og_title)}")
    print(f"{label}_og_description_count={len(og_description)}")
    print(f"{label}_og_image_count={len(og_image)}")
    print(f"{label}_jsonld_scripts={len(parser.jsonld)}")
    print(f"{label}_restaurant_schema_count={types.count('Restaurant')}")
    print(f"{label}_product_schema_count={types.count('Product')}")
    return {
        "status": status,
        "canonical_count": len(parser.canonicals),
        "description_count": len(description),
        "robots": robots,
        "og_title": len(og_title),
        "og_description": len(og_description),
        "og_image": len(og_image),
        "restaurant": types.count("Restaurant"),
        "product": types.count("Product"),
    }


def main() -> int:
    print("SEO STAGING READ-ONLY AUDIT")
    print("mutation=no")

    client = connect()
    try:
        prefix = f"export PATH=\"$HOME/.local/bin:$PATH\"; wp --path=\"{WP_PATH}\""
        plugins = remote(
            client,
            prefix + " plugin list --fields=name,status,version,update,update_version,auto_update --format=csv",
        )
        print("plugin_inventory_begin")
        print(plugins)
        print("plugin_inventory_end")

        blog_public = remote(client, prefix + " option get blog_public")
        seopress_status = remote(client, prefix + " plugin get wp-seopress --field=status")
        seopress_version = remote(client, prefix + " plugin get wp-seopress --field=version")
        description_state = remote(
            client,
            prefix + " option get rollsbar_seo_home_description_state 2>/dev/null || echo missing",
        )
        product_url = remote(
            client,
            prefix
            + " post list --post_type=product --post_status=publish --posts_per_page=1 --field=ID"
            + " | head -n1 | xargs -r "
            + prefix
            + " post url",
        )
        print(f"blog_public={blog_public}")
        print(f"seopress_status={seopress_status}")
        print(f"seopress_version={seopress_version}")
        print(f"home_description_state={description_state}")
        print(f"sample_product_url={product_url}")
    finally:
        client.close()

    home = inspect_html("home", SITE + "/")
    product = inspect_html("product", product_url)
    cart = inspect_html("cart", SITE + "/cart/")
    checkout = inspect_html("checkout", SITE + "/checkout/")

    robots_status, robots_type, robots_body = fetch(SITE + "/robots.txt")
    print(f"robots_status={robots_status}")
    print(f"robots_content_type={robots_type}")
    print(f"robots_disallow_all={'yes' if re.search(r'(?mi)^Disallow:\s*/\s*$', robots_body) else 'no'}")

    sitemap_status, sitemap_type, sitemap_body = fetch(SITE + "/sitemaps.xml")
    print(f"sitemap_status={sitemap_status}")
    print(f"sitemap_content_type={sitemap_type}")
    print(f"sitemap_has_sitemapindex={'yes' if '<sitemapindex' in sitemap_body else 'no'}")

    failures: list[str] = []
    if seopress_status != "active":
        failures.append("seopress_not_active")
    if seopress_version != EXPECTED_SEOPRESS_VERSION:
        failures.append("seopress_version_drift")
    if blog_public != "0":
        failures.append("staging_blog_public_not_zero")
    if int(home["status"]) != 200 or int(product["status"]) != 200:
        failures.append("public_content_route_unhealthy")
    if int(home["canonical_count"]) != 1:
        failures.append("home_canonical_owner_not_exactly_one")
    if int(product["canonical_count"]) != 1:
        failures.append("product_canonical_owner_not_exactly_one")
    if int(home["og_title"]) < 1:
        failures.append("home_open_graph_title_missing")
    if sitemap_status != 200 or "<sitemapindex" not in sitemap_body:
        failures.append("seo_sitemap_missing")
    if int(home["restaurant"]) != 1:
        failures.append("restaurant_schema_owner_not_exactly_one")
    if int(home["product"]) != 0:
        failures.append("product_schema_leaked_to_home")
    if int(product["product"]) != 1:
        failures.append("woocommerce_product_schema_owner_not_exactly_one")
    if int(product["restaurant"]) != 0:
        failures.append("restaurant_schema_leaked_to_product")

    home_robots = " ".join(str(x).lower() for x in home["robots"])  # type: ignore[index]
    if blog_public == "0" and "noindex" not in home_robots:
        failures.append("staging_home_noindex_missing")

    for label, data in (("cart", cart), ("checkout", checkout)):
        robots_values = " ".join(str(x).lower() for x in data["robots"])  # type: ignore[index]
        if "noindex" not in robots_values:
            failures.append(f"{label}_noindex_missing")

    # Since WordPress 5.3, a non-public site no longer has to emit `Disallow: /`.
    # Page-level noindex is the staging hard invariant; robots.txt must still load.
    if robots_status != 200:
        failures.append("robots_txt_unavailable")
    print(
        "staging_indexing_closed="
        + ("yes" if blog_public == "0" and "noindex" in home_robots else "no")
    )

    description_pending = int(home["description_count"]) == 0
    og_description_pending = int(home["og_description"]) == 0
    og_image_pending = int(home["og_image"]) == 0
    print(f"seo_owner_canonical_ready={'yes' if int(home['canonical_count']) == 1 else 'no'}")
    print(f"seo_owner_sitemap_ready={'yes' if sitemap_status == 200 and '<sitemapindex' in sitemap_body else 'no'}")
    print(f"seo_owner_social_title_ready={'yes' if int(home['og_title']) >= 1 else 'no'}")
    print(f"seo_home_description_content_pending={'yes' if description_pending else 'no'}")
    print(f"seo_home_og_description_content_pending={'yes' if og_description_pending else 'no'}")
    print(f"seo_home_og_image_content_pending={'yes' if og_image_pending else 'no'}")

    if description_state == "uses_verified_wordpress_tagline" and description_pending:
        failures.append("verified_home_description_not_rendered")
    if description_state not in ("pending_content_input", "uses_verified_wordpress_tagline"):
        failures.append("home_description_state_unknown")

    if failures:
        print("SEO STAGING AUDIT FAIL: " + ",".join(failures))
        return 1

    print("SEO STAGING READ-ONLY AUDIT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

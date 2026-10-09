#!/usr/bin/env python3
"""Provision the single staging SEO owner without touching production.

Safety invariants:
- hard-coded staging target only;
- explicit confirmation required;
- exact repository SHA checked out on the hosting account;
- fresh canonical DB+uploads backup verified before mutation;
- WordPress/WooCommerce/catalog/indexability invariants verified before and after;
- pinned SEOPress version and auto-update disabled;
- schema-overlap features disabled so WooCommerce remains Product owner and
  RollsBar Core remains Restaurant owner;
- no client-facing SEO description is invented.
"""
from __future__ import annotations

import os
import shlex
import socket
from urllib.parse import urlsplit

import paramiko

BASE = os.environ["ISP_MANAGER_URL"].strip()
USER = os.environ["ISP_MANAGER_USER"].strip()
PASSWORD = os.environ["ISP_MANAGER_PASSWORD"].strip()
DEPLOY_SHA = os.environ["ROLLSBAR_DEPLOY_SHA"].strip()
CONFIRM = os.environ.get("ROLLSBAR_CONFIRM_STAGING_SEO", "")

DOMAIN = "staging.rollsbar.ru"
REPO = "https://github.com/tilaninishi12754-code/rollsbar.git"
WP_VERSION = "7.1.3"
WC_VERSION = "11.1.2"
SEO_SLUG = "wp-seopress"
SEO_VERSION = "10.3"
EXPECTED_PRODUCTS = "118"


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


def execute(client: paramiko.SSHClient) -> str:
    remote = r'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
DOMAIN="__DOMAIN__"
WP_VERSION="__WP_VERSION__"
WC_VERSION="__WC_VERSION__"
SEO_SLUG="__SEO_SLUG__"
SEO_VERSION="__SEO_VERSION__"
EXPECTED_PRODUCTS="__EXPECTED_PRODUCTS__"
DEPLOY_SHA="__DEPLOY_SHA__"
REPO="__REPO__"
WP_PATH="$HOME/www/$DOMAIN"
PROJECT_ROOT="$HOME/.rollsbar-deploy"
BACKUP_ROOT="$HOME/rollsbar-backups/staging"

wp_cmd() { wp --path="$WP_PATH" "$@"; }

[[ -f "$WP_PATH/wp-load.php" ]]
command -v wp >/dev/null 2>&1

home_url="$(wp_cmd option get home)"
site_url="$(wp_cmd option get siteurl)"
core_version="$(wp_cmd core version)"
woo_version="$(wp_cmd plugin get woocommerce --field=version)"
product_count="$(wp_cmd post list --post_type=product --post_status=publish --format=count)"
blog_public="$(wp_cmd option get blog_public)"

[[ "$home_url" == "https://$DOMAIN" ]]
[[ "$site_url" == "https://$DOMAIN" ]]
[[ "$core_version" == "$WP_VERSION" ]]
[[ "$woo_version" == "$WC_VERSION" ]]
[[ "$(wp_cmd plugin get woocommerce --field=status)" == "active" ]]
[[ "$(wp_cmd plugin get rollsbar-core --field=status)" == "active" ]]
[[ "$(wp_cmd theme get rollsbar-theme --field=status)" == "active" ]]
[[ "$product_count" == "$EXPECTED_PRODUCTS" ]]
[[ "$blog_public" == "0" ]]

echo "target=$DOMAIN"
echo "pre_core=$core_version"
echo "pre_woocommerce=$woo_version"
echo "pre_products=$product_count"
echo "pre_blog_public=$blog_public"

if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
  rm -rf "$PROJECT_ROOT"
  git clone --filter=blob:none --no-checkout "$REPO" "$PROJECT_ROOT"
fi
git -C "$PROJECT_ROOT" fetch --depth=1 origin "$DEPLOY_SHA"
git -C "$PROJECT_ROOT" checkout --detach --force "$DEPLOY_SHA"
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == "$DEPLOY_SHA" ]]

echo "stage=backup_before_seo_mutation"
export WP_PATH
export ROLLSBAR_BACKUP_ROOT="$BACKUP_ROOT"
export ROLLSBAR_BACKUP_RETENTION=5
bash "$PROJECT_ROOT/wordpress/deploy/backup-staging.sh"

echo "stage=install_pinned_seopress"
if wp_cmd plugin is-installed "$SEO_SLUG"; then
  installed_version="$(wp_cmd plugin get "$SEO_SLUG" --field=version)"
  echo "seopress_version_before=$installed_version"
  if [[ "$installed_version" != "$SEO_VERSION" ]]; then
    wp_cmd plugin install "$SEO_SLUG" --version="$SEO_VERSION" --force
  fi
else
  echo "seopress_version_before=not_installed"
  wp_cmd plugin install "$SEO_SLUG" --version="$SEO_VERSION"
fi
wp_cmd plugin activate "$SEO_SLUG"
wp_cmd plugin auto-updates disable "$SEO_SLUG" >/dev/null || true

# Keep SEOPress as the metadata/canonical/social/sitemap owner only. Explicitly
# disable overlapping or unused feature families so WooCommerce remains the
# Product schema owner and RollsBar Core remains the Restaurant schema owner.
wp_cmd eval '
$t = get_option( "seopress_toggle", array() );
foreach ( array( "toggle-titles", "toggle-xml-sitemap", "toggle-social" ) as $key ) {
    $t[ $key ] = "1";
}
foreach ( array(
    "toggle-google-analytics",
    "toggle-instant-indexing",
    "toggle-local-business",
    "toggle-rich-snippets",
    "toggle-woocommerce",
    "toggle-robots"
) as $key ) {
    $t[ $key ] = "0";
}
update_option( "seopress_toggle", $t, false );

$sitemap = get_option( "seopress_xml_sitemap_option_name", array() );
$sitemap["seopress_xml_sitemap_general_enable"] = "1";
update_option( "seopress_xml_sitemap_option_name", $sitemap, false );

$social = get_option( "seopress_social_option_name", array() );
$social["seopress_social_facebook_og"] = "1";
$social["seopress_social_twitter_card"] = "1";
update_option( "seopress_social_option_name", $social, false );

// Do not publish a stock WordPress tagline as the home meta description.
$tagline = trim( (string) get_option( "blogdescription", "" ) );
$stock = array( "", "Just another WordPress site", "Ещё один сайт на WordPress", "Еще один сайт на WordPress" );
if ( in_array( $tagline, $stock, true ) ) {
    $titles = get_option( "seopress_titles_option_name", array() );
    $titles["seopress_titles_home_site_desc"] = "";
    update_option( "seopress_titles_option_name", $titles, false );
    update_option( "rollsbar_seo_home_description_state", "pending_content_input", false );
} else {
    update_option( "rollsbar_seo_home_description_state", "uses_verified_wordpress_tagline", false );
}
'

wp_cmd rewrite flush --hard >/dev/null

seo_version="$(wp_cmd plugin get "$SEO_SLUG" --field=version)"
seo_status="$(wp_cmd plugin get "$SEO_SLUG" --field=status)"
woo_version_after="$(wp_cmd plugin get woocommerce --field=version)"
product_count_after="$(wp_cmd post list --post_type=product --post_status=publish --format=count)"
blog_public_after="$(wp_cmd option get blog_public)"
seo_state="$(wp_cmd option get rollsbar_seo_home_description_state)"
seo_auto="$(wp_cmd plugin auto-updates status "$SEO_SLUG" --field=status 2>/dev/null || true)"

toggle_state="$(wp_cmd eval '$t=get_option("seopress_toggle",array()); echo implode(",", array_map(static fn($k)=>$k."=".($t[$k]??"unset"), array("toggle-titles","toggle-xml-sitemap","toggle-social","toggle-local-business","toggle-rich-snippets","toggle-woocommerce","toggle-google-analytics","toggle-instant-indexing","toggle-robots")));')"
sitemap_state="$(wp_cmd eval '$s=get_option("seopress_xml_sitemap_option_name",array()); echo $s["seopress_xml_sitemap_general_enable"]??"unset";')"
social_state="$(wp_cmd eval '$s=get_option("seopress_social_option_name",array()); echo "og=".($s["seopress_social_facebook_og"]??"unset").",twitter=".($s["seopress_social_twitter_card"]??"unset");')"

[[ "$seo_version" == "$SEO_VERSION" ]]
[[ "$seo_status" == "active" ]]
[[ "$woo_version_after" == "$WC_VERSION" ]]
[[ "$product_count_after" == "$EXPECTED_PRODUCTS" ]]
[[ "$blog_public_after" == "0" ]]
[[ "$(wp_cmd plugin get rollsbar-core --field=status)" == "active" ]]
[[ "$(wp_cmd theme get rollsbar-theme --field=status)" == "active" ]]
[[ "$sitemap_state" == "1" ]]

wp_cmd core verify-checksums --version="$WP_VERSION" --locale=en_US >/dev/null

echo "seopress_version=$seo_version"
echo "seopress_status=$seo_status"
echo "seopress_auto_update=${seo_auto:-unknown}"
echo "seopress_toggles=$toggle_state"
echo "seopress_sitemap_enabled=$sitemap_state"
echo "seopress_social=$social_state"
echo "home_description_state=$seo_state"
echo "post_woocommerce=$woo_version_after"
echo "post_products=$product_count_after"
echo "post_blog_public=$blog_public_after"
echo "assert_core_checksums=pass"
echo "STAGING SEO PROVISION PASS"
'''

    replacements = {
        "__DOMAIN__": DOMAIN,
        "__WP_VERSION__": WP_VERSION,
        "__WC_VERSION__": WC_VERSION,
        "__SEO_SLUG__": SEO_SLUG,
        "__SEO_VERSION__": SEO_VERSION,
        "__EXPECTED_PRODUCTS__": EXPECTED_PRODUCTS,
        "__DEPLOY_SHA__": DEPLOY_SHA,
        "__REPO__": REPO,
    }
    for marker, value in replacements.items():
        remote = remote.replace(marker, value)

    _, stdout, stderr = client.exec_command("bash -lc " + q(remote), timeout=900)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    print(out, end="" if out.endswith("\n") or not out else "\n")
    if status != 0:
        safe_lines = [
            line for line in err.splitlines()
            if not any(x in line.lower() for x in ("password", "secret", "token", "dadata", "telegram"))
        ]
        if safe_lines:
            print("remote_stderr=" + " | ".join(safe_lines[-12:])[:1600])
        raise RuntimeError(f"Remote SEO provision failed with exit status {status}")
    return out


if CONFIRM != "YES":
    raise SystemExit("Refusing staging mutation: set ROLLSBAR_CONFIRM_STAGING_SEO=YES")
if len(DEPLOY_SHA) < 7:
    raise SystemExit("ROLLSBAR_DEPLOY_SHA is missing")

client = None
try:
    client = connect()
    result = execute(client)
    if "STAGING SEO PROVISION PASS" not in result:
        raise RuntimeError("SEO provision returned without verification marker")
except (paramiko.SSHException, socket.error, OSError, RuntimeError, ValueError) as exc:
    message = str(exc).replace(PASSWORD, "***") if PASSWORD else str(exc)
    raise SystemExit(message)
finally:
    if client is not None:
        client.close()

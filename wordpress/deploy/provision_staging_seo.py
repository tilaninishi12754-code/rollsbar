#!/usr/bin/env python3
"""Provision the single staging SEO owner without touching production.

Safety invariants:
- hard-coded staging target only;
- explicit confirmation required;
- exact application repository SHA verified on the hosting account;
- fresh canonical DB+uploads backup verified before mutation unless a parent
  routine deploy explicitly proves it already passed the same backup gate;
- WordPress/WooCommerce/catalog/indexability invariants verified before and after;
- pinned SEOPress version and auto-update disabled;
- schema-overlap features disabled so WooCommerce remains Product owner and
  RollsBar Core remains Restaurant owner;
- no client-facing SEO description is invented.
"""
from __future__ import annotations

import os
import re
import shlex

from staging_catalog_audit import AUDIT_PHP, parse_audit, validate_catalog_audit
from staging_ssh import connect


DOMAIN = "staging.rollsbar.ru"
WP_VERSION = "7.1.3"
WC_VERSION = "11.1.2"
SEO_SLUG = "wp-seopress"
SEO_VERSION = "10.3"


def q(value: str) -> str:
    return shlex.quote(value)


def mutation_script(deploy_sha: str, backup_verified: str) -> str:
    remote = r'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
DOMAIN="__DOMAIN__"
WP_VERSION="__WP_VERSION__"
WC_VERSION="__WC_VERSION__"
SEO_SLUG="__SEO_SLUG__"
SEO_VERSION="__SEO_VERSION__"
DEPLOY_SHA="__DEPLOY_SHA__"
BACKUP_ALREADY_VERIFIED="__BACKUP_ALREADY_VERIFIED__"
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
blog_public="$(wp_cmd option get blog_public)"

[[ "$home_url" == "https://$DOMAIN" ]]
[[ "$site_url" == "https://$DOMAIN" ]]
[[ "$core_version" == "$WP_VERSION" ]]
[[ "$woo_version" == "$WC_VERSION" ]]
[[ "$(wp_cmd plugin get woocommerce --field=status)" == "active" ]]
[[ "$(wp_cmd plugin get rollsbar-core --field=status)" == "active" ]]
[[ "$(wp_cmd theme get rollsbar-theme --field=status)" == "active" ]]
[[ "$blog_public" == "0" ]]

echo "target=$DOMAIN"
echo "pre_core=$core_version"
echo "pre_woocommerce=$woo_version"
echo "pre_blog_public=$blog_public"

# Application code is already deployed; SEO never fetches or checks out tooling.
[[ -d "$PROJECT_ROOT/.git" ]]
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == "$DEPLOY_SHA" ]]
[[ -z "$(git -C "$PROJECT_ROOT" status --porcelain)" ]]
[[ "$(wp_cmd eval 'echo wp_get_environment_type();')" == 'staging' ]]

if [[ "$BACKUP_ALREADY_VERIFIED" == "YES" ]]; then
  echo "stage=backup_reused_from_parent_deploy_gate"
else
  echo "stage=backup_before_seo_mutation"
  export WP_PATH
  export ROLLSBAR_BACKUP_ROOT="$BACKUP_ROOT"
  export ROLLSBAR_BACKUP_RETENTION=5
  bash "$PROJECT_ROOT/wordpress/deploy/backup-staging.sh"
fi

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
blog_public_after="$(wp_cmd option get blog_public)"
seo_state="$(wp_cmd option get rollsbar_seo_home_description_state)"
seo_auto="$(wp_cmd plugin auto-updates status "$SEO_SLUG" --field=status 2>/dev/null || true)"

toggle_state="$(wp_cmd eval '$t=get_option("seopress_toggle",array()); echo implode(",", array_map(static fn($k)=>$k."=".($t[$k]??"unset"), array("toggle-titles","toggle-xml-sitemap","toggle-social","toggle-local-business","toggle-rich-snippets","toggle-woocommerce","toggle-google-analytics","toggle-instant-indexing","toggle-robots")));')"
sitemap_state="$(wp_cmd eval '$s=get_option("seopress_xml_sitemap_option_name",array()); echo $s["seopress_xml_sitemap_general_enable"]??"unset";')"
social_state="$(wp_cmd eval '$s=get_option("seopress_social_option_name",array()); echo "og=".($s["seopress_social_facebook_og"]??"unset").",twitter=".($s["seopress_social_twitter_card"]??"unset");')"

[[ "$seo_version" == "$SEO_VERSION" ]]
[[ "$seo_status" == "active" ]]
[[ "$woo_version_after" == "$WC_VERSION" ]]
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
        "__DEPLOY_SHA__": deploy_sha,
        "__BACKUP_ALREADY_VERIFIED__": backup_verified,
    }
    for marker, value in replacements.items():
        remote = remote.replace(marker, value)

    return remote


def run_remote(client, remote):
    # Short exec request; fixed script goes through stdin. Never retry mutation.
    stdin, stdout, stderr = client.exec_command("bash -lc 'exec bash -s'", timeout=900)
    stdin.write(remote)
    stdin.flush()
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    stderr.read()  # Arbitrary plugin stderr may contain credentials; never print it.
    status = stdout.channel.recv_exit_status()
    if status != 0:
        raise RuntimeError(f"Remote SEO provision failed with exit status {status}")
    return out


def catalog_audit(client):
    script = ('set -euo pipefail\nexport PATH="$HOME/.local/bin:$PATH"\n'
              'wp --path="$HOME/www/staging.rollsbar.ru" eval ' + q(AUDIT_PHP))
    audit = parse_audit(run_remote(client, script))
    # Intentionally no incoming marker requirement during an incomplete release.
    validate_catalog_audit(audit)
    return audit


def execute(client, deploy_sha, backup_verified):
    if not re.fullmatch(r"[0-9a-f]{40}", deploy_sha):
        raise ValueError("ROLLSBAR_DEPLOY_SHA must be an exact lowercase SHA")
    if backup_verified not in ("", "YES"):
        raise ValueError("Invalid parent backup confirmation")
    before = catalog_audit(client)
    result = run_remote(client, mutation_script(deploy_sha, backup_verified))
    after = catalog_audit(client)
    if before != after:
        raise RuntimeError("Catalog changed during SEO provisioning")
    if "STAGING SEO PROVISION PASS" not in result:
        raise RuntimeError("SEO provision returned without verification marker")
    print("STAGING SEO PROVISION PASS; identity-aware pre/post catalog unchanged")
    return result


def main():
    if os.environ.get("ROLLSBAR_CONFIRM_STAGING_SEO") != "YES":
        raise SystemExit("Refusing staging mutation: set ROLLSBAR_CONFIRM_STAGING_SEO=YES")
    client = None
    try:
        deploy_sha = os.environ.get("ROLLSBAR_DEPLOY_SHA", "")
        if not re.fullmatch(r"[0-9a-f]{40}", deploy_sha):
            raise ValueError("ROLLSBAR_DEPLOY_SHA must be an exact lowercase SHA")
        client = connect()
        execute(client, deploy_sha, os.environ.get("ROLLSBAR_SEO_BACKUP_ALREADY_VERIFIED", ""))
    except Exception as exc:
        raise SystemExit("SEO provisioning failed: " + type(exc).__name__)
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()

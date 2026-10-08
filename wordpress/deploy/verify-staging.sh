#!/usr/bin/env bash
set -euo pipefail

: "${WP_PATH:?Set WP_PATH}"
: "${STAGING_URL:?Set STAGING_URL}"

WP_VERSION="7.1.3"
WC_VERSION="11.1.2"
fail=0

wp_cmd(){ wp --path="$WP_PATH" "$@"; }
ok(){ printf 'PASS  %s\n' "$*"; }
warn(){ printf 'WARN  %s\n' "$*"; }
bad(){ printf 'FAIL  %s\n' "$*"; fail=1; }

[[ "$(wp_cmd core version)" == "$WP_VERSION" ]] && ok "WordPress $WP_VERSION" || bad "WordPress version mismatch"
[[ "$(wp_cmd plugin get woocommerce --field=version)" == "$WC_VERSION" ]] && ok "WooCommerce $WC_VERSION" || bad "WooCommerce version mismatch"
wp_cmd plugin is-active rollsbar-core && ok "rollsbar-core active" || bad "rollsbar-core inactive"
wp_cmd theme is-active rollsbar-theme && ok "rollsbar-theme active" || bad "rollsbar-theme inactive"

env_type="$(wp_cmd eval 'echo wp_get_environment_type();')"
[[ "$env_type" == "staging" ]] && ok "WP_ENVIRONMENT_TYPE=staging" || bad "environment type is $env_type"

[[ "$(wp_cmd option get blog_public)" == "0" ]] && ok "search indexing disabled" || bad "blog_public must be 0 on staging"
[[ "$(wp_cmd option get home)" == "$STAGING_URL" ]] && ok "home URL matches staging" || bad "home URL mismatch"
[[ "$(wp_cmd option get siteurl)" == "$STAGING_URL" ]] && ok "siteurl matches staging" || bad "siteurl mismatch"

wp_cmd rollsbar catalog validate >/dev/null && ok "catalog JSON validates" || bad "catalog validation failed"

parents="$(wp_cmd post list --post_type=product --post_status=publish --format=count)"
if [[ "$parents" -eq 5 ]]; then
  ok "5-card smoke import present"
elif [[ "$parents" -eq 118 ]]; then
  ok "full 118-card catalog already imported"
else
  warn "published product count is $parents (expected 5 during smoke or 118 after promotion)"
fi

for page in cart checkout myaccount; do
  id="$(wp_cmd eval "echo function_exists('wc_get_page_id') ? wc_get_page_id('$page') : -1;")"
  if [[ "$id" =~ ^[0-9]+$ ]] && (( id > 0 )); then
    ok "WooCommerce $page page exists: $id"
  else
    bad "WooCommerce $page page missing"
  fi
done

if command -v curl >/dev/null 2>&1; then
  code="$(curl -L -sS -o /dev/null -w '%{http_code}' "$STAGING_URL/" || true)"
  if [[ "$code" =~ ^[23][0-9][0-9]$ ]]; then
    ok "HTTP home response: $code"
  else
    warn "home HTTP response: $code"
  fi
fi

echo
if (( fail )); then
  echo "STAGING STATIC VERIFY FAILED"
  exit 1
fi

echo "STAGING STATIC VERIFY PASS"
echo "Next gate is browser/order integration testing; this script alone is not Gate B acceptance."

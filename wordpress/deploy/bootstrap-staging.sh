#!/usr/bin/env bash
set -euo pipefail

WP_VERSION="7.1.3"
WC_VERSION="11.1.2"

: "${WP_PATH:?Set WP_PATH}"
: "${PROJECT_ROOT:?Set PROJECT_ROOT}"
: "${STAGING_URL:?Set STAGING_URL}"
: "${WP_ADMIN_USER:?Set WP_ADMIN_USER}"
: "${WP_ADMIN_EMAIL:?Set WP_ADMIN_EMAIL}"

WP_LOCALE="${WP_LOCALE:-ru_RU}"
WP_TITLE="${WP_TITLE:-Rolls Bar — Staging}"
ROLLSBAR_IMPORT_SMOKE="${ROLLSBAR_IMPORT_SMOKE:-1}"

# Once the public staging certificate exists, HTTPS is a permanent staging
# invariant. Older orchestrators may still pass the historical HTTP URL; do
# not allow a routine redeploy to downgrade WordPress home/siteurl again.
if [[ "$STAGING_URL" == "http://staging.rollsbar.ru" || "$STAGING_URL" == "http://staging.rollsbar.ru/" ]]; then
  STAGING_URL="https://staging.rollsbar.ru"
fi

wp_cmd(){ wp --path="$WP_PATH" "$@"; }

if ! command -v wp >/dev/null 2>&1; then
  echo "WP-CLI is required for this path. Use REG.RU panel/ZIP fallback instead."
  exit 2
fi

mkdir -p "$WP_PATH"

if [[ ! -f "$WP_PATH/wp-load.php" ]]; then
  : "${DB_NAME:?Set DB_NAME for a fresh install}"
  : "${DB_USER:?Set DB_USER for a fresh install}"
  DB_HOST="${DB_HOST:-localhost}"

  if [[ -z "${DB_PASSWORD:-}" ]]; then
    read -rsp "MySQL password: " DB_PASSWORD
    echo
  fi

  echo "Downloading canonical WordPress $WP_VERSION core..."
  wp core download --path="$WP_PATH" --version="$WP_VERSION" --locale=en_US --force

  printf '%s\n' "$DB_PASSWORD" | wp config create --path="$WP_PATH" --dbname="$DB_NAME" --dbuser="$DB_USER" --dbhost="$DB_HOST" --skip-check --prompt=dbpass
  unset DB_PASSWORD

  if [[ -z "${WP_ADMIN_PASSWORD:-}" ]]; then
    read -rsp "Temporary staging WordPress admin password: " WP_ADMIN_PASSWORD
    echo
  fi

  printf '%s\n' "$WP_ADMIN_PASSWORD" | wp core install --path="$WP_PATH" --url="$STAGING_URL" --title="$WP_TITLE" --admin_user="$WP_ADMIN_USER" --admin_email="$WP_ADMIN_EMAIL" --locale=en_US --skip-email --prompt=admin_password
  unset WP_ADMIN_PASSWORD

  if [[ "$WP_LOCALE" != "en_US" ]]; then
    echo "Installing WordPress language pack: $WP_LOCALE"
    wp_cmd language core install "$WP_LOCALE" --activate
    wp_cmd site switch-language "$WP_LOCALE"
  fi
else
  echo "Existing WordPress detected; core download/install skipped."
fi

actual_core="$(wp_cmd core version)"
if [[ "$actual_core" != "$WP_VERSION" ]]; then
  echo "Expected WordPress $WP_VERSION, got $actual_core"
  exit 3
fi

wp_cmd config set WP_ENVIRONMENT_TYPE staging --type=constant
wp_cmd config set DISALLOW_FILE_EDIT true --raw
wp_cmd config set WP_DEBUG true --raw
wp_cmd config set WP_DEBUG_LOG true --raw
wp_cmd config set WP_DEBUG_DISPLAY false --raw
wp_cmd config set FORCE_SSL_ADMIN true --raw

wp_cmd option update home "$STAGING_URL"
wp_cmd option update siteurl "$STAGING_URL"
wp_cmd option update blog_public 0
wp_cmd option update permalink_structure '/%postname%/'
wp_cmd rewrite flush --hard

# REG.RU's Apache setup did not create .htaccess on the first WP-CLI hard
# flush. Ensure the standard WordPress front-controller rules exist so Woo
# pages such as /cart/ and /checkout/ do not become Apache 404s.
if [[ ! -f "$WP_PATH/.htaccess" ]] || ! grep -q 'RewriteEngine On' "$WP_PATH/.htaccess"; then
  cat > "$WP_PATH/.htaccess" <<'HTACCESS'
# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
HTACCESS
  chmod 0644 "$WP_PATH/.htaccess"
fi

if wp_cmd plugin is-installed woocommerce; then
  wp_cmd plugin update woocommerce --version="$WC_VERSION"
else
  wp_cmd plugin install woocommerce --version="$WC_VERSION"
fi
wp_cmd plugin activate woocommerce

# Rolls Bar prices are ruble-denominated integer menu prices. A fresh
# WooCommerce install defaults to USD; enforce the project currency so staging
# cannot silently render approved prices as dollars.
wp_cmd option update woocommerce_currency 'RUB'
wp_cmd option update woocommerce_currency_pos 'right_space'
wp_cmd option update woocommerce_price_num_decimals '0'
wp_cmd option update woocommerce_price_decimal_sep ','
wp_cmd option update woocommerce_price_thousand_sep ' '

theme_src="$PROJECT_ROOT/wordpress/wp-content/themes/rollsbar-theme"
plugin_src="$PROJECT_ROOT/wordpress/wp-content/plugins/rollsbar-core"
theme_dst="$WP_PATH/wp-content/themes/rollsbar-theme"
plugin_dst="$WP_PATH/wp-content/plugins/rollsbar-core"

rm -rf "$theme_dst" "$plugin_dst"

if command -v rsync >/dev/null 2>&1; then
  mkdir -p "$theme_dst" "$plugin_dst"
  rsync -a --delete "$theme_src/" "$theme_dst/"
  rsync -a --delete "$plugin_src/" "$plugin_dst/"
else
  cp -a "$theme_src" "$theme_dst"
  cp -a "$plugin_src" "$plugin_dst"
fi

mkdir -p "$plugin_dst/data"
cp "$PROJECT_ROOT/wordpress/data/catalog.json" "$plugin_dst/data/catalog.json"

wp_cmd theme activate rollsbar-theme
wp_cmd plugin activate rollsbar-core
wp_cmd rollsbar catalog validate

# Configure WooCommerce's modern Checkout Block Local Pickup, not the legacy
# shipping-zone method. The pickup address is seeded from Rolls Bar's existing
# editable business settings, so the deployment does not invent a second
# address source. Exact client-facing details remain editable in wp-admin.
wp_cmd eval '
$rb = get_option( "rollsbar_settings", array() );
$defaults = class_exists( "RollsBar_Settings" ) ? RollsBar_Settings::defaults() : array();
$address = trim( (string) ( $rb["address"] ?? $defaults["address"] ?? "" ) );
$city = trim( (string) ( $rb["city"] ?? $defaults["city"] ?? "" ) );
if ( "" === $address || "" === $city ) {
    fwrite( STDERR, "Rolls Bar city/address are required for staging Local Pickup.\n" );
    exit( 1 );
}
update_option( "woocommerce_store_address", $address );
update_option( "woocommerce_store_city", $city );
update_option( "woocommerce_default_country", "RU" );
update_option(
    "woocommerce_pickup_location_settings",
    array(
        "enabled"    => "yes",
        "title"      => "Самовывоз",
        "cost"       => "",
        "tax_status" => "none",
    )
);
update_option(
    "pickup_location_pickup_locations",
    array(
        array(
            "name"    => "Rolls Bar",
            "address" => array(
                "address_1" => $address,
                "city"      => $city,
                "state"     => "",
                "postcode"  => "",
                "country"   => "RU",
            ),
            "details" => "",
            "enabled" => true,
        ),
    )
);
'

if [[ "$ROLLSBAR_IMPORT_SMOKE" == "1" ]]; then
  echo "Importing first 5 product cards for Gate B smoke..."
  wp_cmd rollsbar catalog import --limit=5
fi

# Final invariants: fail the deploy if a later change regresses staging HTTPS,
# pretty permalinks, ruble currency, or native Blocks Local Pickup.
[[ "$(wp_cmd option get home)" == "$STAGING_URL" ]]
[[ "$(wp_cmd option get siteurl)" == "$STAGING_URL" ]]
force_ssl="$(wp_cmd config get FORCE_SSL_ADMIN)"
[[ "$force_ssl" == "true" || "$force_ssl" == "1" ]]
grep -q 'RewriteEngine On' "$WP_PATH/.htaccess"
[[ "$(wp_cmd option get woocommerce_currency)" == "RUB" ]]
[[ "$(wp_cmd option get woocommerce_price_num_decimals)" == "0" ]]
[[ "$(wp_cmd eval '$s=get_option("woocommerce_pickup_location_settings",array()); echo $s["enabled"] ?? "no";')" == "yes" ]]
[[ "$(wp_cmd eval '$l=get_option("pickup_location_pickup_locations",array()); echo count(array_filter($l,static fn($x)=>!empty($x["enabled"])));')" -ge 1 ]]

echo
echo "BOOTSTRAP COMPLETE"
echo "Staging URL: $STAGING_URL"
echo "WordPress: $(wp_cmd core version)"
echo "WooCommerce: $(wp_cmd plugin get woocommerce --field=version)"
echo "Currency: $(wp_cmd option get woocommerce_currency)"
echo "Local Pickup: enabled"
echo
echo "Next: bash wordpress/deploy/verify-staging.sh"
echo "Do NOT enable live payments, real Telegram credentials, or production indexing yet."

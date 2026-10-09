#!/usr/bin/env bash
set -euo pipefail

: "${WP_PATH:?Set WP_PATH}"

BACKUP_ROOT="${ROLLSBAR_BACKUP_ROOT:-$HOME/rollsbar-backups/staging}"
RETENTION="${ROLLSBAR_BACKUP_RETENTION:-5}"
TIMESTAMP="$(date -u +'%Y%m%dT%H%M%SZ')"
SNAPSHOT="$BACKUP_ROOT/$TIMESTAMP"
TMP="$BACKUP_ROOT/.tmp-$TIMESTAMP-$$"
SNAPSHOT_GLOB='20??????T??????Z'

if ! command -v wp >/dev/null 2>&1; then
  echo "BACKUP FAIL: WP-CLI unavailable"
  exit 2
fi
if [[ ! -f "$WP_PATH/wp-load.php" ]]; then
  echo "BACKUP FAIL: WordPress installation missing"
  exit 2
fi
if ! [[ "$RETENTION" =~ ^[1-9][0-9]*$ ]]; then
  echo "BACKUP FAIL: retention must be a positive integer"
  exit 2
fi

umask 077
mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT" || true
rm -rf "$TMP"
mkdir -p "$TMP"
cleanup(){ rm -rf "$TMP"; }
trap cleanup EXIT

wp_cmd(){ wp --path="$WP_PATH" "$@"; }

echo "backup_target=staging"
echo "backup_timestamp=$TIMESTAMP"
echo "backup_location=$SNAPSHOT"

# Export directly to gzip so an uncompressed SQL file containing customer/order
# data never remains on disk. WP-CLI reads DB credentials from wp-config.php.
wp_cmd db export - --single-transaction --quick --skip-lock-tables 2>"$TMP/db-export.stderr" | gzip -9 >"$TMP/database.sql.gz"
if [[ ! -s "$TMP/database.sql.gz" ]]; then
  echo "BACKUP FAIL: database archive is empty"
  exit 3
fi
gzip -t "$TMP/database.sql.gz"

# Uploads are the main non-Git filesystem state. Project theme/plugin code is
# canonical in Git; WordPress core/WooCommerce are reproducible from official
# packages, so we avoid duplicating executable code and wp-config secrets here.
mkdir -p "$WP_PATH/wp-content/uploads"
tar -C "$WP_PATH/wp-content" -czf "$TMP/uploads.tar.gz" uploads
if [[ ! -s "$TMP/uploads.tar.gz" ]]; then
  echo "BACKUP FAIL: uploads archive is empty"
  exit 3
fi
tar -tzf "$TMP/uploads.tar.gz" >/dev/null

{
  echo "rollsbar_backup_format=1"
  echo "created_utc=$TIMESTAMP"
  echo "site_url=$(wp_cmd option get home)"
  echo "wordpress_version=$(wp_cmd core version)"
  echo "woocommerce_version=$(wp_cmd plugin get woocommerce --field=version 2>/dev/null || echo unavailable)"
  echo "published_products=$(wp_cmd post list --post_type=product --post_status=publish --format=count)"
  echo "blog_public=$(wp_cmd option get blog_public)"
  echo "database_archive=database.sql.gz"
  echo "uploads_archive=uploads.tar.gz"
  echo "wp_config_included=no"
  echo "project_code_source=GitHub:tilaninishi12754-code/rollsbar"
} >"$TMP/manifest.txt"

(
  cd "$TMP"
  sha256sum database.sql.gz uploads.tar.gz manifest.txt >SHA256SUMS
  sha256sum -c SHA256SUMS
)

# Do not keep stderr if export succeeded; it may contain harmless server notes
# but is unnecessary for recovery.
rm -f "$TMP/db-export.stderr"
chmod 600 "$TMP"/*
chmod 700 "$TMP"

# Atomic publish: an incomplete temp directory is never presented as a valid
# snapshot. Because timestamp names are unique under normal operation, refuse
# accidental overwrite rather than merging snapshots.
if [[ -e "$SNAPSHOT" ]]; then
  echo "BACKUP FAIL: snapshot already exists: $SNAPSHOT"
  exit 4
fi
mv "$TMP" "$SNAPSHOT"
trap - EXIT

# Keep newest N complete snapshots. Never delete dot-prefixed temporary dirs
# here; a future audit can diagnose them separately if a process was killed.
mapfile -t old_snapshots < <(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name "$SNAPSHOT_GLOB" -printf '%f\n' | sort -r | tail -n +$((RETENTION + 1)))
for old in "${old_snapshots[@]:-}"; do
  [[ -n "$old" ]] || continue
  rm -rf -- "$BACKUP_ROOT/$old"
done

size_db="$(stat -c '%s' "$SNAPSHOT/database.sql.gz")"
size_uploads="$(stat -c '%s' "$SNAPSHOT/uploads.tar.gz")"
count="$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name "$SNAPSHOT_GLOB" | wc -l | tr -d ' ')"

echo "database_gzip_bytes=$size_db"
echo "uploads_gzip_bytes=$size_uploads"
echo "retained_snapshots=$count"
echo "BACKUP VERIFIED PASS"

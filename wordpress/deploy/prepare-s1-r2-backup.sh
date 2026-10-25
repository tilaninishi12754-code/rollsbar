#!/usr/bin/env bash
# Source from the exact release before bootstrap. No credentials in this receipt.
set -euo pipefail
: "${WP_PATH:?}"
: "${PROJECT_ROOT:?}"
export ROLLSBAR_BACKUP_ROOT="$HOME/rollsbar-backups/staging"
export ROLLSBAR_BACKUP_RETENTION=6
export ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT=20261023T215945Z
[[ "$(realpath "$WP_PATH")" == "$(realpath "$HOME/www/staging.rollsbar.ru")" ]]
backup_root="$(realpath "$ROLLSBAR_BACKUP_ROOT")"
[[ "$backup_root" != "$(realpath "$HOME/www")"/* ]]
[[ "$backup_root" != "$(realpath "$HOME/www")" ]]
[[ "$(wp --path="$WP_PATH" option get home)" == 'https://staging.rollsbar.ru' ]]
[[ "$(wp --path="$WP_PATH" option get siteurl)" == 'https://staging.rollsbar.ru' ]]
[[ "$(wp --path="$WP_PATH" option get blog_public)" == '0' ]]
[[ "$(wp --path="$WP_PATH" eval 'echo wp_get_environment_type();')" == 'staging' ]]
[[ "$(wp --path="$WP_PATH" core version)" == '7.1.3' ]]
[[ "$(wp --path="$WP_PATH" plugin get woocommerce --field=version)" == '11.1.2' ]]

verify_snapshot(){
  local snapshot="$ROLLSBAR_BACKUP_ROOT/$1"
  [[ -d "$snapshot" && ! -L "$snapshot" ]]
  [[ -s "$snapshot/database.sql.gz" && -s "$snapshot/uploads.tar.gz" && -s "$snapshot/manifest.txt" ]]
  (cd "$snapshot"; sha256sum -c SHA256SUMS; gzip -t database.sql.gz; tar -tzf uploads.tar.gz >/dev/null)
  grep -qx 'site_url=https://staging.rollsbar.ru' "$snapshot/manifest.txt"
  grep -qx 'database_archive=database.sql.gz' "$snapshot/manifest.txt"
  grep -qx 'uploads_archive=uploads.tar.gz' "$snapshot/manifest.txt"
}
verify_snapshot "$ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT"
echo 's1_historical_snapshot_before=20261023T215945Z:PASS'
echo "deployed_marker_before=$(cat "$HOME/.rollsbar-staging-deployed-sha")"
echo 'deploy_stage=backup_before_mutation'
if ! backup_receipt="$(bash "$PROJECT_ROOT/wordpress/deploy/backup-staging.sh")"; then
  printf '%s\n' "$backup_receipt"
  echo 'S1-R2 BLOCKED: fresh backup failed; bootstrap/repair not started'
  exit 1
fi
printf '%s\n' "$backup_receipt"
grep -qx 'BACKUP VERIFIED PASS' <<<"$backup_receipt"
ROLLSBAR_FRESH_BACKUP_SNAPSHOT="$(sed -n 's/^backup_timestamp=//p' <<<"$backup_receipt")"
[[ "$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" =~ ^20[0-9]{6}T[0-9]{6}Z$ ]]
[[ "$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" != "$ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT" ]]
verify_snapshot "$ROLLSBAR_FRESH_BACKUP_SNAPSHOT"
grep -qx "created_utc=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" "$ROLLSBAR_BACKUP_ROOT/$ROLLSBAR_FRESH_BACKUP_SNAPSHOT/manifest.txt"
verify_snapshot "$ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT"
export ROLLSBAR_FRESH_BACKUP_SNAPSHOT
export ROLLSBAR_FRESH_BACKUP_VERIFIED=YES
echo 's1_historical_snapshot_after=20261023T215945Z:PASS'
echo 's1_r2_new_backup_db_uploads_manifest_checksums_archives_outside_webroot=PASS'

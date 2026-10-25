#!/usr/bin/env bash
set -euo pipefail

: "${WP_PATH:?Set WP_PATH}"

BACKUP_ROOT="${ROLLSBAR_BACKUP_ROOT:-$HOME/rollsbar-backups/staging}"
RETENTION="${ROLLSBAR_BACKUP_RETENTION:-5}"
DEPLOYED_SHA_MARKER="${ROLLSBAR_DEPLOYED_SHA_MARKER:-$HOME/.rollsbar-staging-deployed-sha}"
TIMESTAMP="$(date -u +'%Y%m%dT%H%M%SZ')"
SNAPSHOT="$BACKUP_ROOT/$TIMESTAMP"
TMP="$BACKUP_ROOT/.tmp-$TIMESTAMP-$$"
SNAPSHOT_GLOB='20??????T??????Z'
PRESERVE_SNAPSHOT="${ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT:-}"
if ! [[ "$RETENTION" =~ ^[1-9][0-9]*$ && ${#RETENTION} -le 18 ]]; then
  echo "BACKUP FAIL: retention must be a positive safely representable integer"
  exit 2
fi

# An explicitly protected recovery point must survive the next retention pass.
# It occupies one retained slot; at least one rolling slot must remain.
if [[ -n "$PRESERVE_SNAPSHOT" ]]; then
  [[ "$PRESERVE_SNAPSHOT" =~ ^20[0-9]{6}T[0-9]{6}Z$ ]] || exit 2
  [[ -d "$BACKUP_ROOT/$PRESERVE_SNAPSHOT" && ! -L "$BACKUP_ROOT/$PRESERVE_SNAPSHOT" ]] || { echo 'BACKUP FAIL: protected snapshot missing or linked'; exit 2; }
  if (( RETENTION < 2 )); then
    echo 'BACKUP FAIL: protected snapshot requires retention of at least 2'
    exit 2
  fi
fi

if ! command -v wp >/dev/null 2>&1; then
  echo "BACKUP FAIL: WP-CLI unavailable"
  exit 2
fi
if [[ ! -f "$WP_PATH/wp-load.php" ]]; then
  echo "BACKUP FAIL: WordPress installation missing"
  exit 2
fi
# A recovery-safe snapshot must identify the code that is actually serving at
# the instant the pre-deploy backup is created. The marker is written only after
# a complete live staging deploy + HTTP hardening passes. Never substitute the
# incoming deployment SHA here: that revision has not yet been applied.
if [[ ! -f "$DEPLOYED_SHA_MARKER" ]]; then
  echo "BACKUP FAIL: verified deployed-SHA marker is missing"
  exit 2
fi
PROJECT_COMMIT="$(tr -d '[:space:]' < "$DEPLOYED_SHA_MARKER")"
if [[ -z "$PROJECT_COMMIT" || ! "$PROJECT_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]]; then
  echo "BACKUP FAIL: deployed-SHA marker is invalid"
  exit 2
fi
PROJECT_COMMIT="${PROJECT_COMMIT,,}"
marker_mode="$(stat -c '%a' "$DEPLOYED_SHA_MARKER")"
if [[ "$marker_mode" != "600" ]]; then
  echo "BACKUP FAIL: deployed-SHA marker must have mode 600"
  exit 2
fi

umask 077
mkdir -p "$BACKUP_ROOT"
[[ ! -L "$BACKUP_ROOT" ]] || { echo 'BACKUP FAIL: linked backup root'; exit 2; }
BACKUP_ROOT="$(realpath "$BACKUP_ROOT")"
SNAPSHOT="$BACKUP_ROOT/$TIMESTAMP"
TMP="$BACKUP_ROOT/.tmp-$TIMESTAMP-$$"
chmod 700 "$BACKUP_ROOT" || true
# Serialize cooperating writers, including export/publish/rotation. mkdir is
# atomic and needs no additional runtime package. An abandoned lock fails closed.
LOCK_DIR="$BACKUP_ROOT/.backup-staging.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo 'BACKUP FAIL: backup already running or abandoned lock requires review'
  exit 4
fi
TMP_CREATED=0
cleanup(){ if (( TMP_CREATED )); then rm -rf -- "$TMP"; fi; rmdir -- "$LOCK_DIR"; }
trap cleanup EXIT
[[ ! -e "$SNAPSHOT" ]] || { echo 'BACKUP FAIL: snapshot already exists'; exit 4; }
mkdir "$TMP"
TMP_CREATED=1

snapshot_complete(){
  local path="$BACKUP_ROOT/$1"
  [[ "$1" =~ ^20[0-9]{6}T[0-9]{6}Z$ && -d "$path" && ! -L "$path" &&
     "$(realpath "$path")" == "$path" &&
     -s "$path/database.sql.gz" && -s "$path/uploads.tar.gz" &&
     -s "$path/manifest.txt" && -s "$path/SHA256SUMS" ]]
}
complete_snapshots(){
  local names name
  names="$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name "$SNAPSHOT_GLOB" -printf '%f\n')" || return
  while IFS= read -r name; do
    if snapshot_complete "$name"; then printf '%s\n' "$name"; fi
  done <<<"$names"
}
if [[ -n "$PRESERVE_SNAPSHOT" ]]; then
  snapshot_complete "$PRESERVE_SNAPSHOT" || { echo 'BACKUP FAIL: protected snapshot incomplete'; exit 2; }
fi

wp_cmd(){ wp --path="$WP_PATH" "$@"; }

echo "backup_target=staging"
echo "backup_timestamp=$TIMESTAMP"
echo "backup_location=$SNAPSHOT"
echo "backup_project_commit=$PROJECT_COMMIT"
echo "backup_project_commit_source=verified_deployed_marker"

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

# Collect metadata with checked command status: echo "$(failing-command)" would
# otherwise publish a checksummed but incomplete manifest and then rotate.
site_url="$(wp_cmd option get home)"
wordpress_version="$(wp_cmd core version)"
woocommerce_version="$(wp_cmd plugin get woocommerce --field=version 2>/dev/null || echo unavailable)"
published_products="$(wp_cmd post list --post_type=product --post_status=publish --format=count)"
blog_public="$(wp_cmd option get blog_public)"
[[ -n "$site_url" && -n "$wordpress_version" && -n "$woocommerce_version" &&
   "$published_products" =~ ^[0-9]+$ && "$blog_public" =~ ^[01]$ ]] || { echo 'BACKUP FAIL: invalid manifest metadata'; exit 3; }
{
  echo "rollsbar_backup_format=3"
  echo "created_utc=$TIMESTAMP"
  echo "site_url=$site_url"
  echo "wordpress_version=$wordpress_version"
  echo "woocommerce_version=$woocommerce_version"
  echo "published_products=$published_products"
  echo "blog_public=$blog_public"
  echo "database_archive=database.sql.gz"
  echo "uploads_archive=uploads.tar.gz"
  echo "wp_config_included=no"
  echo "project_code_source=GitHub:tilaninishi12754-code/rollsbar"
  echo "project_code_commit=$PROJECT_COMMIT"
  echo "project_code_commit_source=verified_deployed_marker"
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
mv -T -- "$TMP" "$SNAPSHOT"
TMP_CREATED=0

# Only after verification and atomic publish, reserve the protected slot and
# retain the newest N-1 ordinary complete snapshots (or newest N without it).
# Unknown, incomplete, linked and dot-prefixed directories are never victims.
listing="$(complete_snapshots | LC_ALL=C sort -r)"
snapshots=()
[[ -z "$listing" ]] || mapfile -t snapshots <<<"$listing"
rolling_slots=$((RETENTION - ( ${#PRESERVE_SNAPSHOT} > 0 ? 1 : 0 )))
ordinary=0
old_snapshots=()
for name in "${snapshots[@]}"; do
  [[ -z "$PRESERVE_SNAPSHOT" || "$name" != "$PRESERVE_SNAPSHOT" ]] || continue
  ordinary=$((ordinary + 1))
  if (( ordinary > rolling_slots )); then old_snapshots+=("$name"); fi
done
# Validate the entire plan before the first deletion, including fresh survival
# if clock skew or an uncooperative writer introduced newer snapshot names.
snapshot_complete "$TIMESTAMP" || { echo 'BACKUP FAIL: published snapshot changed; no eviction performed'; exit 4; }
if [[ -n "$PRESERVE_SNAPSHOT" ]]; then
  snapshot_complete "$PRESERVE_SNAPSHOT" || { echo 'BACKUP FAIL: protected snapshot changed; no eviction performed'; exit 4; }
fi
for old in "${old_snapshots[@]}"; do
  [[ "$old" != "$PRESERVE_SNAPSHOT" && "$old" != "$TIMESTAMP" ]] || { echo 'BACKUP FAIL: unsafe retention victim; no eviction performed'; exit 4; }
  snapshot_complete "$old" || { echo 'BACKUP FAIL: retention candidate changed; no eviction performed'; exit 4; }
done
for old in "${old_snapshots[@]}"; do
  snapshot_complete "$old" || { echo 'BACKUP FAIL: retention candidate changed'; exit 4; }
  [[ "$old" != "$PRESERVE_SNAPSHOT" && "$old" != "$TIMESTAMP" ]] || exit 4
  rm -rf -- "$BACKUP_ROOT/$old"
  echo "rotated_snapshot=$old"
done

size_db="$(stat -c '%s' "$SNAPSHOT/database.sql.gz")"
size_uploads="$(stat -c '%s' "$SNAPSHOT/uploads.tar.gz")"
count="$(complete_snapshots | wc -l | tr -d ' ')"
(( count <= RETENTION )) || { echo 'BACKUP FAIL: concurrent retention count exceeded'; exit 4; }
snapshot_complete "$TIMESTAMP" || exit 4
if [[ -n "$PRESERVE_SNAPSHOT" ]]; then snapshot_complete "$PRESERVE_SNAPSHOT" || exit 4; fi

echo "database_gzip_bytes=$size_db"
echo "uploads_gzip_bytes=$size_uploads"
echo "retained_snapshots=$count"
rmdir -- "$LOCK_DIR"
trap - EXIT
echo "BACKUP VERIFIED PASS"

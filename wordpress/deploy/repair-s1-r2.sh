#!/usr/bin/env bash
set -euo pipefail
: "${WP_PATH:?}"
: "${PROJECT_ROOT:?}"
[[ "${ROLLSBAR_FRESH_BACKUP_VERIFIED:-}" == YES ]]
: "${ROLLSBAR_FRESH_BACKUP_SNAPSHOT:?}"
entry="$PROJECT_ROOT/wordpress/deploy/repair-staging-shrimp-options.php"
echo 'deploy_stage=shrimp_dry_run'
dry="$(ROLLSBAR_SHRIMP_REPAIR_MODE=dry-run wp --path="$WP_PATH" eval-file "$entry")"
printf '%s\n' "$dry"
state="$(printf '%s' "$dry" | php -r '$r=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR); if (($r["source_id"]??"")!=="shrimp-tempura" || ($r["writes"]??-1)!==0) exit(1); echo $r["before_state"];')"
case "$state" in
  missing|empty|pending)
    echo 'deploy_stage=shrimp_options_only_apply'
    ROLLSBAR_SHRIMP_REPAIR_MODE=apply \
      ROLLSBAR_CONFIRM_SHRIMP_OPTIONS=staging:shrimp-tempura:options-only \
      wp --path="$WP_PATH" eval-file "$entry"
    ;;
  canonical) echo 'shrimp_apply=not_needed_canonical_noop' ;;
  *) echo 'REFUSE: unexpected shrimp dry-run state'; exit 1 ;;
esac
post="$(ROLLSBAR_SHRIMP_REPAIR_MODE=dry-run wp --path="$WP_PATH" eval-file "$entry")"
printf '%s\n' "$post"
printf '%s' "$post" | php -r '$r=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR); if (($r["before_state"]??"")!=="canonical" || ($r["writes"]??-1)!==0) exit(1);'
wp --path="$WP_PATH" eval-file "$PROJECT_ROOT/wordpress/deploy/verify-staging-s1-r2.php"
wp --path="$WP_PATH" eval-file "$PROJECT_ROOT/wordpress/deploy/verify-staging-legal-pages.php"
echo 'S1-R2 PRE-MARKER RUNTIME PASS'

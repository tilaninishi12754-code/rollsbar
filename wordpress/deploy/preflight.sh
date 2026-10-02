#!/usr/bin/env bash
set -euo pipefail

WP_PATH="${WP_PATH:-}"
PROJECT_ROOT="${PROJECT_ROOT:-}"
fail=0

ok(){ printf 'PASS  %s\n' "$*"; }
warn(){ printf 'WARN  %s\n' "$*"; }
bad(){ printf 'FAIL  %s\n' "$*"; fail=1; }

command -v php >/dev/null 2>&1 && ok "php: $(php -r 'echo PHP_VERSION;')" || bad "php CLI is unavailable"
command -v wp >/dev/null 2>&1 && ok "WP-CLI: $(wp --version 2>/dev/null)" || bad "WP-CLI is unavailable; use panel/ZIP fallback"
command -v curl >/dev/null 2>&1 && ok "curl available" || warn "curl unavailable"
command -v git >/dev/null 2>&1 && ok "git available" || warn "git unavailable; ZIP deployment still works"
command -v rsync >/dev/null 2>&1 && ok "rsync available" || warn "rsync unavailable; bootstrap will use cp"

if command -v php >/dev/null 2>&1; then
  php -r 'exit(version_compare(PHP_VERSION,"8.1.0",">=")?0:1);' && ok "PHP >= 8.1" || bad "PHP 8.1+ required by rollsbar-core"
  for ext in json mysqli curl mbstring; do
    php -m | grep -qi "^$ext$" && ok "PHP extension: $ext" || warn "PHP extension not visible in CLI: $ext"
  done
fi

if [[ -n "$WP_PATH" ]]; then
  [[ -d "$WP_PATH" ]] && ok "WP_PATH exists: $WP_PATH" || warn "WP_PATH does not exist yet: $WP_PATH"
  parent="$(dirname "$WP_PATH")"
  [[ -w "$parent" ]] && ok "parent directory writable: $parent" || bad "parent directory not writable: $parent"
else
  warn "WP_PATH not set"
fi

if [[ -n "$PROJECT_ROOT" ]]; then
  [[ -f "$PROJECT_ROOT/wordpress/data/catalog.json" ]] && ok "Rolls Bar catalog source found" || bad "catalog source missing"
  [[ -d "$PROJECT_ROOT/wordpress/wp-content/themes/rollsbar-theme" ]] && ok "rollsbar-theme source found" || bad "rollsbar-theme source missing"
  [[ -d "$PROJECT_ROOT/wordpress/wp-content/plugins/rollsbar-core" ]] && ok "rollsbar-core source found" || bad "rollsbar-core source missing"
else
  warn "PROJECT_ROOT not set"
fi

if (( fail )); then
  echo
  echo "PRE-FLIGHT FAILED"
  exit 1
fi

echo
echo "PRE-FLIGHT PASS"

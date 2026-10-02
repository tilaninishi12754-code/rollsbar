#!/usr/bin/env bash
set -euo pipefail

: "${WP_PATH:?Set WP_PATH}"
: "${ROLLSBAR_CONFIRM_FULL_IMPORT:?Set ROLLSBAR_CONFIRM_FULL_IMPORT=YES after the 5-product smoke passes}"

if [[ "$ROLLSBAR_CONFIRM_FULL_IMPORT" != "YES" ]]; then
  echo "Refusing full import. Set ROLLSBAR_CONFIRM_FULL_IMPORT=YES explicitly."
  exit 2
fi

wp_cmd(){ wp --path="$WP_PATH" "$@"; }

wp_cmd rollsbar catalog validate
wp_cmd rollsbar catalog import

count="$(wp_cmd post list --post_type=product --post_status=publish --format=count)"
if [[ "$count" -ne 118 ]]; then
  echo "Full import reconciliation FAILED: expected 118 parent products, got $count"
  exit 1
fi

echo "Full catalog import PASS: 118 parent product cards."

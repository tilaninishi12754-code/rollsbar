# Rolls Bar Staging Deployment Package

Prepared: 2026-10-02

This folder is intentionally credential-free.

## Preferred path: REG.RU Linux hosting + SSH/WP-CLI

1. Create an isolated staging subdomain/document root.
2. Create a separate MySQL database/user for staging.
3. Enable HTTPS.
4. Obtain SSH access.
5. Clone/download the Rolls Bar migration branch outside the public web root when possible.
6. Export the non-secret variables from `staging.env.example`.
7. Run:
   ```bash
   bash wordpress/deploy/preflight.sh
   bash wordpress/deploy/bootstrap-staging.sh
   bash wordpress/deploy/verify-staging.sh
   ```
8. Run Gate B browser/order tests with only 5 product cards.
9. Only after smoke PASS:
   ```bash
   export ROLLSBAR_CONFIRM_FULL_IMPORT=YES
   bash wordpress/deploy/promote-full-catalog.sh
   ```

## Fallback: panel / ZIP installation

If SSH/WP-CLI is unavailable:
- install exact WordPress/WooCommerce versions through the hosting/WordPress panel;
- upload `rollsbar-theme.zip` and `rollsbar-core.zip` from the CI staging bundle;
- activate them;
- keep search indexing off;
- do not manually retype the 118-card catalog.

## Versions pinned for this checkpoint

- WordPress 7.1.2
- WooCommerce 11.1.2
- migration branch: `wordpress/migration-2026-10-01`

Re-verify versions before a later deployment date.

## Never commit

- MySQL passwords
- WordPress admin password
- Telegram bot token / chat ID
- SMTP credentials
- payment gateway credentials
- Yandex Maps API keys

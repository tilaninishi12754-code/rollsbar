# Rolls Bar — WordPress implementation

This directory is the production-oriented WordPress layer for Rolls Bar.

## Architecture

- WordPress + WooCommerce = CMS, products, orders, checkout and admin.
- `rollsbar-theme` = presentation layer only.
- `rollsbar-core` = business logic that must survive theme changes.
- Current GitHub Pages demo remains the UX/reference baseline during migration.

## Rules

1. Never edit WordPress core.
2. Do not put delivery rules, checkout rules, integrations, or order logic into the theme.
3. Use WooCommerce CRUD/APIs rather than direct writes to WooCommerce order tables.
4. Develop and test on staging first.
5. Production deploys require backup + staging verification.
6. Secrets, API keys, passwords and `wp-config.php` never go into Git.
7. Product catalog imports must use stable SKU values.
8. Preserve requirement IDs and project no-loss registry once it is created.

## Target deployment

```
GitHub -> Codex/server workspace -> staging WordPress -> QA -> production WordPress
```

## First server-side actions

1. Create a staging hostname, e.g. `staging.rollsbar.ru`.
2. Install clean WordPress there.
3. Install WooCommerce.
4. Create a dedicated deployment/automation account instead of sharing the owner/admin password.
5. Deploy only this repository's custom theme/plugin code to staging.
6. Import a small test catalog before full catalog migration.

# Rolls Bar — REG.RU Staging Runbook

Date: 2026-10-02
Status: READY BEFORE HOSTING ACCESS / EXECUTION PENDING

## Decision

Create an isolated staging installation before production cutover.

Target placeholder:

`https://staging.<ROLLSBAR_DOMAIN>`

Do not assume the exact production domain until it is confirmed from the REG.RU account.

## Evidence synthesis

### REG.RU official layer
Current REG.RU documentation confirms:
- a subdomain is created in the hosting control panel and, depending on DNS, may also require an A record;
- REG.RU recommends a separate directory for subdomains to reduce confusion;
- SSH is available on Linux virtual hosting except Host-Lite;
- SFTP on virtual hosting is available only to the main hosting account and not Host-Lite/Windows hosting;
- hosting access details are shown under the hosting service's «Доступы» tab;
- REG.RU supports deployment through Git/CI/CD for regular updates.

### WordPress/WooCommerce official layer
Pinned for this checkpoint:
- WordPress 7.1.2 — current stable security release;
- WooCommerce 11.1.2 — current stable release;
- WooCommerce 11.2 remains pre-release at this checkpoint.

WooCommerce recommends staging and testing product/cart/checkout/payment/shipping/email behavior before production.

### Rolls Bar best-fit
Use an isolated subdomain + separate database + exact pinned versions + project-owned theme/plugin + five-product smoke before full catalog.

## What to obtain from REG.RU

Do not send passwords into chat.

Needed facts/screenshots:
1. exact domain;
2. hosting service type/tariff;
3. panel type: ispmanager / cPanel / Plesk;
4. Linux vs Windows;
5. whether tariff is Host-Lite;
6. SSH availability;
7. PHP version;
8. MySQL creation screen;
9. current DNS servers.

Path in account:
`Хостинг → нужная услуга → Управление / Доступы`

## Staging creation

1. Create `staging.<domain>` as an isolated site/document root.
2. Keep it separate from the production root.
3. Verify/add DNS according to the actual nameservers.
4. Enable HTTPS and verify certificate/renewal terms in the account.
5. Create a separate staging MySQL database and user.
6. Never connect staging to the future live WooCommerce database.

## REG.RU access nuance

Preferred deployment is SSH + WP-CLI.

On REG.RU shared hosting, SFTP normally uses the main hosting account; a separate SFTP deploy user may not be available. Do not require a deploy-user that the selected tariff cannot support.

If SSH is unavailable, use the panel + CI ZIP bundle fallback.

## Staging isolation

Before tests:
- `WP_ENVIRONMENT_TYPE=staging`;
- search engine visibility disabled;
- hosting-level password protection when practical;
- no live payment credentials;
- no production Telegram credentials;
- no production customer/order database.

## Automated sequence

```bash
bash wordpress/deploy/preflight.sh
bash wordpress/deploy/bootstrap-staging.sh
bash wordpress/deploy/verify-staging.sh
```

Bootstrap pins:
- WordPress 7.1.2;
- WooCommerce 11.1.2;
- `rollsbar-theme`;
- `rollsbar-core`;
- approved catalog validation;
- first **5 product cards only**.

## Five-product Gate B smoke

Verify:
1. home;
2. simple product;
3. variable product;
4. image and missing-image fallback;
5. add-to-cart;
6. quantity/remove;
7. Checkout Block;
8. +7 behavior;
9. additional address fields;
10. requiredness toggles;
11. WooCommerce order persistence;
12. wp-admin/HPOS;
13. New Order email;
14. Local Pickup;
15. no production side effects;
16. Chromium desktop + WebKit/iPhone browser gate.

## Full catalog promotion

Only after smoke PASS:

```bash
export ROLLSBAR_CONFIRM_FULL_IMPORT=YES
bash wordpress/deploy/promote-full-catalog.sh
```

Reconciliation:
- 118 parent product cards;
- 131 source rows accounting for variants;
- stable SKU mapping;
- no silent duplicates.

## Gate B cannot pass until

- real WordPress staging exists;
- real Checkout Block is rendered;
- a real WooCommerce test order persists;
- test email is delivered;
- Telegram queue/API is verified when credentials are available;
- Local Pickup is verified;
- browser E2E passes against staging;
- client-admin editability is tested;
- no P0/P1 regressions remain;
- backup/rollback exists.

## Production warning

After production starts receiving real orders, never overwrite its database wholesale with an older staging database. Preserve live orders/customers and deploy code/config changes deliberately.

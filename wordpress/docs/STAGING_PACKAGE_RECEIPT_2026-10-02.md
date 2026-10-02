# Rolls Bar — Staging Package Receipt

Date: 2026-10-02
Status: **PACKAGE-OF-RECORD VERIFIED IN CLEAN EPHEMERAL STAGING / REG.RU EXECUTION PENDING**

## Canonical pointers

Migration branch:
`wordpress/migration-2026-10-01`

Approved visual/source baseline:
`a5e524392abcf89ffd5ace2a18218a6b59ed3b61`

Canonical bootstrap rewrite:
`ee7eb4f971869ea637d461371615c380bb44f44b`

Package-of-record source commit:
`bff94b5a4f9278602ced301e2be368e4b1167619`

Smoke-harness-only follow-up:
`75f8a33c59a277ba165c358e5eb1073dec8b0f63`

The smoke follow-up changes the verification workflow, not the staging deploy payload.

## Pinned staging versions

- WordPress 7.1.2
- WooCommerce 11.1.2
- PHP requirement from rollsbar-core: 8.1+
- WooCommerce 11.2 intentionally not used while pre-release at this checkpoint

## Package build evidence

Workflow:
`Build WordPress Staging Package`

Run:
`36961212326`

Result:
**SUCCESS**

Artifact ID:
`11207738345`

GitHub artifact archive SHA-256:
`d2b20ad75508ca32844a798da4bc5b7376a3795e56692b3f995d7b04abdd19b8`

## Exact staging bundle readback

### rollsbar-staging-bundle.zip
SHA-256:
`26c5f2402c8e340daa9a745066fd2eecf515b5398e7b31169d318f291df6a8d8`

ZIP integrity:
**PASS**

### rollsbar-core.zip
SHA-256:
`fb5b1e764ab93b86bfb3f366ebe6848082916397d99d3f93469678dcdc6b3ce3`

ZIP integrity:
**PASS**

Contains:
`rollsbar-core/data/catalog.json`

Fresh packaged catalog readback:
- product cards: 118
- source rows: 131
- approved source commit: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`

### rollsbar-theme.zip
SHA-256:
`871f9efffc9b86f68472307027077b2d19265c695b426f8cc0b67a8da82b09bb`

ZIP integrity:
**PASS**

### manifest.json
SHA-256:
`10e399a94b5d7f2a088bcbf68d19bf72ddaf78d37f7e86c2dce17041d666d838`

Manifest readback:
- git SHA: `bff94b5a4f9278602ced301e2be368e4b1167619`
- environment: staging
- WordPress: 7.1.2
- WooCommerce: 11.1.2
- approved baseline: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`
- catalog cards: 118
- catalog source rows: 131
- secrets included: false

## Static guard evidence

WordPress Migration Static Gate:
run `36961212345`

Result:
**SUCCESS**

Covered:
- PHP syntax
- theme JavaScript
- checkout JavaScript
- Block-native checkout architecture
- post-payment async notification architecture
- catalog invariant 118/131
- deployment shell syntax
- literal-secret scan

## Clean bootstrap evidence

Workflow:
`WordPress Staging Bootstrap Smoke`

Final run:
`36961218015`

Result:
**SUCCESS**

A fresh disposable environment actually performed:

1. MySQL 8 startup.
2. WP-CLI installation.
3. deployment preflight.
4. canonical WordPress 7.1.2 core installation.
5. Russian language pack installed separately from the core archive.
6. WooCommerce 11.1.2 installation/activation.
7. `rollsbar-theme` deployment/activation.
8. `rollsbar-core` deployment/activation.
9. packaged catalog validation.
10. first 5 product-card import.
11. HTTP startup and staging verification.
12. WooCommerce cart/checkout/account page verification.
13. registration of all four Rolls Bar Checkout Block fields.
14. no unsupported Additional Checkout Fields attribute notices.
15. staging safety checks.

## Bugs found by the clean bootstrap and fixed before REG.RU

### 1. Localized WordPress archive assumption
Initial bootstrap attempted a full `7.1.2 ru_RU` core archive and WP-CLI returned `Release not found`.

Fix:
- download canonical 7.1.2 core;
- install `ru_RU` as a language pack;
- switch site language after install.

### 2. Password exposure in CLI arguments
Initial draft passed DB/admin passwords as ordinary command arguments.

Fix:
- passwords are now supplied using WP-CLI prompt input;
- real credentials remain outside Git.

### 3. Unsupported checkout field placeholders
WooCommerce 11.1.2 rejected `placeholder` inside Additional Checkout Field `attributes`.

Fix:
- only supported field attributes are registered;
- clean runtime verification now guards against this WooCommerce API misuse notice.

### 4. Namespace loss in the smoke harness
The first CheckoutFields runtime assertion lost PHP namespaces because of shell escaping.

Fix:
- verification now resolves the WooCommerce service with namespace-safe PHP code.

These failed intermediate runs are retained as audit history; they are not accepted release evidence.

## Bundle contents

- `rollsbar-theme.zip`
- `rollsbar-core.zip`
- `SHA256SUMS`
- `manifest.json`
- `deploy/preflight.sh`
- `deploy/bootstrap-staging.sh`
- `deploy/verify-staging.sh`
- `deploy/promote-full-catalog.sh`
- credential-free `deploy/staging.env.example`
- deployment README

## REG.RU constraints already captured

Runbook accounts for:
- isolated staging subdomain;
- DNS behavior;
- separate document root;
- separate staging database;
- SSH availability on Linux virtual hosting except Host-Lite;
- shared-hosting SFTP main-account limitation;
- panel/ZIP fallback when SSH/WP-CLI is unavailable.

No password/token should be pasted into chat.

## Deployment state

The deployment procedure is now proven in a clean disposable WordPress environment.

It has **not yet been executed on REG.RU**, because the actual hosting account facts/access are still pending.

## FIRST NEXT ACTION

When REG.RU access is available:

1. identify exact domain / tariff / Linux vs Windows / panel / SSH / PHP / DNS;
2. create isolated staging hostname, document root and database;
3. enable HTTPS;
4. run preflight;
5. deploy the exact package-of-record;
6. import only 5 cards;
7. run real Gate B browser/order/email/local-pickup/admin-editability tests;
8. only after Gate B PASS promote to all 118 cards.

Do not switch the production domain or enable live acquiring during this step.

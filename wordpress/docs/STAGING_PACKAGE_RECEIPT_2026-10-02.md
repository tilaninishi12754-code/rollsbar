# Rolls Bar — Staging Package Receipt

Date: 2026-10-02
Status: **READY FOR REG.RU INPUT / NOT DEPLOYED**

## Source

Migration branch:
`wordpress/migration-2026-10-01`

Staging-package source commit:
`f9abc763c24954c1a8b7a7f355a11d9fe253e688`

Latest branch guard commit after secret-scan refinement:
`fe026a9c5bada1e7869f05f416a9113c1cf74035`

Approved visual/source baseline:
`a5e524392abcf89ffd5ace2a18218a6b59ed3b61`

## Pinned staging versions

- WordPress 7.1.2
- WooCommerce 11.1.2
- WooCommerce 11.2 intentionally not used while pre-release

## Build evidence

GitHub Actions workflow:
`Build WordPress Staging Package`

Run:
`36960345717`

Result:
**SUCCESS**

Artifact ID:
`11206833954`

GitHub artifact archive SHA-256:
`0bf57d0fb22dbe6d69138e7504fa222ebbe6dbbf4e79a27f8147940354843bf3`

## Built files

### rollsbar-core.zip
SHA-256:
`d6f4f79183b658da7153dbd4bfe47f3d2b1168fa88c741a2919496f31239da07`

Contains packaged:
`rollsbar-core/data/catalog.json`

Fresh package readback:
- product cards: 118
- source rows: 131
- approved source commit: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`

### rollsbar-theme.zip
SHA-256:
`871f9efffc9b86f68472307027077b2d19265c695b426f8cc0b67a8da82b09bb`

### manifest.json
SHA-256:
`eed8be2a1494c21e0d068640e287554d6a2d23ddd94900bb88170d0a5ea251ed`

Manifest readback:
- environment: staging
- WordPress: 7.1.2
- WooCommerce: 11.1.2
- catalog cards: 118
- catalog rows: 131
- secrets included: false

### rollsbar-staging-bundle.zip
SHA-256:
`ab2e78d3f7b2f4d8ef24b2fe82ee4519455187555f57be7419b45fdaa59525bf`

Bundle contains:
- theme ZIP
- core ZIP
- SHA256SUMS
- manifest
- preflight script
- bootstrap script
- staging verify script
- guarded full-catalog promotion script
- credential-free env example
- deployment README

## Guard evidence

Latest WordPress Migration Static Gate:
Run `36960411777`
Result: **SUCCESS**

Checks:
- PHP syntax
- theme JS
- checkout JS
- Block-native checkout architecture
- post-payment async notification architecture
- catalog invariant 118/131
- deployment shell syntax
- literal-secret scan while allowing runtime `$VARIABLE` references

## REG.RU current constraints captured

Current official REG.RU documentation was re-checked on 2026-10-02.

Runbook accounts for:
- subdomain creation in hosting panel + DNS behavior;
- separate document root preference;
- SSH availability on Linux shared hosting except Host-Lite;
- SFTP on shared hosting using the main hosting account;
- panel fallback if SSH/WP-CLI is unavailable;
- exact service/tariff must be inspected before deployment.

## Deployment state

Not yet executed because hosting account facts are not available.

Needed next:
1. exact domain;
2. hosting tariff/type;
3. ispmanager/cPanel/Plesk;
4. Linux/Windows;
5. Host-Lite yes/no;
6. SSH availability;
7. available PHP version;
8. staging database creation;
9. current DNS nameservers.

No password/token should be pasted into chat.

## FIRST NEXT ACTION

When REG.RU access is available:
1. inspect account facts;
2. create isolated staging subdomain + DB + HTTPS;
3. run preflight;
4. bootstrap exact WP/WC stack;
5. import only 5 cards;
6. run Gate B browser/order smoke;
7. only after PASS promote to all 118 cards.

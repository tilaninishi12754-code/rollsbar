# RollsBar — CURRENT STATE / Project No Loss handoff

Updated: 2026-10-09

## Purpose
This is the current recovery checkpoint for RollsBar. Do not continue from chat memory alone. First read this file, the current override in `wordpress/docs/MIGRATION_PLAN.md`, live branch HEAD, recent CI/runtime evidence, and Todoist task `6hf5v5J535WvjJx5`.

## Source of truth order
1. Live GitHub branch/code + current CI/runtime evidence.
2. `wordpress/docs/MIGRATION_PLAN.md` current execution override.
3. This file / Todoist recovery task / Drive handoff.
4. Historical Git/chat only when provenance is disputed.

Historical detailed checkpoints remain in Git history. This file intentionally summarizes the current verified state rather than duplicating every old checkpoint.

## Git / immutable baseline
Working branch: `wordpress/migration-2026-10-01`.

Latest verified live implementation before this documentation sync:
- security/backup deploy gate: `9a7506c09e3d96a9564afda18465f397f4ebc32e`;
- extension cleanup workflow: `19ec731bf860c1d28241cc5b8d3aac452aafbde8`.

This documentation write advances the branch. **Always re-read live HEAD before any future write.**

Approved baseline is immutable:
`approved/site-2026-10-01 = a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Never modify it.

Default `main` remains infrastructure-only for the address-provider comparison launcher. Last verified HEAD: `af6b829c6c58a072b7bd375af5b8515272c202e7`.

## Live staging — VERIFIED
URL: `https://staging.rollsbar.ru`

Current verified runtime:
- isolated REG.RU staging site/database;
- HTTPS working;
- WordPress 7.1.3;
- WooCommerce 11.1.2;
- `rollsbar-theme` and `rollsbar-core` active;
- full approved catalog preserved: 118 product cards / 131 source rows;
- RUB;
- native WooCommerce Blocks Local Pickup enabled;
- DaData key configured server-side only;
- WooCommerce Coming Soon OFF for anonymous QA;
- `blog_public=0`, search indexing OFF;
- launch payment mode = `Оплата при получении` only;
- online acquiring reserved/disabled and hidden;
- courier polygon enforcement OFF;
- Yandex Metrica code prepared but real counter ID not configured, therefore no Metrica tag loads;
- Telegram staging credentials absent;
- production untouched.

Do not restore the historical 5-product smoke catalog to live staging. Five products are only an isolated CI bootstrap fixture.

## Latest security / backup checkpoint — VERIFIED
### Real staging audit
Read-only security audit implementation: `wordpress/deploy/audit_staging_security_backup.py`.

Latest independent audit is the rerun of workflow `37909036816`, job `113754003039`, and passed after all hardening/cleanup work.

It proves on the real REG.RU staging host:
- WordPress core version = 7.1.3;
- official WordPress core checksums PASS;
- `DISALLOW_FILE_EDIT=true`;
- `FORCE_SSL_ADMIN=true`;
- WordPress automatic updater is not globally disabled;
- WP-Cron is not disabled;
- `wp-config.php` mode = `640`;
- `.htaccess` mode = `644`;
- no world-writable PHP/config files;
- inactive plugins = 0;
- inactive themes = exactly one: `twentytwentyfive` as a bundled fallback theme;
- core updates available = 0;
- WooCommerce is the only plugin with an available newer version, but the project remains intentionally pinned to the tested 11.1.2 until a deliberate staging upgrade cycle;
- database size observed ≈ 5.14 MB;
- uploads size is small and server has ample free space;
- backup directory outside web-root is writable;
- backup snapshot count = 5;
- latest snapshot `20261009T091618Z` independently passed SHA-256/gzip/tar integrity checks;
- direct HTTP probes of `/wp-config.php` and `/.git/config` return HTTP 403.

The many group-writable PHP files on this shared-hosting account are **not** treated as an automatic defect because REG.RU ownership/group semantics can require group write. We did not mass-`chmod` the tree. The sensitive `wp-config.php` was tightened to 640 and both WP-CLI and public HTTP health were proven afterward.

### Core repair / hardening
Workflow `Harden REG.RU Staging Core` run `37909323728`, job `113750376959` — SUCCESS.

Before mutation it created and verified a fresh server-side backup, then:
- re-downloaded the **same pinned WordPress 7.1.3** official package using `--skip-content --force`;
- verified official WordPress checksums;
- changed only `wp-config.php` from 664 to 640;
- verified homepage HTTP 200;
- preserved WooCommerce 11.1.2, 118 products, `blog_public=0`;
- did not update extensions.

### Backup system
Canonical files:
- `wordpress/deploy/backup-staging.sh`;
- `wordpress/deploy/run_staging_backup.py`;
- `.github/workflows/backup-reg-ru-staging.yml`.

Snapshots live outside public web-root under `$HOME/rollsbar-backups/staging/<UTC_TIMESTAMP>/` and contain:
- `database.sql.gz`;
- `uploads.tar.gz`;
- `manifest.txt`;
- `SHA256SUMS`.

Safety properties:
- DB is streamed directly into gzip; no plain SQL dump is intentionally left on disk;
- `wp-config.php`/secrets are not copied into the backup;
- snapshot directories are mode 700, files mode 600;
- snapshot is published atomically only after gzip/tar/SHA-256 verification;
- retention = newest 5 complete snapshots;
- project theme/plugin code remains canonical in Git and WordPress/WooCommerce packages are reproducible.

### Every live staging deploy is now backup-gated
Implementation commit `9a7506c09e3d96a9564afda18465f397f4ebc32e`.

CI/runtime proof on that commit:
- static gate `37909732193` — SUCCESS;
- staging package `37909732076` — SUCCESS;
- clean bootstrap smoke `37909731971` — SUCCESS;
- live REG.RU deploy `37909731997` — SUCCESS.

The real deploy log proves the new order:
1. exact deploy SHA checkout;
2. `deploy_stage=backup_before_mutation`;
3. fresh snapshot `20261009T091218Z` created and verified;
4. only then preflight/bootstrap mutates staging;
5. final core checksum gate;
6. final `wp-config.php=640` assertion;
7. final catalog=118 / WooCommerce=11.1.2 / DaData/runtime assertions PASS.

A failed backup now aborts a routine live staging deploy before mutation.

### Unused extension cleanup
Workflow `Cleanup REG.RU Staging Extensions` run `37910173271`, job `113753155821` — SUCCESS.

It first created verified snapshot `20261009T091618Z` (retained snapshot count = 5), then:
- deleted inactive `akismet`;
- deleted inactive `hello`;
- deleted inactive `twentytwentyfour`;
- deleted inactive `twentytwentythree`;
- kept `twentytwentyfive` as one standard fallback theme for diagnostics;
- confirmed WooCommerce per-plugin auto-update was already disabled and remains disabled;
- did not upgrade WooCommerce;
- verified core checksums, WooCommerce 11.1.2, catalog 118, `wp-config=640`, and home HTTP 200.

The separate read-only audit afterward independently confirmed the cleanup state.

## Checkout / DaData — VERIFIED
Preferred architecture:
`DaData Suggestions -> qc_geo safety gate -> lat/lon -> [approved polygon later] -> delivery tier/minimum`.

25-address live evaluation run `37766333406`:
- 25/25 suggestions returned;
- country metadata `Россия / RU` 25/25;
- non-RU 0/25;
- `qc_geo=0`: 17/25;
- `qc_geo=2`: 5/25;
- `qc_geo=3`: 3/25;
- observed mean latency ~413 ms.

Real anonymous checkout browser smoke run `37775215326`, rerun job `113306962222`:
- exact-house example returns coordinates and `allow_auto_zone=1`;
- lower-precision example is fail-closed with `allow_auto_zone=0` and clarification warning;
- provider country labels are hidden;
- no uncaught checkout JS errors.

Policy:
- `qc_geo=0`: may enter automatic polygon lookup once approved polygons exist;
- `qc_geo>=1`: no silent zone assignment.

Yandex/2GIS are fallback-only. A Yandex Maps key is not a current blocker.

## Delivery polygons — DEFERRED / NON-BLOCKING
Exact polygons are not currently available from the client. This does not block website development.

Already ready:
- thresholds 1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB;
- editable delivery data;
- polygon storage/sanitation;
- point-in-polygon resolver;
- DaData coordinate path;
- fail-closed precision policy.

Deferred:
- client-approved geometry;
- boundary QA;
- polygon -> threshold enforcement;
- courier zone/minimum enforcement.

Never invent polygons. Courier enforcement stays OFF.

## Reviews / privacy — VERIFIED
- `/otzyvy/` exists;
- new review submissions are pending moderation;
- pending reviews are not public;
- published reviews become public;
- no fake reviews/fake average;
- review privacy consent required in form + server-side;
- Checkout Block privacy consent required;
- synthetic QA data is cleaned up after tests.

## Order notifications — INTERNAL PASS / REAL DELIVERY PENDING
Architecture:
`WooCommerce order -> native WooCommerce email + async Telegram through Action Scheduler`.

Verified internally:
- Woo new-order email reaches `wp_mail`;
- Telegram action queues;
- synthetic success -> sent;
- duplicate send is idempotent;
- PII hidden from Telegram by default;
- synthetic HTTP 500 records error + schedules retry.

External pending:
- real Telegram delivery: needs `ROLLSBAR_TELEGRAM_BOT_TOKEN` + `ROLLSBAR_TELEGRAM_CHAT_ID` in GitHub `staging` secrets;
- real email receipt/deliverability test: needs approved real recipient/mail transport decision.

Never paste these secrets into chat or Git.

## Legal / payment readiness — VERIFIED
Nine editable WordPress pages are published and runtime-verified:
- `/pravovaya-informaciya/`
- `/rekvizity-prodavca/`
- `/publichnaya-oferta/`
- `/dostavka-i-oplata/`
- `/oplata-i-vozvrat/`
- `/politika-konfidencialnosti/`
- `/soglasie-na-obrabotku-personalnyh-dannyh/`
- `/cookies/`
- `/bezopasnost-onlajn-oplaty/`.

Woo terms/privacy settings point to canonical WordPress pages. Public acquiring copy is provider-neutral until a provider is actually connected. Historical bank references are not enough to assume the provider.

Seller source facts retained:
- ИП Гридина Надежда Викторовна;
- ИНН 910504301819;
- ОГРНИП 325911200130902.

No missing bank account, email, acquiring provider, polygon or other client fact was invented.

## Launch payment mode — VERIFIED
Current launch scope:
- `cod` enabled;
- title `Оплата при получении`;
- `bacs`/`cheque` disabled;
- no other gateway enabled;
- online-card slot reserved/disabled;
- no current acquiring provider assumed.

Actual acquiring is a separate later stage after authoritative provider/contract confirmation and provider-specific sandbox testing.

## Yandex Metrica — PREPARED / REAL ID PENDING
Implemented and runtime-tested:
- editable numeric `metrika_counter_id`;
- no ID -> no Yandex tag/request;
- valid ID -> still waits for explicit analytics consent;
- Webvisor off;
- marketing tools not configured;
- goals prepared: `add_to_cart`, `open_cart`, `begin_checkout`, `submit_order`, `purchase`, `phone_click`, plus `shipping_method_select`.

Do not invent the real counter ID and do not claim actual goal reception until the client supplies the counter and hits are observed in Metrica.

## Current migration status
Completed / verified:
- [x] staging foundation + HTTPS;
- [x] full catalog + Gate B;
- [x] cart/checkout/mobile regression baseline;
- [x] Local Pickup;
- [x] DaData suggestions + coordinate resolution + fail-closed precision UX;
- [x] review moderation;
- [x] explicit personal-data consent in checkout/reviews;
- [x] notification internal pipeline + retry/idempotency runtime test;
- [x] legal/payment-readiness pages + runtime validation;
- [x] receipt-only launch payment mode;
- [x] Yandex Metrica integration/goal wiring prepared behind ID+consent gate;
- [x] deploy self-heal ordering;
- [x] official WordPress core integrity restored and continuously gated;
- [x] `wp-config.php` hardened to 640;
- [x] verified server-side staging backups outside web-root;
- [x] every routine live staging deploy backup-gated;
- [x] unused plugins/old bundled themes removed while retaining one fallback theme.

Externally pending / deferred:
- [ ] real Yandex Metrica counter ID + live goal reception verification;
- [ ] real Telegram delivery;
- [ ] real email receipt/deliverability;
- [ ] actual online acquiring — separate future stage;
- [ ] final vacancy questionnaire — needs client wording/input;
- [~] exact polygons/courier enforcement — DEFERRED, NON-BLOCKING.

## CURRENT NEXT ACTION
1. Treat baseline WordPress security and backup/update readiness as **verified on staging**.
2. Continue independent launch acceptance/regression work that does not require client secrets: current HTTP/security headers and public-route health, Site Health/cron/REST checks, recovery/runbook verification, and final pre-production acceptance inventory.
3. Do not automatically upgrade WooCommerce beyond 11.1.2. A version bump must be a deliberate backup -> staging upgrade -> regression cycle.
4. Do not wait on Metrica ID, Telegram/email external credentials, acquiring provider, vacancy wording or polygons; they are external-input blocks.
5. Production remains untouched until full staging QA + explicit owner approval.

## Project No Loss rules
- approved baseline immutable;
- migration code stays separate from `main`;
- no secret values in chat or Git;
- no invented polygons/product facts/client wording/payment-provider facts/analytics IDs;
- do not restore live staging to 5-product smoke catalog;
- factual GitHub/CI/runtime evidence outranks stale summaries;
- do not complete Todoist recovery task `6hf5v5J535WvjJx5` without explicit owner confirmation.

## New-chat recovery prompt
> RollsBar: восстанови состояние по Project No Loss. Не полагайся на память чата. Сначала прочитай `wordpress/docs/CURRENT_STATE.md` и current override в `wordpress/docs/MIGRATION_PLAN.md`, затем сверяй live HEAD `wordpress/migration-2026-10-01`, `main`, последние CI/runtime результаты и Todoist task `6hf5v5J535WvjJx5`. Фактический GitHub/CI выше старых summary. Не повторяй успешно завершённые операции. Security/backup readiness уже VERIFIED: core checksum PASS, wp-config=640, 5 verified server-side snapshots, every staging deploy backup-gated, unused extensions cleaned. Полигоны DEFERRED/NON-BLOCKING. Launch payment = при получении. Внешние credentials/analytics ID не считать настроенными без фактического доказательства.

# RollsBar — CURRENT STATE / Project No Loss handoff

Updated: 2026-10-09

## Purpose
This is the canonical current-state checkpoint for continuing RollsBar without relying on chat memory. Before any future write, re-read this file, the current execution override in `wordpress/docs/MIGRATION_PLAN.md`, the live migration-branch HEAD, recent CI/runtime evidence and Todoist task `6hf5v5J535WvjJx5`.

## Source of truth order
1. Live GitHub branch/code + actual CI/runtime evidence.
2. `wordpress/docs/MIGRATION_PLAN.md` current execution override.
3. This file / Todoist recovery task / Drive handoff.
4. Historical Git/chat only when provenance is disputed.

Historical detailed checkpoints remain in Git history. This file summarizes the latest verified state.

## Git / immutable baseline
Working branch: `wordpress/migration-2026-10-01`.

Latest verified recovery/acceptance state before this documentation write:
- recovery-safe backup/restore tooling through `a5d7cc0288074efe91ee7902fffcc83e246b5675`;
- successful isolated recovery-drill trigger commit `0f9b6866e6da8210456d947c5c3c7831b17517e1`;
- recovery workflow returned to manual-only at `f248071e119f6b235d1fc86d88bdc72c8dcaa791`.

This documentation write advances the branch. **Always re-read live HEAD before any future write.**

Approved baseline is immutable:
`approved/site-2026-10-01 = a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Never modify it.

Default `main` remains infrastructure-only for the address-provider comparison launcher. Last verified HEAD: `af6b829c6c58a072b7bd375af5b8515272c202e7`.

## Live staging — VERIFIED
URL: `https://staging.rollsbar.ru`

Current verified runtime:
- isolated REG.RU staging site/database;
- HTTP -> HTTPS redirect works;
- HTTPS/TLS works;
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
- Yandex Metrica code prepared but no real counter ID is configured, so no Metrica tag loads;
- Telegram staging credentials absent;
- production untouched.

Do not restore the historical five-product smoke catalog to live staging. Five products are only an isolated CI/bootstrap fixture.

## Final technical acceptance — PASS WITH NON-BLOCKING WARNINGS
The independent staging acceptance completed with:
- **42 PASS**;
- **4 WARN**;
- **0 FAIL**.

Verified:
- public HTTPS routes healthy;
- TLS valid;
- HTTP redirects to HTTPS;
- HSTS present;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: strict-origin-when-cross-origin`;
- `X-Frame-Options: SAMEORIGIN`;
- public REST endpoint HTTP 200;
- internal WordPress REST routing healthy (~671 registered routes at the time of audit);
- DB connectivity PASS;
- WordPress loopback PASS;
- WP-Cron enabled and scheduled events healthy;
- WordPress.org connectivity/background update capability PASS;
- uploads writable/working;
- catalog still 118;
- WooCommerce still 11.1.2;
- no fresh PHP fatal/parse errors found.

Non-blocking warnings:
1. WordPress Site Health's admin-context REST probe received expected `401 Unauthorized` from an unauthenticated CLI context; public/internal REST were independently PASS.
2. `Permissions-Policy` is not forced yet.
3. CSP is intentionally not imposed without a dedicated browser regression because an aggressive CSP could break WooCommerce checkout/integrations.
4. XML-RPC connection behavior is warning-only and not required for the current project flows.

Do not rerun this entire acceptance suite solely because a chat reconnects. Rerun only if later changes materially touch the audited layers.

## Security / backup — VERIFIED
Real staging evidence proves:
- official WordPress 7.1.3 core checksums PASS;
- `DISALLOW_FILE_EDIT=true`;
- `FORCE_SSL_ADMIN=true`;
- `wp-config.php` mode = `640`;
- `.htaccess` mode = `644`;
- no world-writable PHP/config files;
- direct `/wp-config.php` and `/.git/config` probes return HTTP 403;
- inactive plugins = 0;
- bundled fallback theme retained: `twentytwentyfive`;
- old bundled themes and unused `akismet`/`hello` removed;
- WooCommerce remains intentionally pinned to tested 11.1.2 and per-plugin auto-update is disabled.

Do not mass-chmod the shared-hosting WordPress tree just because many files may be group-writable. REG.RU ownership/group semantics can require group write. Sensitive config was hardened and no world-writable PHP/config files were found.

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
- DB streams directly into gzip; plain SQL is not intentionally left on disk;
- `wp-config.php` and secrets are not copied;
- snapshot dirs/files have restrictive permissions;
- snapshot publishes only after gzip/tar/SHA-256 verification;
- retention = newest 5 complete snapshots;
- every routine live staging deploy creates/verifies a fresh backup **before mutation** and aborts if backup fails;
- project code is canonical in Git.

### Recovery-safe format 3
Backups now record the exact deployed code through a verified deployed-SHA marker outside web-root:
- `rollsbar_backup_format=3`;
- `project_code_commit=<verified deployed SHA>`;
- `project_code_commit_source=verified_deployed_marker`.

The marker is updated only after a successful deployment. Backups do not treat an incoming, not-yet-deployed SHA as the source version.

## Recovery / runbook proof — VERIFIED
Workflow: `Staging Recovery Drill`.
Successful run: **37924804277**.
Successful job: **113801071712**.

The drill restored the latest recovery-safe snapshot into a **separate temporary REG.RU database**, never over the live staging DB and never over production.

Verified snapshot:
- `20261009T101550Z`;
- format `3`;
- `project_code_commit=09fdafc81a9225383115461523566cd101470b6f`;
- commit source = `verified_deployed_marker`;
- snapshot SHA-256 PASS;
- gzip/tar archive integrity PASS;
- manifest invariants PASS;
- SQL uncompressed bytes = 1,175,422;
- SQL CREATE TABLE statements = 51;
- uploads restored to temp path = 19 files;
- DB import into isolated temp DB PASS;
- restored table count = 51;
- restored `blog_public=0`;
- restored published products = 118;
- content invariants PASS;
- temporary DB cleanup PASS.

Final workflow state is **manual-only `workflow_dispatch`**. Ordinary commits must not create recovery-drill databases.

Do not repeat the recovery drill just because a chat reconnects. Repeat intentionally only after a material backup/recovery architecture change or before a high-risk transition when fresh restore proof is desired.

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
- exact-house address returns coordinates and `allow_auto_zone=1`;
- lower-precision address is fail-closed with `allow_auto_zone=0` and clarification warning;
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
- new submissions are pending moderation;
- pending reviews are not public;
- published reviews become public;
- no fake reviews/fake average;
- review privacy consent required client-side/server-side;
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
- real Telegram delivery requires approved bot token/chat ID in GitHub `staging` secrets;
- real email receipt/deliverability requires approved real recipient/mail transport decision.

Never paste secrets into chat or Git.

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
- goals prepared: `add_to_cart`, `open_cart`, `begin_checkout`, `submit_order`, `purchase`, `phone_click`, `shipping_method_select`.

Do not invent the real counter ID and do not claim actual goal reception until the client supplies the counter and hits are observed in Metrica.

## Pre-production acceptance inventory
### Internally READY / verified on staging
- [x] staging foundation + HTTPS;
- [x] full catalog + Gate B;
- [x] cart/checkout/mobile baseline;
- [x] Local Pickup;
- [x] DaData suggestions + coordinates + fail-closed precision UX;
- [x] review moderation;
- [x] personal-data consent in checkout/reviews;
- [x] internal notification queue/retry/idempotency;
- [x] legal/payment-readiness pages;
- [x] receipt-only launch payment mode;
- [x] Metrica integration/goal wiring prepared behind ID+consent gate;
- [x] deploy self-heal ordering;
- [x] WordPress core integrity + security hardening;
- [x] backup-before-mutation gate;
- [x] unused extension cleanup;
- [x] public-route / HTTP / REST / loopback / cron / Site Health acceptance;
- [x] server-side backup restore proof in isolated temporary DB;
- [x] recovery workflow returned to manual-only mode.

### Deferred / non-blocking for continued development
- [~] exact delivery polygons and courier enforcement;
- [~] online acquiring (current launch scope is payment at receipt);
- [~] stronger CSP / Permissions-Policy, pending dedicated compatibility testing.

### External input / real-world proof still pending
- [ ] real Telegram delivery, only if Telegram is required for launch;
- [ ] real email receipt/deliverability, if email delivery is required for launch acceptance;
- [ ] real Yandex Metrica counter + observed goal hits, if analytics is required at launch;
- [ ] final vacancy wording/input;
- [ ] actual acquiring provider/contract/credentials for the later online-payment phase;
- [ ] client-approved delivery polygons for the later courier-enforcement phase.

These are **not automatically all production blockers**. The final go-live scope must distinguish required launch functionality from intentionally deferred features. Current agreed payment scope can launch without online acquiring; polygons are explicitly deferred/non-blocking; Metrica/Telegram are not to be invented or falsely marked configured.

## CURRENT NEXT ACTION
1. Build the final **go-live decision matrix**: `required for current launch` vs `approved deferred` vs `optional integration`.
2. Identify only the smallest external facts/credentials that are truly required by the chosen current launch scope.
3. Do not rerun already-passed security/acceptance/recovery suites unless later code changes touch those layers.
4. Do not automatically upgrade WooCommerce beyond 11.1.2. Any version bump requires backup -> staging upgrade -> regression.
5. Keep production untouched until owner explicitly approves transition.
6. When owner approves transition, prepare a production cutover checklist/backup/rollback plan before any production mutation.

## Project No Loss rules
- approved baseline immutable;
- migration code stays separate from `main`;
- no secret values in chat or Git;
- no invented polygons/product facts/client wording/payment-provider facts/analytics IDs;
- do not restore live staging to five-product smoke catalog;
- factual GitHub/CI/runtime evidence outranks stale summaries;
- do not complete Todoist recovery task `6hf5v5J535WvjJx5` without explicit owner confirmation.

## New-chat recovery prompt
> RollsBar: восстанови состояние по Project No Loss. Не полагайся на память чата. Сначала прочитай `wordpress/docs/CURRENT_STATE.md` и current override в `wordpress/docs/MIGRATION_PLAN.md`, затем сверяй live HEAD `wordpress/migration-2026-10-01`, `main`, последние CI/runtime результаты и Todoist task `6hf5v5J535WvjJx5`. Фактический GitHub/CI выше старых summary. Не повторяй успешно завершённые операции. Security/backup + final technical acceptance + isolated recovery proof уже VERIFIED. Полигоны DEFERRED/NON-BLOCKING. Launch payment = при получении. Production не трогать без явного одобрения владельца. Внешние credentials/analytics IDs не считать настроенными без фактического доказательства.
# Rolls Bar — Production Cutover / Backup / Rollback Runbook

Updated: 2026-10-09
Status: **PREPARED ONLY — PRODUCTION MUST NOT BE TOUCHED YET**

## Purpose
This runbook defines the exact safety gates for moving the verified WordPress staging build to production later. It is documentation only. Creating or updating this file is **not** permission to mutate production.

The current working branch is `wordpress/migration-2026-10-01`. Always re-read live GitHub HEAD, staging deployed SHA and current CI/runtime evidence before using this runbook.

## Non-negotiable production gate
Do not perform any production write, DNS switch, WordPress install/update, database import, file replacement, indexability change or secret installation until **all** of these are true:

1. The owner explicitly approves the production transition in the current conversation/workflow.
2. Current-launch external requirements are resolved or explicitly deferred by the owner:
   - real WooCommerce New order e-mail recipient + real delivery proof;
   - real Telegram delivery if it remains in the agreed launch scope;
   - explicit Telegram PII decision if Telegram remains in scope;
   - real Yandex Metrica counter + goal proof if it remains in the agreed launch scope.
3. Exact release Git SHA is frozen **after** the required integrations are staged and tested.
4. Staging deployed-SHA marker equals that exact frozen release SHA.
5. Targeted regression for every change made after the last broad acceptance suite is green.
6. A production backup/rollback point has been created and verified **before the first production mutation**.

If any item is missing, status is **NO-GO**.

## Current scope that must remain unchanged during cutover
Unless the owner explicitly changes scope before release:

- payment method = **Оплата при получении**;
- online acquiring = OFF / hidden / deferred;
- exact delivery polygons and courier zone/minimum enforcement = OFF / deferred;
- DaData address suggestions remain enabled with `qc_geo` fail-closed policy;
- `qc_geo >= 1` must not silently select a delivery zone;
- WooCommerce stays on the deliberately tested/pinned version until a separate upgrade cycle;
- SEOPress stays on the deliberately tested/pinned version until a separate upgrade cycle;
- no invented delivery polygons, client wording, analytics ID, payment provider or mail recipient;
- no 5-product smoke catalog may be restored to a live environment.

## Phase 0 — Freeze the candidate release
Do this only after the remaining launch integrations are proven on staging.

Record in the release note/checkpoint:

- release Git SHA;
- staging deployed SHA marker;
- WordPress version;
- WooCommerce version;
- SEOPress version;
- catalog count / source-row count;
- enabled payment methods;
- DaData status;
- real e-mail delivery proof reference;
- Telegram proof/reference if in scope;
- Metrica counter/proof reference if in scope;
- owner-approved list of explicitly deferred items.

**Pass condition:** repository release SHA and staging deployed SHA are identical.

Do not make new feature commits after freeze. Any required fix creates a new candidate SHA and resets the freeze check.

## Phase 1 — Inventory production before mutation
This phase is read-only until the backup step begins.

Record, without exposing secrets:

- current production document root;
- current production database name/host identity (masked where needed);
- current WordPress version, if WordPress already exists;
- active theme/plugins and their versions;
- current production home/siteurl;
- PHP version;
- current production SSL status;
- current indexability/robots state;
- current DNS targets relevant to `rollsbar.ru`;
- production file ownership/permissions relevant to deployment;
- available disk space;
- current mail/DNS setup;
- current production content that must be preserved.

If production contains anything not represented in Git/staging, classify it before proceeding:
- preserve and migrate;
- intentionally replace with owner approval;
- unknown -> STOP and resolve.

## Phase 2 — Create the production rollback point
**Never reuse a staging backup as the production backup.**

Before any production write, create a production-specific snapshot outside the public web root containing at minimum:

1. production database dump;
2. production uploads/media archive;
3. production `wp-config.php`/environment configuration backup where safe and appropriate;
4. production `.htaccess` / server routing configuration backup;
5. inventory of existing production plugins/themes and versions;
6. exact pre-cutover production state marker/timestamp;
7. SHA-256 checksums for all backup artifacts;
8. a manifest describing domain, timestamp, source environment and rollback purpose.

Security rules:
- backup storage must not be web-accessible;
- secret-bearing files must retain restrictive permissions;
- do not print DB passwords, SMTP passwords, bot tokens, DaData keys or other secrets into CI logs;
- do not copy production customer/order data into Git or chat.

### Production backup validation
Before continuing:
- checksum validation PASS;
- gzip/tar structural validation PASS;
- DB dump can be parsed/imported in a non-production validation context where feasible;
- backup directory exists and is not inside production document root;
- rollback operator can identify the exact snapshot unambiguously.

If backup validation fails: **STOP. No production deployment.**

## Phase 3 — Prepare production-only secrets/configuration
Secrets must be installed through the chosen secure server/GitHub environment mechanism, never chat or Git.

Expected categories may include:
- DaData server-side key;
- mail/SMTP credentials for the approved operator mailbox/provider;
- Telegram bot token + chat ID if Telegram remains in launch scope;
- production DB credentials;
- hosting/deploy credentials.

Non-secret configuration:
- Yandex Metrica counter ID, if supplied;
- approved operator recipient e-mail address;
- approved `From` name/address;
- production URLs/domain.

Before deployment verify only presence/shape of secrets, not their values.

## Phase 4 — Production deployment rules
The production deployment implementation must be production-specific. Do **not** blindly point the staging bootstrap at production.

Required deployment invariants:

1. backup gate completes before mutation;
2. deploy exact frozen Git SHA only;
3. preserve production customer/order/media state as required;
4. do not replace production database with the staging database;
5. do not import staging orders/users/sessions into production;
6. install/sync only project-owned code and explicitly approved configuration/content migrations;
7. keep payment-at-receipt mode only;
8. keep courier polygon enforcement OFF;
9. apply production home/siteurl deliberately;
10. retain HTTPS and safe HTTP headers;
11. preserve WordPress file-edit restrictions and secure permissions;
12. install pinned WooCommerce/SEOPress versions only through the tested path;
13. install production secrets outside Git;
14. record exact deployed SHA only after all deployment gates pass.

## Phase 5 — Indexability transition
Staging is intentionally noindex. Production must not inherit staging noindex accidentally, but indexability must also not be enabled before the site is ready.

At the deliberate production-indexability step verify:

- production `blog_public` is intentionally set for launch;
- homepage no longer receives the staging-wide `noindex,nofollow` state;
- transactional pages such as cart/checkout remain noindex;
- canonical URLs use the production domain;
- SEOPress XML sitemap uses the production domain and returns successfully;
- Restaurant schema uses the production URL/business entity once;
- WooCommerce Product schema remains single-owner;
- no staging hostname appears in canonical, sitemap, Open Graph URLs or schema;
- `robots.txt` does not accidentally block the whole public site after launch.

Do not submit Search Console/sitemap until these checks pass.

## Phase 6 — Immediate post-cutover smoke
Run immediately after deployment before announcing completion.

### Public frontend
- homepage HTTP 200 over HTTPS;
- HTTP -> HTTPS redirect;
- catalog count/content present;
- product page opens;
- cart add/update/remove works;
- no historical mobile cart-overlay regression;
- checkout opens on desktop + mobile;
- no uncaught JavaScript fatal errors;
- legal/privacy/cookies/reviews/vacancy pages open;
- production-safe SEO signals pass.

### Checkout / order
Place a controlled production-like test order using the currently approved launch payment mode.

Verify:
- order is created exactly once in WooCommerce;
- order number shown to customer;
- customer name/phone/order contents persist;
- shipping/pickup state correct;
- extra address fields persist once;
- payment mode = receipt only;
- no online card gateway exposed;
- no unapproved courier polygon enforcement;
- DaData exact-address path works;
- low-precision address remains fail-closed.

### Operator notification
Required before declaring go-live complete:
- approved operator mailbox receives the real New order e-mail;
- message includes required order information;
- Rolls Bar additional address fields appear once, not duplicated;
- no unexpected recipient receives it.

If Telegram remains in scope:
- Telegram message arrives;
- checkout/order creation did not wait for Telegram API;
- Telegram status is visible in order/admin;
- payload follows the explicitly approved PII policy.

If Metrica remains in scope and counter is supplied:
- tag loads only after consent;
- agreed goals are observed in the real counter/test tooling;
- Webvisor/advertising tools remain off unless separately approved.

### Admin / infrastructure
- wp-admin login works;
- order opens in WooCommerce admin;
- WordPress core checksum PASS;
- expected plugins active at pinned versions;
- no fresh PHP fatal/parse errors;
- scheduled actions/cron healthy;
- no production secret appears in logs/output;
- deployed SHA marker equals frozen release SHA.

## Phase 7 — GO / NO-GO decision
### GO
Only when all current-launch requirements and post-cutover smoke checks pass.

### NO-GO / immediate rollback triggers
Rollback immediately if any of the following occurs and cannot be corrected safely within the approved cutover window:

- production homepage/site inaccessible;
- TLS/redirect regression blocks normal access;
- cart or checkout cannot complete;
- duplicate/incorrect orders are created;
- approved launch payment method unavailable or unapproved payment method exposed;
- critical product/catalog loss;
- database corruption/migration failure;
- PHP fatal/parse errors affecting customer/admin flow;
- order is created but primary operator e-mail cannot be delivered;
- widespread wrong canonical/noindex/robots state that risks indexing the wrong environment;
- production secret exposure;
- deployment SHA cannot be identified/reconciled;
- any unknown production-data overwrite.

Telegram-only failure does not technically prevent WooCommerce from creating the order, but if Telegram remains an agreed launch requirement it still makes the overall launch acceptance **NO-GO** until fixed or explicitly waived by the owner.

## Phase 8 — Rollback procedure
Exact production commands must be finalized only after Phase 1 inventories the actual production host. Do not invent paths/database names in advance.

Rollback sequence conceptually:

1. stop further production writes/deploy jobs;
2. put the site into the safest available short maintenance state if needed;
3. restore pre-cutover project-owned files/server config from the production rollback point;
4. restore pre-cutover production DB **only if the failure involved DB mutation/corruption and after assessing orders created since cutover**;
5. restore uploads only if changed/damaged;
6. restore previous production routing/config/indexability state;
7. clear only safe caches/transients;
8. verify frontend + admin + order data;
9. verify no post-cutover legitimate order/customer data was silently lost;
10. record rollback result and cause.

### Critical order-data rule
If any real customer orders were created after cutover, do **not** blindly import the old database over them. First preserve/export/reconcile those orders. A rollback must never trade a website bug for silent order loss.

## Phase 9 — After successful launch
After a stable observation window:

- retain the pre-cutover production rollback snapshot per agreed retention;
- create the first post-launch production backup and verify it;
- review WooCommerce logs and scheduled actions;
- confirm recurring backup process;
- confirm real order notifications continue working;
- connect/verify Search Console after production SEO checks;
- document exact production deployed SHA;
- keep WooCommerce/SEOPress automatic updates disabled until a deliberate `backup -> staging upgrade -> targeted regression -> production` cycle.

## Current known blockers before this runbook may be executed
As of 2026-10-09:

- actual working operator e-mail address/provider is not documented in Project No Loss;
- current staging Woo recipient is only the staging default/admin address;
- current REG.RU ISPmanager account exposes no mail domain/mailbox for RollsBar and public `rollsbar.ru` has no MX/SPF/DMARC in the read-only audit;
- real New order e-mail delivery is not proven;
- real Telegram credentials/delivery are not configured/proven;
- Telegram PII behavior needs explicit owner/client decision because final TЗ requests name/phone/address while current implementation hides PII by default;
- real Yandex Metrica counter ID has not been supplied/proven.

These do **not** justify touching production early. Resolve or explicitly defer them first, then freeze the release SHA.

## Project No Loss rule
Live GitHub/CI/runtime evidence outranks this runbook if they ever disagree. Re-read the live branch, staging deployed marker, CI results and current external-input decisions immediately before cutover.

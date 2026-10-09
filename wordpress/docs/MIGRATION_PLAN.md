# Rolls Bar — migration plan

## CURRENT EXECUTION OVERRIDE — 2026-10-09

This section is the current execution plan and supersedes stale next-action lines in historical checkpoints. Detailed evidence is in `wordpress/docs/CURRENT_STATE.md` and Git/CI history.

### Current verified state
- Phases 1–5 staging foundation/catalog work are complete.
- Live REG.RU staging remains isolated from production.
- WordPress 7.1.3 + WooCommerce 11.1.2.
- Full catalog = 118 product cards / 131 approved source rows.
- DaData Suggestions is the checkout address provider; fail-closed `qc_geo` browser QA passed.
- Provider country labels/raw unrestricted geography are hidden from customers.
- Local Pickup works.
- Reviews moderation + explicit checkout/review privacy consent are runtime-verified.
- Internal Woo email + async Telegram notification pipeline is runtime-verified; real external delivery remains pending.
- Nine legal/payment-readiness pages are published and wired to canonical WordPress/WooCommerce settings.
- Launch payment mode = **payment at receipt only**; online acquiring is reserved/disabled and hidden.
- Yandex Metrica integration/goals are prepared, but no real counter ID is configured, therefore analytics does not load.
- Production remains untouched; production indexing/live acquiring are OFF.

### Security / backup / recovery — VERIFIED
Completed on real staging:
- [x] official WordPress core checksums PASS;
- [x] `DISALLOW_FILE_EDIT=true`;
- [x] `FORCE_SSL_ADMIN=true`;
- [x] `wp-config.php` mode 640;
- [x] no world-writable PHP/config files;
- [x] sensitive `/wp-config.php` and `/.git/config` HTTP probes return 403;
- [x] server-side DB + uploads backups outside web-root;
- [x] gzip/tar/SHA-256 validation and newest-5 retention;
- [x] every routine live staging deploy creates/verifies backup **before mutation**;
- [x] backup format 3 records the exact verified deployed Git SHA;
- [x] unused plugins/old bundled themes cleaned while one fallback theme remains;
- [x] WooCommerce intentionally pinned to tested 11.1.2 with per-plugin auto-update disabled;
- [x] latest format-3 snapshot actually restored into an isolated temporary REG.RU DB and verified;
- [x] temporary recovery DB removed after proof;
- [x] recovery workflow returned to manual-only `workflow_dispatch`.

Recovery proof:
- workflow run `37924804277` — SUCCESS;
- job `113801071712` — SUCCESS;
- snapshot `20261009T101550Z`;
- restored tables = 51;
- restored products = 118;
- restored `blog_public=0`;
- restored uploads = 19 files;
- cleanup = PASS.

Do not repeat security/backup/recovery work solely because a chat reconnects. Rerun only when later changes materially affect those layers or when intentionally refreshing recovery proof before a high-risk transition.

### Final technical staging acceptance — PASS
Independent acceptance result:
- **42 PASS**;
- **4 WARN**;
- **0 FAIL**.

Verified areas include HTTPS/TLS, HTTP->HTTPS redirect, public routes, security headers, REST, DB, loopback, WP-Cron/scheduled events, WordPress.org connectivity, uploads, 118 products, WooCommerce 11.1.2, and no fresh PHP fatal/parse errors.

Non-blocking warnings remain around admin-context Site Health REST auth, optional `Permissions-Policy`, intentionally deferred CSP, and XML-RPC behavior. They are not current launch failures.

### Delivery polygons — DEFERRED / NON-BLOCKING
Exact delivery polygons are unavailable from the client. This does **not** block continued development.

Already prepared:
- thresholds 1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB;
- editable delivery data;
- polygon storage/sanitation;
- point-in-polygon resolver;
- DaData address -> coordinates;
- fail-closed geocode precision policy.

Deferred:
- client drawing/approval of real boundaries;
- boundary-case QA;
- polygon -> threshold enforcement;
- courier zone/minimum enforcement.

Never invent production polygons. Courier enforcement stays OFF.

### Phase 6 — behavior / integrations
Completed:
- [x] checkout fields + +7 helper;
- [x] editable promo/vacancy/content/admin model;
- [x] HPOS/order-list compatibility;
- [x] Local Pickup;
- [x] DaData Suggestions + coordinate resolution;
- [x] fail-closed geocode precision UX;
- [x] reviews moderation;
- [x] required privacy consent;
- [x] internal order notification pipeline + retry/idempotency test;
- [x] Yandex Metrica code/goal preparation behind counter-ID + consent gate.

External/pending:
- [ ] real Yandex Metrica counter ID + live goal reception verification;
- [ ] real Telegram delivery — bot token/chat ID absent on staging;
- [ ] real email receipt/deliverability;
- [ ] final vacancy questionnaire — needs final client wording/input;
- [~] exact polygons/courier enforcement — deferred/non-blocking.

### Phase 7 — payment readiness / acquiring
Current launch state:
- [x] payment at receipt enabled;
- [x] unapproved core alternatives disabled;
- [x] online-card gateway hidden/reserved;
- [x] no acquiring provider assumed from historical references;
- [x] HTTPS/catalog/cart/checkout/legal/privacy/payment-security readiness verified.

Online acquiring is a separate future stage and requires:
- [ ] authoritative provider/contract confirmation;
- [ ] provider-specific credentials supplied secret-safely;
- [ ] staging success/failure/cancel callback tests;
- [ ] refund-flow test where applicable;
- [ ] explicit production enablement decision.

Historical references to a bank are not enough to assume the current provider.

### FINAL PRE-PRODUCTION DECISION PATH
The next work is **not another technical rebuild**. The next step is to decide the exact current go-live scope.

Classify each remaining item as:
1. **REQUIRED FOR CURRENT LAUNCH** — must be supplied/tested before production;
2. **APPROVED DEFERRED** — intentionally absent at first launch and does not block production;
3. **OPTIONAL INTEGRATION** — can be connected later without changing the core launch decision.

Known remaining inputs/features to classify:
- real Telegram order delivery;
- real email receipt/deliverability;
- real Yandex Metrica counter + observed goals;
- vacancy final wording;
- exact delivery polygons/courier enforcement;
- online acquiring.

Current architectural decisions already imply:
- online acquiring is **not required** for the receipt-only launch scope;
- exact polygons/courier enforcement are **DEFERRED / NON-BLOCKING**;
- Metrica and Telegram must not be invented or marked configured merely to satisfy a checklist.

### Next executable path
1. Build/confirm the current-launch go-live matrix from the remaining external items above.
2. Request only the smallest external inputs that are truly required by that chosen launch scope.
3. Do not repeat already-passed technical acceptance/recovery suites unless a later change touches them.
4. Do not automatically upgrade WooCommerce past 11.1.2. Any version bump requires backup -> staging upgrade -> regression.
5. Before any production mutation, prepare a production cutover + production backup + rollback checklist.
6. Production transition requires explicit owner approval.

---

## Phase 0 — freeze baseline
Approved UX baseline is immutable: `approved/site-2026-10-01` / `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.

## Phase 1 — staging foundation
Status: COMPLETE.
- isolated staging hostname/database
- HTTPS
- WordPress/WooCommerce
- secret-safe deployment access
- verified backups

## Phase 2 — code foundation
Status: COMPLETE.
- `rollsbar-theme`
- `rollsbar-core`
- no direct core edits
- Git-backed deployment
- self-healing project-code deploy order

## Phase 3 — catalog model
Status: COMPLETE.
Stable approved catalog model/importer with client-edit preservation.

## Phase 4 — pilot
Status: COMPLETE.
Representative catalog/cart/checkout behavior validated.

## Phase 5 — full catalog
Status: COMPLETE ON STAGING.
118 product cards / 131 source rows; repeat import preserves 118 products.

## Phase 6 — Rolls Bar behavior
Status: COMPLETE FOR INTERNAL IMPLEMENTATION; EXTERNAL REAL-WORLD INTEGRATIONS REMAIN TO BE CLASSIFIED FOR GO-LIVE.

## Phase 7 — payments
Status: LAUNCH = PAYMENT AT RECEIPT; LEGAL/BANK-READINESS PASS; ONLINE ACQUIRING IS NOT CONNECTED AND IS A SEPARATE FUTURE STAGE.

## Phase 8 — production
Not started.
Required before transition:
- current go-live scope explicitly confirmed;
- all items classified REQUIRED FOR CURRENT LAUNCH completed;
- production backup/transition/rollback plan;
- explicit owner approval;
- then domain/runtime transition and monitoring.

Do not overwrite a production database with staging after live orders begin.

## Project No Loss rules
- live GitHub/CI/runtime evidence outranks stale summaries;
- approved baseline immutable;
- migration work stays off `main`;
- no secret values in chat or Git;
- never invent polygons, product facts, payment-provider facts, client wording or analytics IDs;
- do not restore the five-product CI smoke catalog onto live staging;
- production remains untouched until explicit owner approval;
- Todoist recovery task `6hf5v5J535WvjJx5` stays open until owner explicitly confirms closure.
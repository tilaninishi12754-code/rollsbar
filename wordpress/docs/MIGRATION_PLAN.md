# Rolls Bar — migration plan

## CURRENT EXECUTION OVERRIDE — 2026-10-09

This section is the current execution plan and supersedes stale "current next action" lines in historical checkpoints. Detailed evidence is in `wordpress/docs/CURRENT_STATE.md` and Git/CI history.

### Current verified state
- Phase 1–5 staging foundation/catalog work is complete.
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

### Security / backup readiness — VERIFIED
Completed on real staging:
- [x] official WordPress 7.1.3 core checksum PASS;
- [x] `DISALLOW_FILE_EDIT=true`;
- [x] `FORCE_SSL_ADMIN=true`;
- [x] `wp-config.php` tightened to mode 640 and verified with WP-CLI + HTTP health;
- [x] no world-writable PHP/config files found;
- [x] sensitive `/wp-config.php` and `/.git/config` HTTP probes return 403;
- [x] canonical server-side DB + uploads backup outside web-root;
- [x] gzip/tar/SHA-256 verification before a snapshot is considered valid;
- [x] retention of newest 5 complete snapshots;
- [x] every routine live staging deploy creates/verifies a fresh backup **before mutation** and aborts if backup fails;
- [x] deploy final gate re-verifies official core checksums and `wp-config.php=640`;
- [x] inactive plugins `akismet` and `hello` removed;
- [x] old bundled themes `twentytwentythree` and `twentytwentyfour` removed;
- [x] one bundled fallback theme `twentytwentyfive` retained for diagnostics;
- [x] WooCommerce remains intentionally pinned to tested 11.1.2; per-plugin auto-update is disabled so upgrades go through backup -> staging -> regression.

Key evidence:
- hardening workflow `37909323728` — SUCCESS;
- backup-gated live deploy `37909731997` — SUCCESS;
- static gate `37909732193` — SUCCESS;
- package build `37909732076` — SUCCESS;
- clean bootstrap `37909731971` — SUCCESS;
- extension cleanup `37910173271` — SUCCESS;
- independent post-cleanup audit rerun job `113754003039` — SUCCESS.

Current independent audit proves:
- inactive plugins = 0;
- inactive themes = only `twentytwentyfive`;
- backup snapshot count = 5;
- latest backup integrity PASS;
- core checksum PASS;
- core updates available = 0;
- only a newer WooCommerce release is offered, but current live staging remains 11.1.2 by design.

Do **not** mass-chmod the shared-hosting WordPress tree solely because many files are group-writable. REG.RU shared ownership/group semantics may require group write. We hardened the sensitive config and proved there are no world-writable PHP/config files.

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
- [x] no acquiring provider assumed from historical references.

Readiness layer:
- [x] HTTPS;
- [x] catalog/prices/cart/checkout;
- [x] seller requisites;
- [x] public offer;
- [x] delivery/payment page;
- [x] payment/refund page;
- [x] privacy policy + separate consent;
- [x] payment-security page;
- [x] footer legal links;
- [x] runtime validation of canonical terms/privacy/provider-neutral copy.

Online acquiring is a separate future stage and requires:
- [ ] authoritative provider/contract confirmation;
- [ ] official sandbox/merchant details;
- [ ] secret-safe credentials;
- [ ] staging success/failure/cancel callback tests;
- [ ] refund-flow test where applicable;
- [ ] explicit production enablement decision.

Historical references to a bank are not enough to assume the current provider.

### Next executable path
1. Treat baseline WordPress security + backup/update readiness as **complete and verified on staging**.
2. Continue independent final acceptance work that needs no client secrets:
   - public-route/HTTP health and security-header audit;
   - WordPress Site Health / REST / loopback / cron readiness;
   - recovery/runbook validation without destructive restore on live staging;
   - final pre-production acceptance inventory and remaining blockers.
3. Do not automatically upgrade WooCommerce past 11.1.2. Any version bump must be deliberate and pass a fresh staging regression cycle.
4. Do not wait on Metrica ID, Telegram/email external credentials, acquiring provider, vacancy wording or polygons.
5. Production transition remains gated by full staging QA + explicit owner approval.

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
Status: IN PROGRESS ONLY FOR EXTERNAL-INPUT ITEMS.
Core functional flows are internally verified; remaining items are listed in the current override above.

## Phase 7 — payments
Status: LAUNCH = PAYMENT AT RECEIPT; LEGAL/BANK-READINESS PASS; ONLINE ACQUIRING IS NOT CONNECTED AND IS A SEPARATE FUTURE STAGE.

## Phase 8 — production
Not started.
Required before transition:
- current staging acceptance pass;
- production backup/transition plan;
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

# Rolls Bar — migration plan

## CURRENT EXECUTION OVERRIDE — 2026-10-09

This section is the current execution plan and supersedes stale "current next action" lines in the historical checkpoints below. Historical sections are intentionally preserved for Project No Loss evidence.

### Current verified state
- Phase 1–5 staging foundation/catalog work is complete.
- Full staging catalog remains 118 product cards from 131 approved source rows.
- WordPress 7.1.3 + WooCommerce 11.1.2 are live on isolated REG.RU staging.
- DaData Suggestions is the current checkout address provider on staging.
- Real checkout browser verification passed: exact-house `qc_geo=0` may proceed to future zone lookup; lower precision is fail-closed and cannot silently choose a zone.
- Provider country labels/raw unrestricted geography are not shown to customers.
- Native Local Pickup is working.
- Review moderation flow is implemented and runtime-verified on live staging: `/otzyvy/`, anonymous submission -> `pending`, pending review hidden publicly, admin publish -> public visibility. Synthetic QA review is deleted after verification.
- Production remains untouched.

### Delivery polygons — DEFERRED / NON-BLOCKING
Exact delivery polygons are not currently available from the client. This does **not** block continued website development.

Already prepared:
- 7 canonical minimum/free-delivery thresholds: 1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB;
- polygon storage and sanitation;
- tested point-in-polygon resolver;
- DaData address -> coordinate path;
- fail-closed precision policy.

Deferred until real geometry exists:
- client drawing/approval of exact boundaries;
- boundary-case QA;
- automatic polygon -> threshold enforcement;
- courier zone/minimum enforcement.

Safety rule: NEVER invent real polygons. Courier enforcement stays OFF. We may later provide a client-safe free/open map drawing layer so the client can draw/correct geometry themselves. The historical Yandex-only editor direction below is no longer the required current path; Yandex/2GIS are fallback-only unless DaData materially fails.

### Phase 6 remaining work, in execution order
- [x] DaData address selection on staging checkout
- [x] fail-closed `qc_geo` policy and real checkout browser verification
- [x] reviews moderation flow + live runtime verification
- [ ] real order-notification delivery test (WooCommerce email + Telegram) — requires actual staging recipient/Telegram credentials before claiming end-to-end delivery
- [ ] final vacancy questionnaire — blocked only on final client wording/input
- [ ] future integrations only when explicitly required
- [~] exact delivery polygons / courier enforcement — DEFERRED, NON-BLOCKING

### Next executable path
1. Finish everything that can be verified without delivery polygons.
2. Validate order notification behavior and identify the smallest external credential/input still required for a true delivery test.
3. If notification delivery is externally blocked, continue to the next independent migration/payment-readiness work instead of stopping the project.
4. Return to polygons later without reworking DaData/checkout architecture.
5. Production transition remains gated by full staging QA + explicit owner approval.

---

## Phase 0 — freeze baseline
Keep the current GitHub Pages demo as the approved UX reference while WordPress is built.

## Phase 1 — staging foundation
- staging hostname
- HTTPS
- clean WordPress
- WooCommerce
- backup
- separate automation/deploy user

## Phase 2 — code foundation
- rollsbar-theme
- rollsbar-core
- no direct WordPress core edits
- Git-backed changes

## Phase 3 — catalog model
Before bulk import:
- stable SKU for every sellable item/variation
- categories
- simple vs variable products
- sizes / dough / sauce / modifiers
- prices
- image mapping
- stock/visibility policy

## Phase 4 — pilot
Import a small sample first:
- simple roll
- variable pizza
- WOK with options
- set
- sauce/drink

Verify catalog -> cart -> checkout -> order admin.

## Phase 5 — full catalog
Generate WooCommerce CSV from the approved master table and import the full catalog.

Status: **COMPLETE ON STAGING** — 118 product cards / 131 source rows; repeat import leaves exactly 118 products.

## Phase 6 — Rolls Bar behavior

Status: **IN PROGRESS — LIVE STAGING GATE B PASS**

Implemented before staging:
- [x] block-native additional checkout fields via WooCommerce Additional Checkout Fields API
- [x] configurable requiredness for entrance / door code / floor / apartment-office
- [x] +7 phone helper prepared for checkout
- [x] editable promo cards connected to frontend
- [x] editable vacancies connected to careers page
- [x] Restaurant schema / transactional noindex ownership layer
- [x] client-safe settings for phone/address/socials
- [x] separate editable Composition / Ingredients field
- [x] product weight/volume + optional KBJU fields
- [x] catalog importer seeds composition and only explicit source weight/volume values without overwriting later admin edits
- [x] HPOS-compatible operator order-list columns: name / phone / address / delivery zone / time
- [x] explicit WooCommerce compatibility declarations for HPOS + Cart/Checkout Blocks

Prepared architecture / pending staging or client input:
- [x] native WooCommerce Blocks Local Pickup configuration on staging
- [x] editable delivery-area table with 7 confirmed free-delivery minimum thresholds
- [x] storefront delivery table sourced from the same editable WordPress data
- [ ] Yandex address/map integration — runtime API key still required
- [x] minimal client-safe polygon editor implemented in WordPress; runtime map activation waits for Yandex JS API key
- [ ] automatic delivery-zone resolution from real polygons — resolver engine is tested, but no accepted real polygons/address geocoding yet
- [ ] enforce the confirmed minimum-order threshold after an address resolves to a polygon
- [ ] courier shipping method enabled only after real zone polygons exist
- [x] order notification architecture: native WooCommerce email + async Telegram via Action Scheduler
- [ ] staging credentials + real email/Telegram delivery test
- [ ] final vacancy questionnaire
- [x] reviews moderation flow — implemented and verified on live staging 2026-10-09; see current override above
- [ ] future integrations

Rule: do not invent production delivery prices, minimums, polygons or required checkout fields.

Polygon editor rule: do not build a standalone GIS/map-management system. During Gate B/staging, implement only the minimum client-safe Yandex Maps polygon editor needed to select a delivery tier, draw/edit its boundary, save coordinates, and test real addresses. Business users may edit zone geometry; code/layout/checkout mechanics remain protected. Exact polygons are created and corrected with the client on staging, not guessed pre-hosting.

Historical note: the Yandex-specific wording above records the earlier implementation direction. Current 2026-10-09 direction is provider-independent and DaData-first; visual polygon editing may use a free/open map layer later. This historical section must not be interpreted as a current Yandex-key blocker.

## Phase 7 — payments
Connect acquiring only after the site, legal pages, SSL, catalog and checkout are ready for bank review.

## Phase 8 — production
- backup staging and production
- regression test
- point domain to production host
- monitor checkout/orders
- do not overwrite production database with staging after live orders begin


## Staging deployment readiness — 2026-10-05

Status: **REG.RU STAGING LIVE / FULL CATALOG + GATE B PASS**

Verified on real REG.RU staging:
- `staging.rollsbar.ru` DNS resolves to the isolated REG.RU staging site;
- trusted HTTPS / Let's Encrypt works;
- WordPress 7.1.2 + WooCommerce 11.1.2;
- isolated staging database;
- `rollsbar-theme` + `rollsbar-core` active;
- indexing disabled (`blog_public=0`);
- RUB currency and pretty permalinks fixed as deployment invariants;
- native WooCommerce Blocks Local Pickup visible in checkout;
- full catalog promoted from 5-card smoke to 118 cards / 131 source rows;
- repeat full import leaves exactly 118 products (idempotency proof);
- routine live code deploy preserves the promoted 118-product catalog and no longer reruns the historical 5-card seed.

Live browser Gate B (desktop + mobile) verifies:
- HTTPS home/cart/checkout;
- 118 product cards;
- add-to-cart + Woo Store API session persistence;
- ruble prices and no dollar rendering;
- checkout fields + phone `+7` behavior;
- no manual delivery-zone selector;
- native Local Pickup;
- historical mobile sticky-cart overlay regression absent;
- no uncaught page JavaScript errors.

Historical current next action (SUPERSEDED by 2026-10-09 override):
connect a restricted Yandex Maps JS API 3.0 key to staging → live-test the minimal polygon editor → client draws/accepts exact boundaries → then wire address geocoding and production delivery-zone/minimum enforcement.

Historical package/readiness evidence from 2026-10-02 remains valid:
- REG.RU staging runbook;
- credential-free deployment scripts;
- exact WordPress 7.1.2 / WooCommerce 11.1.2 pin;
- isolated 5-product smoke import via `--limit=5`;
- guarded full-catalog promotion;
- self-contained `rollsbar-core.zip` with catalog;
- `rollsbar-theme.zip`;
- deterministic manifest/SHA package;
- static + shell + secret CI gates.

Package-of-record build run `36961212326`: SUCCESS.
Static gate run `36961212345`: SUCCESS.
Clean ephemeral WordPress staging bootstrap run `36961218015`: SUCCESS.

See `STAGING_PACKAGE_RECEIPT_2026-10-02.md`.

## Admin model no-loss checkpoint — 2026-10-02

Recovered source/chat reconciliation confirmed the latest admin requirements are preserved. Safe pre-staging gaps were implemented on `wordpress/migration-2026-10-01` without changing the frozen approved site.

Implemented and verified:
- separate `Состав / ингредиенты` product field;
- catalog seed maps source description into Composition while preserving the original Woo description;
- display weight is seeded only where the approved source explicitly states a leading weight/volume value; missing source weights are not invented;
- HPOS-compatible operator order columns for customer name, phone, address, delivery zone and order time, alongside WooCommerce status/total;
- `WC tested up to: 11.1.2` plus `custom_order_tables` and `cart_checkout_blocks` compatibility declarations;
- backup branch: `backup/pre-admin-gaps-2026-10-02`.

Verification:
- package build run `37002184393`: SUCCESS;
- static gate run `37002184427`: SUCCESS;
- clean runtime smoke run `37002348736`: SUCCESS;
- runtime smoke confirmed the first imported product has separate composition + `250 г` display weight and that the HPOS operator columns register.

Still intentionally pending:
- real delivery polygons (minimum/free-delivery thresholds are now confirmed and implemented as editable data);
- exact final vacancy questionnaire;
- any weight/volume values absent from the approved catalog source;
- final decision on splitting Street and House into separate checkout fields;
- any WOK remodel beyond the already approved catalog model.


## Delivery threshold checkpoint — 2026-10-02

Father clarified the supplied amounts are both the minimum order threshold for the listed territory and the amount from which courier delivery is free. No separate courier fee was supplied.

Implemented:
- dedicated client-editable Rolls Bar → Delivery admin screen;
- 7 confirmed thresholds: 1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 ₽;
- area lists preserved as source wording;
- storefront delivery table uses the same WordPress data;
- manual zone selection remains absent;
- no polygon or address matching is guessed from neighborhood names.

Safety:
- backup branch: `backup/pre-delivery-rules-2026-10-02`;
- exact polygon resolver remains disabled until precise boundaries exist.

Verification:
- package build run `37007807192`: SUCCESS;
- static gate run `37007811445`: SUCCESS;
- clean WordPress bootstrap smoke run `37007818359`: SUCCESS;
- runtime smoke verified all 7 tiers and representative mappings `М. Жукова → 1500 ₽`, `Мазанка → 4000 ₽`.

Current non-blocking missing data:
- exact polygon boundaries for address → zone automation;
- Yandex Maps production API key/runtime configuration;
- final vacancy questionnaire;
- source weights/volumes absent from the approved catalog;
- direct decision if Street and House should be split in checkout.

These items do not block continued WordPress migration. They block only their corresponding final production behaviors.

## Live Gate B + polygon-editor checkpoint — 2026-10-05

Closed by observed evidence, not by declaration:
- live full-catalog Browser Gate B run `37353602056`: SUCCESS;
- full-catalog promotion run `37353275622`: SUCCESS, `5 -> 118 -> 118` products across initial and repeat import;
- native Blocks Local Pickup is visible in both desktop and mobile checkout;
- delivery polygon storage accepts only valid coordinate ranges, strips a duplicate closing point, requires at least 3 valid vertices, and caps geometry at 150 vertices;
- point-in-polygon resolver passes synthetic inside/outside runtime tests in the clean WordPress smoke environment;
- Yandex editor code is gated behind `ROLLSBAR_YANDEX_MAPS_API_KEY`, so absence of a key cannot alter current checkout/delivery behavior;
- no real delivery polygons have been invented or enabled.

Historical runtime activation blocker (SUPERSEDED as global blocker):
- Yandex Maps JS API 3.0 key with HTTP Referer restriction for staging is still absent;
- therefore the historical Yandex visual editor cannot be live-tested, but this no longer blocks continued website development. Exact real polygons remain deferred until client input/editor use.

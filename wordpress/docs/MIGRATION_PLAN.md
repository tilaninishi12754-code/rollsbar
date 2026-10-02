# Rolls Bar — migration plan

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

## Phase 6 — Rolls Bar behavior

Status: **IN PROGRESS**

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
- [ ] native WooCommerce Blocks Local Pickup configuration on staging
- [x] editable delivery-area table with 7 confirmed free-delivery minimum thresholds
- [x] storefront delivery table sourced from the same editable WordPress data
- [ ] Yandex address/map integration
- [ ] minimal client-safe polygon editor in WordPress during Gate B/staging
- [ ] automatic delivery-zone resolution from real polygons
- [ ] enforce the confirmed minimum-order threshold after an address resolves to a polygon
- [ ] courier shipping method enabled only after real zone polygons exist
- [x] order notification architecture: native WooCommerce email + async Telegram via Action Scheduler
- [ ] staging credentials + real email/Telegram delivery test
- [ ] final vacancy questionnaire
- [ ] reviews moderation flow
- [ ] future integrations

Rule: do not invent production delivery prices, minimums, polygons or required checkout fields.

Polygon editor rule: do not build a standalone GIS/map-management system. During Gate B/staging, implement only the minimum client-safe Yandex Maps polygon editor needed to select a delivery tier, draw/edit its boundary, save coordinates, and test real addresses. Business users may edit zone geometry; code/layout/checkout mechanics remain protected. Exact polygons are created and corrected with the client on staging, not guessed pre-hosting.

## Phase 7 — payments
Connect acquiring only after the site, legal pages, SSL, catalog and checkout are ready for bank review.

## Phase 8 — production
- backup staging and production
- regression test
- point domain to production host
- monitor checkout/orders
- do not overwrite production database with staging after live orders begin


## Staging deployment readiness — 2026-10-02

Status: **PACKAGE + CLEAN BOOTSTRAP VERIFIED / REG.RU INPUT PENDING**

Prepared:
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

The clean smoke proved WP 7.1.2 + WooCommerce 11.1.2 install, language pack, theme/core activation, 5-card import, HTTP startup, WooCommerce pages, CheckoutFields registration and staging safety before access to REG.RU.

See `STAGING_PACKAGE_RECEIPT_2026-10-02.md`.

FIRST NEXT ACTION when REG.RU access arrives:
inspect hosting facts → create staging subdomain/DB/HTTPS → preflight → bootstrap → 5-card Gate B smoke.

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

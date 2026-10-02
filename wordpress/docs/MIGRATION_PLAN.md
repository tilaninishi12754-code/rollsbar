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
- [x] product weight/volume + optional KBJU fields

Prepared architecture / pending staging or client input:
- [ ] native WooCommerce Blocks Local Pickup configuration on staging
- [ ] Yandex address/map integration
- [ ] automatic delivery-zone resolution from real polygons
- [ ] minimum order / delivery fee / free-delivery threshold by zone
- [ ] courier shipping method enabled only after real zone rules exist
- [x] order notification architecture: native WooCommerce email + async Telegram via Action Scheduler
- [ ] staging credentials + real email/Telegram delivery test
- [ ] final vacancy questionnaire
- [ ] reviews moderation flow
- [ ] future integrations

Rule: do not invent production delivery prices, minimums, polygons or required checkout fields.

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

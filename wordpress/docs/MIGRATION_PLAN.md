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
Implement in rollsbar-core:
- custom checkout fields
- phone normalization (+7)
- address/map
- automatic delivery zone
- minimum order by zone
- delivery/pickup
- Telegram/email notifications
- reviews moderation
- jobs/vacancies
- future integrations

## Phase 7 — payments
Connect acquiring only after the site, legal pages, SSL, catalog and checkout are ready for bank review.

## Phase 8 — production
- backup staging and production
- regression test
- point domain to production host
- monitor checkout/orders
- do not overwrite production database with staging after live orders begin

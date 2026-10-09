# Rolls Bar — migration plan

## CURRENT EXECUTION OVERRIDE — 2026-10-09

This section is the current execution plan and supersedes stale "current next action" lines in the historical checkpoints below. Historical sections are intentionally preserved for Project No Loss evidence.

### Current verified state
- Phase 1–5 staging foundation/catalog work is complete.
- Full staging catalog remains 118 product cards from 131 approved source rows.
- WordPress 7.1.3 + WooCommerce 11.1.2 are live on isolated REG.RU staging.
- DaData Suggestions is the checkout address provider on staging.
- Real checkout browser verification passed: exact-house `qc_geo=0` may proceed to future zone lookup; lower precision is fail-closed and cannot silently choose a zone.
- Provider country labels/raw unrestricted geography are not shown to customers.
- Native Local Pickup is working.
- Review moderation flow is implemented and runtime-verified.
- Checkout and review flows require explicit personal-data consent.
- Order-notification INTERNAL pipeline is runtime-verified: Woo new-order email reaches `wp_mail`; Telegram Action Scheduler queue/success/idempotency/retry behavior passes synthetic tests. Real external delivery is NOT yet claimed.
- Nine legal/payment-readiness pages are published in WordPress, linked to Woo terms/privacy settings and runtime-verified.
- Published acquiring copy is provider-neutral until an actual current provider is confirmed; stale baseline SberBank wording is not treated as current truth.
- Deployment can now self-heal a broken active project plugin copy by replacing project code before WP-CLI boots active plugins.
- Production remains untouched and live payments are OFF.

Latest full proof on implementation commit `3dd7ad2a88f970059335769459d8cf5eb76ac6b8`:
- static gate `37900012834` — SUCCESS;
- package build `37900012809` — SUCCESS;
- clean bootstrap `37900012723` — SUCCESS;
- live REG.RU deploy `37900012673` — SUCCESS;
- live runtime: `LEGAL / PAYMENT READINESS RUNTIME PASS`, `ORDER NOTIFICATIONS RUNTIME PASS`, `REVIEWS MODERATION RUNTIME PASS`, `ADDRESS SUGGESTIONS RUNTIME PASS`, catalog=118, `blog_public=0`, staging deploy PASS.

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

Safety rule: NEVER invent real polygons. Courier enforcement stays OFF. We may later provide a client-safe free/open map drawing layer so the client can draw/correct geometry themselves. Yandex/2GIS are fallback-only unless DaData materially fails.

### Phase 6 remaining work
- [x] DaData address selection on staging checkout
- [x] fail-closed `qc_geo` policy and real checkout browser verification
- [x] reviews moderation flow + live runtime verification
- [x] explicit privacy consent for checkout + reviews
- [x] internal Woo email + async Telegram notification pipeline/runtime verification
- [ ] real external Telegram delivery — current staging bot token/chat ID absent
- [ ] real external email receipt/deliverability test
- [ ] final vacancy questionnaire — blocked only on final client wording/input
- [~] exact delivery polygons / courier enforcement — DEFERRED, NON-BLOCKING

### Phase 7 — payment readiness / acquiring
Internally ready on staging:
- [x] HTTPS
- [x] catalog with prices
- [x] cart/checkout
- [x] seller requisites page
- [x] public offer page
- [x] delivery/payment page
- [x] payment/refund page
- [x] privacy policy
- [x] separate personal-data consent
- [x] payment-security page
- [x] legal links exposed in footer
- [x] Woo terms/privacy options wired to canonical pages
- [x] legal runtime verifier prevents stale `.html` links and unverified acquiring-provider claims

Still required before a real online-payment test:
- [ ] authoritative current acquiring-provider/contract confirmation;
- [ ] official sandbox/merchant integration details for that provider;
- [ ] credentials stored through a secret-safe path, never in chat/Git;
- [ ] staging payment success/failure/cancel callback test;
- [ ] staging refund flow test where supported/required;
- [ ] only after those checks decide production enablement.

Historical references to a bank or earlier acquiring discussion are NOT enough to assume the current provider. Do not write provider-specific production code until provider/contract status is confirmed by authoritative project/client input.

### Next executable path
1. Treat legal/payment-readiness plumbing as complete on staging.
2. Confirm the actual current acquiring provider/contract status from authoritative project/client context.
3. If provider is confirmed, follow that provider's current official integration docs and wire staging/sandbox only.
4. If provider/credentials are externally blocked, continue any remaining independent work rather than stopping the project.
5. Complete real Telegram/email receipt tests when approved real credentials/recipients become available.
6. Return to exact polygons later without reworking DaData/checkout architecture.
7. Production transition remains gated by full staging QA + explicit owner approval.

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
- [x] order notification architecture: native WooCommerce email + async Telegram via Action Scheduler
- [x] internal notification runtime test without external sends
- [ ] real email/Telegram receipt test
- [ ] final vacancy questionnaire
- [x] reviews moderation flow
- [x] explicit privacy consent at checkout/reviews
- [~] automatic real-polygon zone enforcement — DEFERRED, NON-BLOCKING
- [ ] future integrations only when explicitly required

Rule: do not invent production delivery prices, minimums, polygons, required checkout fields, payment-provider facts or missing legal/contact details.

Historical note: earlier Yandex-specific polygon-editor direction is preserved in prior project history only. Current direction is provider-independent and DaData-first; exact polygons are deferred, and a Yandex key is not a current project blocker.

## Phase 7 — payments
Current status: **LEGAL / BANK-READINESS LAYER PASS ON STAGING; ACQUIRING ITSELF NOT CONNECTED**.

Connect acquiring only after confirming the actual provider/contract, then use official provider documentation and sandbox/merchant credentials through secret-safe configuration. Do not enable production payments based only on historical bank references.

## Phase 8 — production
- backup staging and production
- regression test
- point domain to production host
- monitor checkout/orders
- do not overwrite production database with staging after live orders begin

## Historical checkpoints
Older detailed staging/catalog/admin/delivery checkpoints remain available in Git history and Project No Loss artifacts. They are evidence, not current execution blockers. In case of conflict, the current override above plus live GitHub/CI/runtime evidence wins.

# Rolls Bar — migration plan

## CURRENT EXECUTION OVERRIDE — 2026-10-09

This section is the current execution plan and supersedes stale "current next action" lines in historical checkpoints below. Historical sections are preserved for Project No Loss evidence.

### Current verified state
- Phase 1–5 staging foundation/catalog work is complete.
- Full staging catalog remains 118 product cards from 131 approved source rows.
- WordPress 7.1.3 + WooCommerce 11.1.2 are live on isolated REG.RU staging.
- DaData Suggestions is the checkout address provider on staging; real browser QA passed with fail-closed `qc_geo` handling.
- Provider country labels/raw unrestricted geography are not shown to customers.
- Native Local Pickup is working.
- Review moderation flow is runtime-verified.
- Checkout and review flows require explicit personal-data consent.
- Order-notification INTERNAL pipeline is runtime-verified; real Telegram/email receipt is still external/pending.
- Nine legal/payment-readiness pages are published and wired to canonical Woo/WordPress settings.
- Launch payment mode is deliberately **payment at receipt only**; online-card acquiring is reserved/disabled and hidden until a separate provider stage.
- Yandex Metrica integration and goal wiring are prepared, but no real counter ID is configured, so no analytics tag loads on staging.
- Deployment self-heals project theme/plugin files before WP-CLI boots active plugins.
- Production remains untouched; live acquiring and production indexing are OFF.

Latest full proof on implementation commit `a438412e7e538cf8b6ec0b001af53a6078791cb7`:
- static gate `37902087037` — SUCCESS;
- package build `37902086946` — SUCCESS;
- clean bootstrap `37902086984` — SUCCESS;
- live REG.RU deploy `37902086959` — SUCCESS;
- live runtime: `REVIEWS MODERATION RUNTIME PASS`, `ORDER NOTIFICATIONS RUNTIME PASS`, `LEGAL / PAYMENT READINESS RUNTIME PASS`, `PAYMENT LAUNCH MODE RUNTIME PASS`, `ANALYTICS PREPARATION RUNTIME PASS`, `ADDRESS SUGGESTIONS RUNTIME PASS`, catalog=118, `blog_public=0`, staging deploy PASS.

Analytics proof:
- `live_counter_configured=no`;
- synthetic valid counter loader = PASS;
- consent required before Yandex tag load;
- Webvisor OFF;
- marketing tools not configured;
- goals prepared for `add_to_cart`, `open_cart`, `begin_checkout`, `submit_order`, `purchase`, `phone_click`; delivery/pickup selection is also wired as `shipping_method_select`.

Payment proof:
- only `cod` enabled;
- public title `Оплата при получении`;
- `online_payment_state=reserved_disabled`;
- `online_card_gateway_visible=no`;
- no provider-specific gateway assumed.

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

Safety rule: NEVER invent real polygons. Courier enforcement stays OFF. Yandex/2GIS remain fallback-only unless DaData materially fails.

### Phase 6 remaining work
- [x] DaData address selection on staging checkout
- [x] fail-closed `qc_geo` policy and real checkout browser verification
- [x] reviews moderation flow + live runtime verification
- [x] explicit privacy consent for checkout + reviews
- [x] internal Woo email + async Telegram notification pipeline/runtime verification
- [x] Yandex Metrica integration + stable goal wiring prepared behind counter-ID + consent gate
- [ ] real Yandex Metrica counter ID + real goal reception verification
- [ ] real external Telegram delivery — current staging bot token/chat ID absent
- [ ] real external email receipt/deliverability test
- [ ] final vacancy questionnaire — blocked only on final client wording/input
- [~] exact delivery polygons / courier enforcement — DEFERRED, NON-BLOCKING

### Phase 7 — payment readiness / acquiring
Launch payment state:
- [x] payment at receipt enabled
- [x] unapproved core payment alternatives disabled
- [x] online-card gateway hidden/reserved
- [x] no acquiring provider assumed from historical references

Payment-readiness layer:
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
- [x] runtime verifier blocks stale `.html` links and unverified acquiring-provider claims

Online acquiring is a separate future stage and requires, before any real test:
- [ ] authoritative current acquiring-provider/contract confirmation;
- [ ] official sandbox/merchant integration details;
- [ ] credentials through a secret-safe path, never chat/Git;
- [ ] staging success/failure/cancel callback test;
- [ ] staging refund flow test where supported/required;
- [ ] explicit decision before production enablement.

Historical references to a bank are NOT enough to assume the current provider.

### Next executable path
1. Treat DaData, legal/payment readiness, receipt-only launch payment mode, reviews, privacy consent, notification internals and analytics preparation as internally complete on staging.
2. Do **not** wait on analytics counter ID, Telegram secrets, email recipient, acquiring provider or polygons; all are external-input blocks.
3. Continue independent launch-readiness work from the final TЗ: baseline WordPress security, backup/update readiness and remaining acceptance/regression checks that do not require client secrets.
4. When a real Metrica counter ID arrives, add only the ID and verify actual goal hits in Yandex Metrica before calling analytics complete.
5. When Telegram/email recipient credentials exist, perform real external delivery tests.
6. Online acquiring remains a separate later stage; launch payment stays at receipt unless owner explicitly changes scope.
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
Status: **IN PROGRESS — LIVE STAGING CORE FLOWS PASS**

Implemented / verified:
- [x] block-native additional checkout fields via WooCommerce Additional Checkout Fields API
- [x] configurable requiredness for entrance / door code / floor / apartment-office
- [x] +7 phone helper
- [x] editable promo cards connected to frontend
- [x] editable vacancies connected to careers page
- [x] Restaurant schema / transactional noindex ownership layer
- [x] client-safe settings for phone/address/socials
- [x] separate editable Composition / Ingredients field
- [x] product weight/volume + optional KBJU fields
- [x] catalog importer preserves later admin edits
- [x] HPOS-compatible operator order-list columns
- [x] WooCommerce compatibility declarations for HPOS + Cart/Checkout Blocks
- [x] native WooCommerce Blocks Local Pickup
- [x] editable delivery-area thresholds
- [x] order notification architecture + internal runtime test
- [x] reviews moderation
- [x] explicit privacy consent at checkout/reviews
- [x] Yandex Metrica code/goal preparation with consent gate
- [~] automatic real-polygon zone enforcement — DEFERRED, NON-BLOCKING

Rule: do not invent production delivery prices, polygons, required checkout fields, payment-provider facts, analytics IDs or missing legal/contact details.

## Phase 7 — payments
Current status: **LAUNCH = PAYMENT AT RECEIPT; LEGAL/BANK-READINESS PASS; ONLINE ACQUIRING NOT CONNECTED AND NOT PART OF CURRENT LAUNCH WITHOUT NEW SCOPE**.

## Phase 8 — production
- backup staging and production
- regression test
- explicit owner approval
- point domain to production host
- monitor checkout/orders
- do not overwrite production database with staging after live orders begin

## Historical checkpoints
Older detailed staging/catalog/admin/delivery checkpoints remain available in Git history and Project No Loss artifacts. They are evidence, not current execution blockers. In case of conflict, the current override above plus live GitHub/CI/runtime evidence wins.

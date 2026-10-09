# Rolls Bar — current-launch go-live decision matrix

Updated: 2026-10-09

## Purpose
This matrix separates what must be true for the **current receipt-only launch** from features that are explicitly deferred or optional. It prevents external credentials and pending client content from becoming accidental blockers when the core site can launch safely without them.

Before using this matrix, re-read live GitHub/CI/runtime evidence. `wordpress/docs/CURRENT_STATE.md` remains the factual implementation checkpoint.

## Classification rules
- **REQUIRED FOR CURRENT LAUNCH** — production transition must not be approved until this is verified.
- **APPROVED DEFERRED** — intentionally omitted from the first launch; absence is not a launch blocker.
- **OPTIONAL INTEGRATION** — useful and already prepared where possible, but can be connected after launch without changing the core order flow.
- **INTERNAL PRE-CUTOVER WORK** — no client secret/input is needed; finish it before asking the owner for production approval.

## REQUIRED FOR CURRENT LAUNCH

### Core order flow — READY ON STAGING
- catalog = 118 product cards / 131 approved source rows;
- cart / Checkout Block / order persistence;
- mobile + desktop baseline;
- Local Pickup;
- phone and additional checkout fields;
- privacy consent;
- legal/payment pages;
- receipt-only launch payment mode (`Оплата при получении`);
- WordPress order/admin lifecycle;
- staging security, backup, technical acceptance and isolated restore proof.

### Operator order email — REAL DELIVERY STILL REQUIRED
Project architecture makes WooCommerce **New order email the primary native transaction notification**. Telegram is supplemental only.

Before production approval:
1. approved recipient address must be configured in WooCommerce;
2. real mail transport/deliverability must be proven by a test order;
3. operator must actually receive the New order message;
4. Rolls Bar additional address fields must appear once, not duplicated.

Current state: internal `wp_mail` path is verified, but real receipt/deliverability is not yet proven.

### Production cutover controls — REQUIRED AT TRANSITION
Before any production mutation:
- exact release Git SHA identified;
- current production backup exists and is recoverable;
- production DB backup exists;
- rollback path written down;
- staging matches intended release;
- no secrets committed;
- production indexability/robots/canonical/sitemap behavior reviewed;
- explicit owner approval obtained.

Immediately after cutover:
- frontend smoke;
- wp-admin smoke;
- production-like test order;
- New order email receipt;
- logs/errors check;
- deployed SHA recorded.

## INTERNAL PRE-CUTOVER WORK
These are not waiting on client credentials and should be completed before production approval.

### Vacancy page fail-closed cleanup
Final questionnaire wording and application channel are still a documented pending client input. Do not invent them.

Current WordPress template visibly renders technical `Pending input` copy and a questionnaire CTA even though no final questionnaire exists. That is acceptable on staging but not production-facing content.

Required internal fix:
- while questionnaire configuration is absent, do not render the pending questionnaire block or dead application CTA;
- keep only already approved/known vacancy listing and existing contact routes;
- once client wording arrives, enable the real form without redesigning the page.

### SEO / indexability readiness
Project SEO decision still calls for one controlled SEO layer and pre-production verification.

Before production approval verify at minimum:
- one canonical SEO owner; no duplicate competing SEO/schema owners;
- editable titles/meta/canonicals;
- intended robots behavior;
- XML sitemap available;
- Restaurant/LocalBusiness schema has one owner;
- WooCommerce Product schema is not duplicated;
- cart/checkout remain noindex as intended;
- production indexability is intentionally enabled only at cutover.

Search Console connection/submission happens when the production domain is ready and does not require blocking staging development.

## APPROVED DEFERRED

### Exact delivery polygons / courier enforcement
Owner decision: continue development without waiting for exact client polygons.

Already ready:
- DaData address -> coordinates;
- `qc_geo` fail-closed safety policy;
- polygon storage/sanitation;
- point-in-polygon resolver;
- canonical thresholds 1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB.

Deferred:
- client-approved real geometry;
- boundary QA;
- automatic polygon -> threshold enforcement;
- courier zone/minimum enforcement.

Never invent polygons. Courier enforcement remains OFF until geometry is approved.

### Online acquiring
Current launch scope is payment at receipt. Online card payment is deliberately reserved/disabled/hidden.

Deferred until later:
- authoritative acquiring provider/contract;
- provider-specific credentials;
- sandbox success/failure/cancel callbacks;
- refund-flow test;
- explicit production enablement.

Historical bank references do not select a provider.

### Final vacancy questionnaire
The questionnaire itself is deferred until the client supplies final wording and receiving channel. The public page must nevertheless be production-clean (see internal cleanup above).

### Stronger CSP / Permissions-Policy
Optional hardening after a dedicated WooCommerce/browser compatibility regression. Do not deploy an aggressive CSP only to satisfy a checklist.

## OPTIONAL INTEGRATIONS

### Telegram order alert
Telegram is **supplemental**, not the canonical order record and not the primary transactional notification.

Current implementation already provides:
- async Action Scheduler delivery;
- retries/idempotency;
- no PII by default;
- status in order/admin;
- order creation continues if Telegram is unavailable.

No bot token/chat ID should be requested merely to unblock launch. Connect later unless owner explicitly promotes Telegram to a current-launch requirement.

### Yandex Metrica
Integration and goals are prepared, but without a real counter ID no Yandex tag loads.

This is safe for launch without analytics. Connect later by supplying the real counter ID, then verify actual goal reception. Do not invent an ID and do not claim analytics is working before observed hits exist.

Prepared goals:
- `add_to_cart`;
- `open_cart`;
- `begin_checkout`;
- `submit_order`;
- `purchase`;
- `phone_click`;
- `shipping_method_select`.

### Search Console
Connect and submit sitemap once the production domain is live/ready. This is an operational post-cutover SEO step, not a reason to keep staging blocked.

## Smallest remaining external input for current launch
Under the current scope, the only external operational input still clearly required **before owner production approval** is the primary New order email path:
- the operator recipient email address (configured outside public frontend copy as appropriate);
- a working mail transport/deliverability path so one real test order can be received.

Telegram credentials, Metrica ID, acquiring credentials, final vacancy questionnaire and delivery polygons are **not required merely to continue development or prepare the cutover** under the current agreed scope.

## Next execution order
1. Make the vacancy page production-safe while questionnaire input is absent.
2. Complete SEO/indexability readiness on staging without enabling production indexing.
3. Re-run only targeted regression tests for the layers changed in steps 1–2; do not repeat security/recovery suites unnecessarily.
4. Establish and prove the real New order email recipient/delivery path.
5. Prepare the production cutover + backup + rollback checklist.
6. Present final go/no-go to owner.
7. Touch production only after explicit owner approval.

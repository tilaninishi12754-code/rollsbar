# Rolls Bar — current-launch go-live decision matrix

Updated: 2026-10-09

## Purpose
This matrix separates what must be true for the **current receipt-only launch** from features that are explicitly deferred or optional. It prevents external credentials and pending client content from becoming accidental blockers when the core site can launch safely without them.

Before using this matrix, re-read live GitHub/CI/runtime evidence. `wordpress/docs/CURRENT_STATE.md` remains the detailed historical implementation checkpoint; this matrix is the current launch decision layer.

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

Current state: internal `wp_mail` path is verified, but real receipt/deliverability is not yet proven. This is the smallest clearly required external operational proof still outstanding under the current launch scope.

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

### Vacancy page fail-closed cleanup — DONE / VERIFIED
Final questionnaire wording and application channel remain a documented pending client input and were **not invented**.

Production-safe behavior is now verified on staging:
- canonical page `/rabota-v-rolls-bar/` is provisioned when absent;
- public route returns HTTP 200;
- technical `Pending input` copy is not exposed;
- dead questionnaire CTA is not exposed;
- existing vacancy listing and approved contact routes remain available;
- the real questionnaire can be enabled later when the client supplies final wording/channel.

The questionnaire itself is still deferred; the public page no longer leaks an unfinished implementation state.

### SEO / indexability readiness — DONE / VERIFIED
A single controlled SEO layer is now established on staging without enabling production indexing.

Verified owner split:
- **SEOPress 10.3** = titles/canonicals/Open Graph/XML sitemap owner;
- **RollsBar Core** = one Restaurant entity + project transactional noindex rules;
- **WooCommerce** = Product schema owner.

Safety/maintenance properties:
- SEOPress pinned to 10.3;
- auto-update disabled;
- every routine staging deploy now reasserts the pinned SEO owner after its already-verified backup gate;
- routine deploy then runs a read-only SEO ownership audit before recording deployed SHA;
- schema-overlap modules are disabled in SEOPress: Local Business, rich snippets and WooCommerce schema ownership remain off there;
- SEOPress analytics/instant-indexing/robots ownership remain off;
- staging stays `blog_public=0` and `noindex`.

Routine deploy proof on commit `497ca86d6a59a09626af60a40b7618d48c4c6b38`, run `37933737320`:
- pre-mutation backup verified;
- WordPress deploy PASS;
- SEOPress 10.3 active / auto-update disabled;
- WooCommerce preserved at 11.1.2;
- catalog preserved at 118;
- `blog_public=0` preserved;
- canonical present;
- XML sitemap available;
- Open Graph title present;
- homepage Restaurant schema count = 1;
- sample product Product schema count = 1;
- cart and checkout remain noindex;
- live SEO audit PASS;
- deployed SHA marker persisted as `497ca86d6a59a09626af60a40b7618d48c4c6b38`.

Intentionally pending content:
- homepage meta description / OG description are not invented. The system records this as `pending_content_input` until approved copy exists.

Search Console connection/submission happens when the production domain is ready and does not block staging development.

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
The questionnaire itself is deferred until the client supplies final wording and receiving channel. The public vacancy page is already production-safe while this input is absent.

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
1. Read-only audit the current WooCommerce New order recipient and actual mail-transport capability; do not send to an unapproved address.
2. Establish the approved recipient and prove one real New order email is received end-to-end.
3. Prepare the production cutover + backup + rollback checklist around an exact release SHA.
4. Present final go/no-go to owner.
5. Touch production only after explicit owner approval.

Do not rerun already-passed security, backup, recovery, vacancy or SEO suites merely because a chat reconnects. Rerun only targeted checks after a material change to those layers.

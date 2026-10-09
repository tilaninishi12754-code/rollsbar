# Rolls Bar — current-launch go-live decision matrix

Updated: 2026-10-09

## Purpose
This matrix separates what must be true for the **current receipt-only launch** from features that are explicitly deferred. It follows the latest explicit owner decisions over older draft/final-TЗ wording when they conflict.

Before using this matrix, re-read live GitHub/CI/runtime evidence. `wordpress/docs/CURRENT_STATE.md` remains the detailed historical implementation checkpoint; this matrix is the current launch decision layer.

## Classification rules
- **REQUIRED FOR CURRENT LAUNCH** — production approval needs proof, the required client input, or an explicit later owner decision to defer/waive it.
- **APPROVED DEFERRED / SEPARATE WORK** — intentionally omitted from the first launch by a later explicit owner decision; absence is not a launch blocker.
- **INTERNAL PRE-CUTOVER WORK** — no client secret/input is needed; finish before asking the owner for production approval.
- A technically supplemental integration may still be a required launch deliverable. “Failure must not block checkout” does not mean “optional to deliver”.

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

### Operator New order email — EXTERNAL INPUT / DELIVERY PROOF PENDING
WooCommerce owns the primary transactional New order email.

Verified internally:
- WooCommerce `New order` email is enabled;
- internal Woo -> `wp_mail()` path is verified by an intercepted runtime test;
- REG.RU PHP `mail()` is available;
- local sendmail path/binary is available;
- no real message was sent during audit.

Read-only mail audit run `37935330502` showed the current effective recipient is merely the staging default/admin mailbox (`***@staging.rollsbar.ru`), not an explicitly approved operator recipient.

Read-only ISPmanager/DNS audit run `37935746357` showed:
- ISPmanager mail domains: 0;
- ISPmanager mailboxes: 0;
- no `rollsbar.ru` mail domain/mailbox in this panel;
- `rollsbar.ru` MX: absent;
- `rollsbar.ru` SPF: absent;
- `rollsbar.ru` DMARC: absent;
- `staging.rollsbar.ru` MX/SPF/DMARC: absent.

Therefore local sendmail capability alone is **not** accepted as end-to-end launch proof.

Before production approval:
1. obtain the actual client-approved working operator mailbox when the client provides it;
2. determine its existing mail/SMTP provider (do not invent a new mailbox/provider if the client already has one);
3. configure a reliable authenticated transport where required, with secrets outside Git/chat;
4. configure the approved recipient in WooCommerce;
5. place one real staging test order and confirm the operator actually receives it;
6. confirm the Rolls Bar additional address fields appear once, not duplicated.

### Telegram order alert — REQUIRED FOR FIRST LAUNCH / IMPLEMENTATION READY
Owner decision on 2026-10-09: Telegram remains **mandatory for the first launch**.

The architecture remains technically non-blocking: Telegram failure must never block checkout/order creation and WooCommerce remains the canonical order record.

Already implemented and verified internally:
- async Action Scheduler queue;
- retry/idempotency logic;
- failure does not block order;
- status is stored in order/admin;
- operator payload includes order number, total, fulfillment, payment title when present, full order item list, customer name, phone, address, extra address fields and customer comment;
- owner-approved PII behavior is implemented;
- intercepted staging runtime test passed without sending a real external Telegram message.

Owner privacy/content decision on 2026-10-09:
- Telegram order notification **may include customer name, phone number and delivery address**, matching the requested operator workflow in the TЗ;
- this is an approved project decision, not a pending question.

Still required before launch:
- real bot token + operator chat ID installed outside Git/chat;
- real end-to-end staging delivery proof;
- confirm the real message arrives once and contains the approved order data without unintended secrets/technical data.

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
- Telegram delivery;
- logs/errors check;
- deployed SHA recorded.

## INTERNAL PRE-CUTOVER WORK

### Client admin UX — DONE / VERIFIED
The custom Rolls Bar admin dashboard is implemented for owner/operator use.

Verified on exact deployed staging SHA `2a9c0fcf0bb07bdca4834f07ec622590b979205d` by Admin UX Staging Smoke run `37948679330`:
- dashboard is client-operational;
- 118 published products preserved;
- prominent daily actions: Orders / Products and prices / Reviews;
- secondary actions: promos, vacancies, delivery, media, settings;
- email and Telegram readiness are shown without exposing secrets;
- Telegram copy reflects the approved PII payload;
- Metrica is shown as non-required for current launch;
- production untouched.

Client-facing usage guide: `wordpress/docs/CLIENT_ADMIN_GUIDE.md`.

### Operator order workflow — DONE / VERIFIED
Self-cleaning staging smoke run `37950008575` passed against deployed SHA `2a9c0fcf0bb07bdca4834f07ec622590b979205d`.

Verified:
- operator columns: name, phone, address, delivery zone, time;
- order item list exists;
- four additional address fields are read through the WooCommerce Additional Checkout Fields storage path;
- customer comment persists;
- admin detail block renders fulfillment + extra address fields + Telegram state;
- temporary test order stayed pending only;
- no external email sent;
- no external Telegram sent;
- temporary order cleanup PASS;
- remaining smoke orders = 0;
- production untouched.

### Vacancy page fail-closed cleanup — DONE / VERIFIED
Final questionnaire wording and application channel remain a documented pending client input and were **not invented**.

Production-safe behavior is verified on staging:
- canonical page `/rabota-v-rolls-bar/` is provisioned when absent;
- public route returns HTTP 200;
- technical `Pending input` copy is not exposed;
- dead questionnaire CTA is not exposed;
- existing vacancy listing and approved contact routes remain available;
- the real questionnaire can be enabled later when the client supplies final wording/channel.

### SEO / indexability readiness — DONE / VERIFIED
A single controlled SEO layer is established on staging without enabling production indexing.

Verified owner split:
- **SEOPress 10.3** = titles/canonicals/Open Graph/XML sitemap owner;
- **RollsBar Core** = one Restaurant entity + project transactional noindex rules;
- **WooCommerce** = Product schema owner.

Routine deploy proof on commit `497ca86d6a59a09626af60a40b7618d48c4c6b38`, run `37933737320`:
- pre-mutation backup verified;
- SEOPress 10.3 active / auto-update disabled;
- WooCommerce 11.1.2 and catalog 118 preserved;
- `blog_public=0` preserved;
- canonical + XML sitemap + Open Graph title present;
- homepage Restaurant schema count = 1;
- sample product Product schema count = 1;
- cart and checkout remain noindex;
- live SEO audit PASS;
- deployed SHA marker persisted.

Intentionally pending content:
- homepage meta description / OG description are not invented. They remain `pending_content_input` until approved copy exists.

Search Console connection/submission happens when the production domain is ready.

## APPROVED DEFERRED / SEPARATE WORK

### Yandex Metrica — DEFERRED / SEPARATE PAID WORK
Owner decision on 2026-10-09 supersedes the older TЗ wording for the first-launch acceptance scope: Yandex Metrica was not separately agreed with the client and **does not block the first launch**. If the client wants analytics, it can be connected as separate paid work.

Keep the prepared integration dormant:
- counter-ID setting remains available;
- no ID => no Yandex request/tag;
- consent gate remains in place;
- Webvisor OFF;
- advertising/marketing tools OFF;
- prepared goals remain in code for a later analytics task.

Do not invent/create a counter on the client's behalf without a separate request and access/ownership decision.

### Exact delivery polygons / courier enforcement
Later explicit owner decision: continue development without waiting for exact client polygons.

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
Current launch is payment at receipt. Online card payment is deliberately reserved/disabled/hidden.

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
Optional hardening after a dedicated WooCommerce/browser compatibility regression. Do not deploy an aggressive CSP merely to satisfy a checklist.

## External inputs actually missing now
Do not ask for payment credentials, polygons, Metrica or vacancy copy merely to continue development.

For the current first launch, the still-missing external inputs/proofs are:
1. **Working operator e-mail address + its real mail/SMTP provider/access path.** The owner will provide the address when the client sends it. Do not paste SMTP passwords into chat; secrets go into a secure secret store once the provider is known.
2. **Telegram bot/chat access** for a real staging delivery test. Bot token must never be pasted into chat/Git.

Telegram PII approval is resolved and already implemented: name, phone and delivery address are approved for the operator notification.
Yandex Metrica is not a first-launch blocker.

Consolidated client request/checklist: `wordpress/docs/CLIENT_INPUTS_PENDING.md`.

## Next execution order
1. Keep production untouched.
2. Wait for the client-supplied operator e-mail and Telegram access; do not invent substitutes.
3. Configure and prove real email delivery on staging.
4. Configure and prove real Telegram delivery on staging.
5. Run only targeted regression after these external integrations.
6. Freeze exact release SHA.
7. Present final go/no-go to owner.
8. Touch production only after explicit owner approval.

Do not rerun already-passed security, backup, recovery, vacancy, SEO, Admin UX or operator-workflow suites merely because a chat reconnects. Rerun only targeted checks after a material change to those layers.

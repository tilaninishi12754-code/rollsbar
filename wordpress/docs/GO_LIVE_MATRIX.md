# Rolls Bar — current-launch go-live decision matrix

Updated: 2026-10-09

## Purpose
This matrix separates what must be true for the **current receipt-only launch** from features that are explicitly deferred. It must follow explicit owner decisions and the final client requirements; architecture documents may make a channel non-blocking technically without making that client requirement optional.

Before using this matrix, re-read live GitHub/CI/runtime evidence. `wordpress/docs/CURRENT_STATE.md` remains the detailed historical implementation checkpoint; this matrix is the current launch decision layer.

## Classification rules
- **REQUIRED FOR CURRENT LAUNCH** — final client requirement or explicit owner requirement. Production approval needs proof, the required client input, or an explicit owner decision to defer/waive it.
- **APPROVED DEFERRED** — intentionally omitted from the first launch by a later explicit owner decision; absence is not a launch blocker.
- **INTERNAL PRE-CUTOVER WORK** — no client secret/input is needed; finish before asking the owner for production approval.
- A technically supplemental integration may still be a launch deliverable. “Failure must not block checkout” does not mean “optional to deliver”.

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
1. obtain the actual client-approved working operator mailbox;
2. determine its existing mail/SMTP provider (do not invent a new mailbox/provider if the client already has one);
3. configure a reliable authenticated transport where required, with secrets outside Git/chat;
4. configure the approved recipient in WooCommerce;
5. place one real staging test order and confirm the operator actually receives it;
6. confirm the four Rolls Bar additional address fields appear once, not duplicated.

### Telegram order alert — REQUIRED CLIENT DELIVERABLE, TECHNICALLY NON-BLOCKING
The final client specification says the operator receives each order by **e-mail and Telegram** at launch. The architecture still correctly keeps Telegram supplemental technically: Telegram failure must never block checkout/order creation and WooCommerce remains the canonical order record.

Already verified internally:
- async Action Scheduler queue;
- retry/idempotency logic;
- failure does not block order;
- status is stored in order/admin;
- default Telegram payload excludes PII unless a separate explicit privacy/business decision enables it.

Still required for the agreed launch unless the owner explicitly defers it:
- real bot token + operator chat ID supplied outside Git/chat;
- real end-to-end staging delivery proof;
- resolve the client-TZ-vs-privacy difference: final client wording expects name/phone/address in Telegram, while current safe implementation hides PII by default. Do not silently enable PII; obtain explicit owner/client decision first.

### Yandex Metrica — REQUIRED BY FINAL TЗ, CLIENT COUNTER PENDING
The final client specification says to connect Yandex Metrica after receiving the client's counter and configure goals.

Already ready:
- counter-ID setting;
- no ID => no Yandex request/tag;
- explicit analytics consent gate;
- Webvisor OFF;
- advertising/marketing tools OFF;
- prepared goals: `add_to_cart`, `open_cart`, `begin_checkout`, `submit_order`, `purchase`, `phone_click`, `shipping_method_select`.

Still required unless the owner explicitly defers it:
- real client counter ID;
- configure the corresponding goals in Metrica;
- observe real staging/production-safe test hits before claiming analytics works.

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
- Telegram delivery if it remains in launch scope;
- analytics validation if the counter has been supplied;
- logs/errors check;
- deployed SHA recorded.

## INTERNAL PRE-CUTOVER WORK

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

## APPROVED DEFERRED

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
Do not ask for payment credentials, polygons or vacancy copy merely to continue development.

For the current launch contract, the still-missing external inputs/proofs are:
1. **Working operator e-mail address + its real mail/SMTP provider/access path.** Do not paste SMTP passwords in chat; secrets must be installed through a secure secret store once provider-specific names are defined.
2. **Telegram bot/chat access** for a real staging delivery test, unless the owner explicitly changes the client requirement. Bot token must never be pasted into chat/Git.
3. **Yandex Metrica counter ID**, unless the owner explicitly defers analytics. The counter ID itself is not a secret.
4. **Explicit decision on Telegram PII** because the final TЗ asks for name/phone/address but the current privacy-safe implementation intentionally hides them.

## Next execution order
1. Prepare the production cutover + backup + rollback runbook without touching production.
2. Obtain only the external inputs above that remain in launch scope.
3. Configure and prove real email delivery on staging.
4. Configure and prove Telegram delivery if retained in launch scope.
5. Configure real Metrica counter/goals if retained in launch scope.
6. Freeze exact release SHA and run only targeted regression after these changes.
7. Present final go/no-go to owner.
8. Touch production only after explicit owner approval.

Do not rerun already-passed security, backup, recovery, vacancy or SEO suites merely because a chat reconnects. Rerun only targeted checks after a material change to those layers.

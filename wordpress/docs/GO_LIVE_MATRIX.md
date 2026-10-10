# Rolls Bar — current-launch go-live decision matrix

Updated: 2026-10-10

## Purpose
This matrix is the current launch decision layer. It follows the latest explicit owner/client decisions over older TЗ/checkpoint wording when they conflict. Historical implementation evidence remains in `wordpress/docs/CURRENT_STATE.md` and Git/CI history.

Before any consequential implementation or production change, re-read live GitHub/CI/runtime evidence.

## Latest owner/client decisions — 2026-10-10
- Telegram is **no longer required for launch**. The client explicitly replaced Telegram order alerts with **MAX**.
- MAX feasibility is confirmed from the current official MAX Bot API, but the Rolls Bar MAX integration is **not implemented or end-to-end verified yet**.
- For the first real e-mail test, use temporary staging recipient `tilaninishi12754@gmail.com`. This is a test recipient, not automatically the final production operator mailbox.
- The client supplied a delivery-tier table with thresholds 1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB. The table is useful source data but is **not exact polygon geometry**.
- Vacancy questionnaire remains deferred; no new vacancy input is required now.
- Yandex Metrica remains separate/deferred work. Online acquiring remains a later phase.

## REQUIRED FOR CURRENT LAUNCH

### Core order flow — READY ON STAGING
Already verified on staging:
- catalog = 118 product cards / 131 approved source rows;
- cart / Checkout Block / order persistence;
- mobile + desktop functional baseline;
- Local Pickup;
- phone and additional checkout fields;
- privacy consent;
- legal/payment pages;
- receipt-only launch payment mode (`Оплата при получении`);
- WordPress order/admin lifecycle;
- staging security, backup, technical acceptance and isolated restore proof.

Visual parity with the immutable approved frontend baseline is a separate active frontend pass and must be completed/verified before final owner go-live approval.

### Operator New order email — TEST RECIPIENT KNOWN / REAL DELIVERY PROOF PENDING
WooCommerce owns the primary transactional New order email.

Verified internally:
- WooCommerce `New order` email is enabled;
- internal Woo -> `wp_mail()` path was verified by intercepted runtime test;
- REG.RU PHP `mail()` and local sendmail path are available;
- previous audit did not prove real external receipt.

Current test decision:
1. configure staging `New order` recipient as `tilaninishi12754@gmail.com`;
2. do **not** request or store a Gmail password merely to receive the message;
3. place one real staging test order;
4. verify Inbox/Spam receipt, single delivery and expected order fields;
5. only if delivery/reputation fails, choose and configure an authenticated outbound transport separately with secrets outside Git/chat.

The temporary Gmail address is for staging proof only. Final production recipient can be replaced later with the client-approved operator mailbox.

### MAX order alert — REQUIRED FOR FIRST LAUNCH / INTEGRATION PENDING
Latest client decision supersedes the previous Telegram requirement: new-order messenger alerts should go to **MAX**.

Current official MAX platform facts verified on 2026-10-10:
- MAX exposes a Bot API and `POST /messages` can send to a `user_id` or `chat_id`;
- the bot authenticates with a bot access token, not with the user's MAX account login/password;
- a bot requires a verified MAX partner profile for an RF organization, IP or self-employed person and passes moderation;
- the destination `chat_id`/`user_id` is obtained from bot events such as `bot_started` / chat events;
- token and webhook secrets must remain outside Git/chat.

Therefore **do not send or store a MAX account password** for this integration.

Implementation target:
`WooCommerce order -> async Action Scheduler -> MAX Bot API`, preserving the already-proven non-blocking notification properties: checkout/order creation must succeed even if MAX is temporarily unavailable; retries/idempotency/status tracking remain required.

Still required before launch:
1. verified MAX business/IP/self-employed profile suitable for creating the bot;
2. created/moderated MAX bot;
3. bot token installed in secure staging secret storage;
4. destination operator `user_id` or `chat_id` captured without exposing credentials;
5. real staging order -> one real MAX message;
6. verify order number, total, fulfillment, items, name, phone, address/additional address fields and comment; no unintended secrets/technical payload; no duplicate message.

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
- MAX delivery;
- logs/errors check;
- deployed SHA recorded.

## DELIVERY RULES / CLIENT TABLE — SOURCE RECEIVED, AUTOMATION NOT YET SAFE
The 2026-10-10 client spreadsheet supplies tier membership examples for the canonical thresholds:
1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB.

It contains a mix of:
- named settlements/districts;
- streets;
- landmarks;
- corridor/range phrases such as `от ... до ...`;
- approximate area descriptions.

This is useful business source material, but it is **not a polygon boundary file** and cannot be converted blindly into exact production polygons.

Observed normalization issues include duplicates/variants and at least one material ambiguity: `МАЗАНКА` appears under 3500 RUB while `Мазанка` also appears under 4000 RUB. Do not silently choose one tier.

Safe next approach:
1. normalize the spreadsheet into a machine-readable delivery register;
2. resolve unambiguous whole settlements/streets through DaData/FIAS-compatible address identifiers where possible;
3. isolate only ambiguous corridor/landmark/boundary rows for clarification;
4. optionally create draft map geometry for client review, but never invent approved borders;
5. keep automatic courier minimum/zone enforcement fail-closed until the normalized rules are approved and boundary cases are tested.

So exact polygons are **not necessarily required for every table row**, but exact enough machine-readable boundaries/rules are still required before fully automatic address -> tier enforcement can be enabled.

## INTERNAL PRE-CUTOVER WORK ALREADY VERIFIED
Do not rerun merely because a chat reconnects unless the touched layer changes:
- security / hardening;
- backup-before-mutation;
- isolated restore proof;
- SEO/indexability readiness;
- vacancy fail-closed cleanup;
- client admin UX;
- operator order workflow;
- catalog / checkout / DaData functional acceptance.

The earlier Telegram implementation remains historical code/evidence only. It is no longer the chosen launch channel and must not be presented as the client requirement.

## APPROVED DEFERRED / SEPARATE WORK
- Yandex Metrica: separate paid work, not first-launch blocker.
- Online acquiring: deferred; first launch remains payment at receipt.
- Final vacancy questionnaire: deferred until client wants/provides it.
- Stronger CSP / Permissions-Policy: optional after dedicated compatibility regression.
- Fully automatic polygon/courier enforcement: remains OFF until delivery-table normalization/approval produces safe machine-readable rules.

## External inputs actually missing now
For the current first launch:
1. **Email:** no external credential is required for the first receipt test; temporary staging recipient is known (`tilaninishi12754@gmail.com`). Authenticated outbound mail credentials are only requested if the real test proves they are needed.
2. **MAX:** verified business/IP/self-employed MAX profile + created/moderated bot + secure bot token + destination `user_id`/`chat_id` for real staging delivery proof.
3. **Delivery:** clarification only for the subset of spreadsheet rows that remain ambiguous after normalization; do not ask the client to redraw every zone before this analysis is done.

## Next execution order
1. Keep production untouched.
2. Continue the Visual Parity Pass separately against immutable `approved/site-2026-10-01`.
3. Configure the temporary Gmail staging recipient and prove one real WooCommerce New order receipt.
4. Prepare MAX bot onboarding/integration; never use the user's MAX password as an application credential.
5. Normalize the supplied delivery table and produce the smallest ambiguity list; keep courier enforcement OFF meanwhile.
6. Implement MAX by adapting the existing async notification architecture, then run targeted end-to-end MAX QA.
7. Run only targeted regression after the changed integrations/frontend layers.
8. Freeze exact release SHA.
9. Present final go/no-go to owner.
10. Touch production only after explicit owner approval.

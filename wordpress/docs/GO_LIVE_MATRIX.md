# Rolls Bar — current-launch go-live decision matrix

Updated: 2026-10-14

## Purpose
This matrix is the current launch decision layer. It follows the latest explicit owner/client decisions over older TЗ/checkpoint wording when they conflict. Historical implementation evidence remains in `wordpress/docs/CURRENT_STATE.md` and Git/CI history.

Before any consequential implementation or production change, re-read live GitHub/CI/runtime evidence.

## Latest owner/client decisions — 2026-10-14
- Telegram is **no longer required for launch**. The client explicitly replaced Telegram order alerts with **MAX**.
- MAX feasibility is confirmed from the current official MAX Bot API, but the Rolls Bar MAX integration is **not implemented or end-to-end verified yet**.
- Temporary staging recipient remains `tilaninishi12754@gmail.com`, but the first real receipt test **failed end-to-end**: WordPress reported a successful local handoff, while the owner confirmed that order №275 did not appear in Gmail Inbox/Spam/search.
- Read-only staging mail diagnostics on 2026-10-14 confirmed that WordPress currently uses native PHP `mail()` through local Exim, with no SMTP authentication and no mail-related WordPress plugin. Public DNS checks returned no MX/TXT/SPF/DMARC records for `rollsbar.ru`.
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

### Operator New order email — END-TO-END DELIVERY FAILED / AUTHENTICATED TRANSPORT REQUIRED
WooCommerce owns the primary transactional New order email.

Verified internally:
- WooCommerce `New order` email is enabled;
- staging recipient is `tilaninishi12754@gmail.com`;
- order №275 triggered the WooCommerce e-mail path;
- `wp_mail_succeeded=yes`, `wp_mail_failed=no`, and `mail_to=tilaninishi12754@gmail.com` proved only that WordPress/PHPMailer handed the message to its configured local transport without a local error;
- the owner later confirmed that no message for order №275 appeared in Gmail Inbox/Spam/search, so external delivery is **not** proven and the test is considered failed end-to-end.

Read-only transport diagnosis on 2026-10-14:
- no active SMTP/mail-delivery WordPress plugin;
- PHPMailer mode = `mail`;
- PHP sendmail path = `/usr/sbin/sendmail -t -i`;
- `/usr/sbin/sendmail` resolves to local **Exim**;
- SMTP auth is not configured;
- host identity = `server108.hosting.reg.ru`;
- staging IP = `37.140.192.67`;
- current WordPress generic From observed during diagnostics = `wordpress@staging.rollsbar.ru`;
- public DNS lookup returned no MX records for `rollsbar.ru`, no root TXT/SPF records and no `_dmarc.rollsbar.ru` TXT record.

Decision:
1. do not repeat the same unauthenticated local-Exim test;
2. configure a proper authenticated outbound SMTP/API transport for staging;
3. keep credentials outside Git/chat in secure environment/server secret storage;
4. run exactly one new staging WooCommerce `New order` test to `tilaninishi12754@gmail.com`;
5. require actual Gmail Inbox/Spam receipt before marking e-mail READY;
6. final production sender/recipient can be replaced later with client-approved mailboxes/domain mail.

For a temporary proof, the owner may use a Gmail account as authenticated SMTP sender if desired; use a dedicated Google App Password/OAuth-capable mailer rather than the normal Google account password. A dedicated transactional/domain sender remains preferable for production.

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
1. **Email:** authenticated outbound sender credentials/configuration are now required because the unauthenticated local Exim path failed real Gmail receipt. Do not use/store the normal Gmail password. If using the temporary Gmail account as sender for staging proof, enable the appropriate Google authentication method and store its secret outside Git/chat.
2. **MAX:** verified business/IP/self-employed MAX profile + created/moderated bot + secure bot token + destination `user_id`/`chat_id` for real staging delivery proof.
3. **Delivery:** clarification only for the subset of spreadsheet rows that remain ambiguous after normalization; do not ask the client to redraw every zone before this analysis is done.

## Next execution order
1. Keep production untouched.
2. Continue the Visual Parity Pass separately against immutable `approved/site-2026-10-01`.
3. Configure authenticated staging outbound mail and prove one real Gmail receipt.
4. Prepare MAX bot onboarding/integration; never use the user's MAX password as an application credential.
5. Normalize the supplied delivery table and produce the smallest ambiguity list; keep courier enforcement OFF meanwhile.
6. Implement MAX by adapting the existing async notification architecture, then run targeted end-to-end MAX QA.
7. Run only targeted regression after the changed integrations/frontend layers.
8. Freeze exact release SHA.
9. Present final go/no-go to owner.
10. Touch production only after explicit owner approval.

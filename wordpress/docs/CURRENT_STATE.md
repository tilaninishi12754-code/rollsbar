# RollsBar — CURRENT STATE / Project No Loss handoff

Updated: 2026-10-09

## Purpose
Explicit recovery checkpoint for RollsBar. Never continue from chat memory alone: first re-read this file, `MIGRATION_PLAN.md`, live branch HEAD, recent CI/runtime evidence and Todoist task `6hf5v5J535WvjJx5`.

## Source of truth order
1. Live GitHub branch/code + CI/runtime evidence
2. `wordpress/docs/MIGRATION_PLAN.md` current execution override
3. Project No Loss / Todoist task `6hf5v5J535WvjJx5`
4. Historical chats/raw only when provenance is disputed

## Git / immutable baseline
Working branch: `wordpress/migration-2026-10-01`.

Latest verified implementation deployed to real REG.RU staging before this documentation sync:
`3dd7ad2a88f970059335769459d8cf5eb76ac6b8` — self-healing deploy order + legal/payment-readiness runtime verification.

This documentation commit itself advances the branch; ALWAYS re-read live HEAD before any write.

Approved baseline is immutable:
`approved/site-2026-10-01 = a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Never modify it.

Default `main` remains infrastructure-only for address-provider comparison. Last verified HEAD:
`af6b829c6c58a072b7bd375af5b8515272c202e7`.

## Live staging — VERIFIED
`https://staging.rollsbar.ru`

Current verified runtime:
- isolated REG.RU staging site/database;
- trusted HTTPS;
- WordPress 7.1.3;
- WooCommerce 11.1.2;
- `rollsbar-theme` + `rollsbar-core` active;
- full approved catalog preserved: 118 product cards / 131 source rows;
- RUB;
- native WooCommerce Blocks Local Pickup enabled;
- DaData key configured server-side only;
- WooCommerce Coming Soon OFF for anonymous QA;
- `blog_public=0`, search indexing OFF;
- courier polygon enforcement OFF;
- live acquiring/payment gateway NOT enabled;
- production untouched.

Do NOT restore the historical 5-product smoke catalog on live staging. The 5-card state is only an isolated CI bootstrap fixture.

## Latest full CI/runtime evidence — PASS
Implementation commit `3dd7ad2a88f970059335769459d8cf5eb76ac6b8`:
- `WordPress Migration Static Gate` run `37900012834` — SUCCESS;
- `Build WordPress Staging Package` run `37900012809` — SUCCESS;
- `WordPress Staging Bootstrap Smoke` run `37900012723` — SUCCESS;
- `Deploy REG.RU RollsBar Staging WordPress` run `37900012673` — SUCCESS.

Real REG.RU deploy proves:
- `LEGAL PAGES PROVISIONED 9`;
- `LEGAL / PAYMENT READINESS RUNTIME PASS`;
- `legal_pages_published=9`;
- WooCommerce terms page = `publichnaya-oferta`;
- WordPress privacy page = `politika-konfidencialnosti`;
- checkout privacy consent = required checkbox;
- review privacy consent = required server-side + form checkbox;
- acquiring provider claim remains neutral until a real gateway is connected;
- deferred delivery-polygon enforcement is disclosed truthfully;
- `REVIEWS MODERATION RUNTIME PASS`;
- `ORDER NOTIFICATIONS RUNTIME PASS`;
- `ADDRESS SUGGESTIONS RUNTIME PASS`;
- exact `qc_geo=0 -> allow_auto_zone=yes`;
- lower precision `qc_geo=2 -> allow_auto_zone=no`;
- `country_labels_exposed=no`;
- catalog assertion = 118;
- `blog_public=0`;
- DaData server key = yes;
- Telegram server credentials = no;
- `STAGING WORDPRESS DEPLOY PASS`.

## Deployment recovery hardening — DONE
A prior failed/intermediate auto-deploy temporarily left the active staging `rollsbar-core` copy with a syntactically broken PHP file. The next deploy initially could not recover because WP-CLI booted active plugins before replacing project code.

Root cause was deployment ordering, not the legal/payment layer.

Bootstrap now self-heals project-owned code:
1. fetch exact Git commit;
2. replace `rollsbar-theme`, `rollsbar-core` and catalog files on staging;
3. only then run WP-CLI commands that boot active plugins.

The live deploy run `37900012673` proves this recovery path works: it repaired staging and completed all runtime assertions successfully.

## Order notifications — INTERNAL PIPELINE PASS / REAL DELIVERY PENDING
Architecture remains:
`WooCommerce order -> native WooCommerce email + async Telegram through Action Scheduler`.

Runtime verifier `wordpress/deploy/verify-staging-notifications.php` proves without contacting real users:
- WooCommerce new-order email reaches the `wp_mail` pipeline with non-empty subject/body;
- actionable order queues Telegram action;
- successful synthetic Telegram response -> status `sent`, attempts=1;
- duplicate send is idempotent;
- personal data is hidden from Telegram message by default;
- synthetic HTTP 500 records error and schedules retry;
- synthetic QA orders/actions are removed after the test.

Safe optional staging secret path is implemented for:
- `ROLLSBAR_TELEGRAM_BOT_TOKEN`
- `ROLLSBAR_TELEGRAM_CHAT_ID`

Secrets flow only through GitHub `staging` environment -> masked deploy runtime -> short-lived mode-0600 env -> server-side `wp-config.php`. Partial Telegram configuration is rejected. No secret values are stored in Git/browser/chat.

Current objective blocker for a true Telegram delivery test:
- both Telegram staging secrets are currently absent (`assert_telegram_server_credentials=no`).

Real email receipt is also not yet proven; only the internal WooCommerce -> `wp_mail` pipeline is proven.

Do NOT call notification delivery end-to-end complete until a real configured recipient actually receives test messages.

## Legal / payment-readiness layer — DONE ON STAGING
The approved frozen legal baseline has been migrated into editable WordPress Pages without inventing missing facts.

Published WordPress pages:
- `/pravovaya-informaciya/`
- `/rekvizity-prodavca/`
- `/publichnaya-oferta/`
- `/dostavka-i-oplata/`
- `/oplata-i-vozvrat/`
- `/politika-konfidencialnosti/`
- `/soglasie-na-obrabotku-personalnyh-dannyh/`
- `/cookies/`
- `/bezopasnost-onlajn-oplaty/`

Provisioning rules:
- baseline source comes from immutable approved commit lineage;
- pages are created only if missing and are NOT overwritten by routine deploys after admin/client edits;
- static `.html` links are converted to WordPress URLs;
- stale SberBank-specific acquiring wording is not published as current truth; public copy stays provider-neutral until actual acquiring is connected;
- Woo terms setting points to the public offer;
- WordPress privacy setting points to the privacy policy;
- footer exposes core legal/payment documents;
- generic responsive legal-page template/style exists.

Seller details verified in the approved requisites source and runtime:
- ИП Гридина Надежда Викторовна;
- ИНН 910504301819;
- ОГРНИП 325911200130902.

No missing bank-account details or final written contact email were invented.

Delivery legal copy was corrected to match actual staging behavior: thresholds/rules are prepared, but exact polygon geometry is deferred and automatic courier zone enforcement is not claimed as enabled.

## Personal-data consent — DONE ON STAGING
Approved legal baseline required consent to be a separate explicit action.

Implemented:
- Checkout Block additional field `rollsbar/privacy-consent` = required checkbox;
- server-side WooCommerce field validation enforces it;
- review form includes separate required privacy-consent checkbox linked to policy;
- review submission handler independently rejects missing/negative consent.

Runtime verifier proves checkout + review consent requirements are actually registered, not merely displayed in static markup.

## Reviews — DONE ON STAGING
- route `/otzyvy/`;
- form: name, 1–5 rating, review text, optional photo <=5 MiB, required privacy consent;
- public submission always `pending`;
- pending review not public;
- admin Publish -> public;
- no fake reviews/fake average;
- honeypot protection;
- synthetic QA review removed after runtime test.

## Checkout / DaData — DONE ON STAGING
Preferred architecture:
`DaData Suggestions -> qc_geo safety gate -> lat/lon -> [approved polygon later] -> delivery tier/minimum`.

25-address live evaluation run `37766333406`:
- result 25/25;
- country metadata `Россия / RU` 25/25;
- non-RU 0/25;
- `qc_geo=0`: 17/25;
- `qc_geo=2`: 5/25;
- `qc_geo=3`: 3/25;
- observed latency 233–737 ms, mean ~413 ms.

Real anonymous checkout browser smoke run `37775215326`, rerun job `113306962222`:
- real Woo cart -> Checkout Block;
- `Симферополь Гагарина 17`: `qc_geo=0`, coordinates returned, `allow_auto_zone=1`;
- `Дубки Раздерина 12`: `qc_geo=2`, `allow_auto_zone=0`, clarification warning shown;
- provider country labels hidden;
- no uncaught checkout JS errors.

Fail-closed policy:
- `qc_geo=0`: may enter automatic polygon lookup when approved polygons exist;
- `qc_geo>=1`: no silent zone assignment.

Yandex/2GIS remain fallback-only. A Yandex key is NOT a current blocker.

## Delivery polygons — DEFERRED / NON-BLOCKING
Owner decided development must continue without exact polygons because client cannot currently provide exact boundaries.

Already ready:
- canonical thresholds 1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB;
- editable delivery data;
- polygon storage/sanitation;
- point-in-polygon resolver;
- DaData coordinate path;
- fail-closed precision policy.

Deferred:
- exact client-approved polygons;
- boundary QA;
- polygon -> threshold enforcement;
- courier zone/minimum enforcement.

Rules:
- NEVER invent real polygons;
- courier enforcement stays OFF;
- later provide a client-safe free/open map layer if useful;
- this block must not regain critical-path status without a new owner decision.

## Current migration status
Completed / verified:
- [x] staging foundation
- [x] full catalog + Gate B
- [x] cart/checkout/mobile regression baseline
- [x] Local Pickup
- [x] DaData suggestions + coordinate resolution
- [x] fail-closed geocode precision UX
- [x] review moderation
- [x] required personal-data consent in checkout/reviews
- [x] notification internal pipeline + retry/idempotency runtime test
- [x] legal/payment-readiness WordPress pages + runtime validation
- [x] deploy self-heal order

Externally pending / deferred:
- [ ] real Telegram delivery — needs actual staging bot token + chat ID stored in GitHub `staging` secrets, never pasted into chat;
- [ ] real email receipt/deliverability test — needs approved real recipient/mail transport decision;
- [ ] actual acquiring/payment gateway — provider/contract/credentials/test flow not yet connected;
- [ ] final vacancy questionnaire — requires final client wording/input;
- [~] exact polygons/courier enforcement — DEFERRED, NON-BLOCKING.

## CURRENT NEXT ACTION
1. Treat legal/payment readiness as internally complete on staging; do NOT enable live payments yet.
2. Determine the actual acquiring provider/contract status from authoritative project/client input before writing provider-specific code. Historical references to a bank are not sufficient to assume the current provider.
3. Once provider is confirmed, obtain only the minimum official sandbox/merchant credentials through a secret-safe path and perform a staging test transaction/refund flow required by that provider.
4. Real Telegram/email delivery can be completed independently when real recipient credentials/configuration are available; it must not block unrelated development.
5. Exact polygons remain deferred.
6. Production remains untouched until full staging QA + explicit owner approval.

## Project No Loss rules
- approved baseline immutable;
- migration code stays separate from `main`;
- no secret values in chat or Git;
- no invented polygons/product facts/client wording/payment-provider facts;
- do not restore live staging to 5-product smoke catalog;
- factual GitHub/CI/runtime evidence outranks stale summaries;
- do not complete Todoist recovery task `6hf5v5J535WvjJx5` without explicit owner confirmation.

## New-chat recovery prompt
> RollsBar: восстанови состояние по Project No Loss. Не полагайся на память чата. Сначала прочитай `wordpress/docs/CURRENT_STATE.md` и текущий override в `wordpress/docs/MIGRATION_PLAN.md`, затем сверяй live HEAD `wordpress/migration-2026-10-01`, `main`, последние CI/runtime результаты и Todoist task `6hf5v5J535WvjJx5`. Фактический GitHub/CI выше старых summary. Не повторяй уже успешно завершённые операции. Полигоны сейчас DEFERRED/NON-BLOCKING. Legal/payment readiness и notification internal pipeline уже PASS; реальные внешние credentials не считать настроенными без фактического доказательства.

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
`a438412e7e538cf8b6ec0b001af53a6078791cb7` — consent-gated Yandex Metrica preparation + runtime verification on top of the verified payment/notification/legal/DaData stack.

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
- launch payment mode = payment at receipt only;
- online acquiring reserved/disabled and not visible to customers;
- Yandex Metrica integration code prepared but live counter NOT configured, therefore analytics tag does not load;
- Telegram staging credentials absent;
- production untouched.

Do NOT restore the historical 5-product smoke catalog on live staging. The 5-card state is only an isolated CI bootstrap fixture.

## Latest full CI/runtime evidence — PASS
Implementation commit `a438412e7e538cf8b6ec0b001af53a6078791cb7`:
- `WordPress Migration Static Gate` run `37902087037` — SUCCESS;
- `Build WordPress Staging Package` run `37902086946` — SUCCESS;
- `WordPress Staging Bootstrap Smoke` run `37902086984` — SUCCESS;
- `Deploy REG.RU RollsBar Staging WordPress` run `37902086959` — SUCCESS.

Real REG.RU deploy proves:
- catalog = 118 product cards / 131 source rows;
- `REVIEWS MODERATION RUNTIME PASS`;
- `ORDER NOTIFICATIONS RUNTIME PASS`;
- `LEGAL / PAYMENT READINESS RUNTIME PASS`;
- `PAYMENT LAUNCH MODE RUNTIME PASS`;
- payment-at-receipt gateway enabled with title `Оплата при получении`;
- only enabled payment gateway ID = `cod`;
- `online_payment_state=reserved_disabled`;
- `online_card_gateway_visible=no`;
- no provider-specific acquiring gateway assumed;
- `ANALYTICS PREPARATION RUNTIME PASS`;
- `live_counter_configured=no`;
- synthetic counter loader = PASS;
- analytics consent required before Yandex tag load;
- Webvisor OFF;
- marketing tools not configured;
- prepared goals: `add_to_cart`, `open_cart`, `begin_checkout`, `submit_order`, `purchase`, `phone_click`;
- extra prepared delivery-method goal: `shipping_method_select`;
- `ADDRESS SUGGESTIONS RUNTIME PASS`;
- exact `qc_geo=0 -> allow_auto_zone=yes`;
- lower precision `qc_geo=2 -> allow_auto_zone=no`;
- provider country labels exposed = no;
- `blog_public=0`;
- DaData server key = yes;
- Telegram server credentials = no;
- `STAGING WORDPRESS DEPLOY PASS`.

## Yandex Metrica — PREPARED / COUNTER ID PENDING
Final project requirements call for Yandex Metrica plus goals for cart/checkout/order/phone actions.

Implemented on staging:
- editable `metrika_counter_id` in Rolls Bar admin settings;
- invalid/non-numeric counter IDs are rejected;
- when ID is empty, no Yandex analytics JS is rendered or requested;
- when a valid ID exists, Metrica still loads only after explicit analytics consent stored in the browser;
- consent UI links to `/cookies/`;
- Webvisor disabled;
- automatic link tracking/clickmap disabled in our init configuration;
- no advertising/marketing tools configured;
- goal events prepared in code for add-to-cart, cart open, checkout start, order-submit click, successful order, phone click, and delivery/pickup method selection.

Current objective blocker for full analytics activation:
- client/order owner has not yet provided the real Yandex Metrica counter ID.

Do NOT invent a counter ID and do NOT claim real Metrica collection or goal reception until the real counter is added and goal hits are verified in Yandex Metrica.

## Deployment recovery hardening — DONE
A prior failed/intermediate auto-deploy temporarily left the active staging `rollsbar-core` copy with a syntactically broken PHP file. The next deploy initially could not recover because WP-CLI booted active plugins before replacing project code.

Bootstrap now self-heals project-owned code:
1. fetch exact Git commit;
2. replace `rollsbar-theme`, `rollsbar-core` and catalog files on staging;
3. only then run WP-CLI commands that boot active plugins.

Verified on real REG.RU staging. Do not revert this ordering.

## Order notifications — INTERNAL PIPELINE PASS / REAL DELIVERY PENDING
Architecture:
`WooCommerce order -> native WooCommerce email + async Telegram through Action Scheduler`.

Runtime verifier proves without contacting real users:
- WooCommerce new-order email reaches the `wp_mail` pipeline with non-empty subject/body;
- actionable order queues Telegram action;
- successful synthetic Telegram response -> status `sent`, attempts=1;
- duplicate send is idempotent;
- personal data is hidden from Telegram message by default;
- synthetic HTTP 500 records error and schedules retry;
- synthetic QA orders/actions are removed after the test.

Safe optional staging secrets:
- `ROLLSBAR_TELEGRAM_BOT_TOKEN`
- `ROLLSBAR_TELEGRAM_CHAT_ID`

Secrets flow only through GitHub `staging` environment -> masked deploy runtime -> short-lived mode-0600 env -> server-side `wp-config.php`. Partial Telegram configuration is rejected. Never paste these values into chat or Git.

Current blocker for true Telegram delivery: both Telegram staging secrets are absent (`assert_telegram_server_credentials=no`).

Real email receipt is also not yet proven; only the internal WooCommerce -> `wp_mail` pipeline is proven.

## Legal / payment readiness — DONE ON STAGING
Nine editable WordPress pages are published:
- `/pravovaya-informaciya/`
- `/rekvizity-prodavca/`
- `/publichnaya-oferta/`
- `/dostavka-i-oplata/`
- `/oplata-i-vozvrat/`
- `/politika-konfidencialnosti/`
- `/soglasie-na-obrabotku-personalnyh-dannyh/`
- `/cookies/`
- `/bezopasnost-onlajn-oplaty/`

Verified behavior:
- baseline comes from immutable approved lineage;
- pages are created only when missing and routine deploys do not overwrite later admin/client edits;
- Woo terms points to `publichnaya-oferta`;
- WordPress privacy points to `politika-konfidencialnosti`;
- checkout privacy consent is a required checkbox;
- review privacy consent is required in form and server-side;
- stale SberBank-specific wording is not published as current truth;
- public acquiring copy stays provider-neutral until an actual provider is connected;
- exact delivery polygon enforcement is truthfully described as deferred.

Seller details verified from approved source:
- ИП Гридина Надежда Викторовна;
- ИНН 910504301819;
- ОГРНИП 325911200130902.

No missing bank account, email, acquiring provider or other client fact was invented.

## Launch payment mode — VERIFIED
Final project scope says online acquiring is not part of the launch unless separately agreed. Current staging therefore intentionally uses payment at receipt only.

Verified on real staging:
- WooCommerce `cod` enabled;
- public title = `Оплата при получении`;
- `bacs` and `cheque` disabled;
- no other gateway enabled;
- online-card slot remains reserved/disabled;
- no current acquiring provider is assumed from historical bank references.

Actual online acquiring requires a separate future stage after authoritative provider/contract confirmation and provider-specific sandbox testing.

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
- 25/25 suggestions returned;
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

Yandex/2GIS remain fallback-only. A Yandex Maps key is NOT a current blocker.

## Delivery polygons — DEFERRED / NON-BLOCKING
Owner decided development continues without exact polygons because client cannot currently provide exact boundaries.

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

NEVER invent real polygons. Courier enforcement stays OFF. This block is non-critical until the owner changes that decision.

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
- [x] receipt-only launch payment mode + online gateway disabled
- [x] Yandex Metrica integration/goal wiring prepared with ID+consent gate
- [x] deploy self-heal order

Externally pending / deferred:
- [ ] real Yandex Metrica counter ID + live goal reception verification;
- [ ] real Telegram delivery — requires actual staging bot token + chat ID in GitHub `staging` secrets;
- [ ] real email receipt/deliverability test — requires approved recipient/mail transport decision;
- [ ] actual online acquiring — separate future stage; provider/contract/credentials/test flow not confirmed;
- [ ] final vacancy questionnaire — requires final client wording/input;
- [~] exact polygons/courier enforcement — DEFERRED, NON-BLOCKING.

## CURRENT NEXT ACTION
1. Treat analytics implementation as prepared but inactive; obtain the real Yandex Metrica counter ID later and then verify actual goal reception. This is external input and must not block unrelated work.
2. Continue independent launch-readiness work from the final TЗ, especially baseline WordPress security/backup/update readiness and any remaining acceptance tests that do not require client secrets.
3. Real Telegram/email receipt tests can be completed when approved real credentials/recipients exist.
4. Do not implement provider-specific acquiring until authoritative provider/contract status exists; launch remains payment at receipt.
5. Exact polygons remain deferred.
6. Production remains untouched until full staging QA + explicit owner approval.

## Project No Loss rules
- approved baseline immutable;
- migration code stays separate from `main`;
- no secret values in chat or Git;
- no invented polygons/product facts/client wording/payment-provider facts/analytics IDs;
- do not restore live staging to 5-product smoke catalog;
- factual GitHub/CI/runtime evidence outranks stale summaries;
- do not complete Todoist recovery task `6hf5v5J535WvjJx5` without explicit owner confirmation.

## New-chat recovery prompt
> RollsBar: восстанови состояние по Project No Loss. Не полагайся на память чата. Сначала прочитай `wordpress/docs/CURRENT_STATE.md` и текущий override в `wordpress/docs/MIGRATION_PLAN.md`, затем сверяй live HEAD `wordpress/migration-2026-10-01`, `main`, последние CI/runtime результаты и Todoist task `6hf5v5J535WvjJx5`. Фактический GitHub/CI выше старых summary. Не повторяй успешно завершённые операции. Полигоны DEFERRED/NON-BLOCKING. Launch payment = при получении. Legal/payment readiness, notification internal pipeline, DaData, reviews и analytics preparation уже PASS; реальные внешние credentials/counter IDs не считать настроенными без доказательства.

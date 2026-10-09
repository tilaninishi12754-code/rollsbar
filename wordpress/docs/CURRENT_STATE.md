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

Latest verified implementation deployed to staging:
`84ffeb0b1b59f8fab44389b967f05e14b29d6327` — reviews moderation runtime verification.

The branch has later documentation commits; always re-read live HEAD before any write.

Approved baseline is immutable:
`approved/site-2026-10-01 = a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Never modify it.

Default `main` remains infrastructure-only for address-provider comparison. Last verified HEAD:
`af6b829c6c58a072b7bd375af5b8515272c202e7`.

## Live staging — VERIFIED
`https://staging.rollsbar.ru`

Current verified runtime:
- isolated REG.RU staging site/database;
- HTTPS trusted;
- WordPress 7.1.3;
- WooCommerce 11.1.2;
- `rollsbar-theme` + `rollsbar-core` active;
- full catalog preserved: 118 product cards / 131 approved source rows;
- RUB;
- native WooCommerce Blocks Local Pickup enabled;
- DaData key configured server-side only;
- WooCommerce Coming Soon OFF for anonymous QA;
- `blog_public=0`, search indexing OFF;
- courier enforcement OFF;
- production untouched.

Do NOT restore the historical 5-product smoke catalog on live staging. The 5-card state is only an isolated CI bootstrap smoke fixture.

## Latest CI/runtime evidence — REVIEWS PASS
Implementation commit `84ffeb0b1b59f8fab44389b967f05e14b29d6327`:
- `WordPress Staging Bootstrap Smoke` run `37896840912` — SUCCESS;
- `Build WordPress Staging Package` run `37896840878` — SUCCESS;
- `WordPress Migration Static Gate` run `37896840821` — SUCCESS;
- `Deploy REG.RU RollsBar Staging WordPress` run `37896840834` — SUCCESS.

Real REG.RU deploy log proves:
- `REVIEWS MODERATION RUNTIME PASS`;
- `/otzyvy/` page published;
- new site review status = `pending`;
- pending review publicly visible = `no`;
- after admin publish, publicly visible = `yes`;
- synthetic QA review is removed by the runtime test;
- `ADDRESS SUGGESTIONS RUNTIME PASS` still passes;
- exact `qc_geo=0 -> allow_auto_zone=yes`;
- low precision `qc_geo=2 -> allow_auto_zone=no`;
- `country_labels_exposed=no`;
- catalog assertion = 118;
- `blog_public=0`;
- `STAGING WORDPRESS DEPLOY PASS`.

## Reviews — DONE ON STAGING
Approved static baseline behavior was migrated to WordPress:
- route `/otzyvy/`;
- public feed contains only published `rb_review` records;
- form fields: name, 1–5 rating, review text, optional photo up to 5 MiB;
- public submission is always created as `pending`;
- admin sees reviews inside Rolls Bar WordPress admin and explicitly publishes approved reviews;
- pending reviews are never included in the public feed;
- page does not invent reviews or a fake rating; its average is calculated only from actually published site reviews;
- basic honeypot protection is present;
- photo upload uses WordPress media handling.

Do not repeat this implementation unless a new requirement/regression appears.

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
- `qc_geo=1`: no silent zone assignment;
- `qc_geo=2/3/4`: no automatic zone; clarify/fallback/manual-point flow only;
- `qc_geo=5` / missing / invalid: no zone lookup.

Yandex/2GIS are fallback-only if DaData later materially fails. A Yandex API key is NOT a current project blocker.

## Delivery polygons — DEFERRED / NON-BLOCKING
User explicitly decided development must continue without exact polygons because the client cannot currently provide exact boundaries.

Already ready:
- 7 canonical minimum/free-delivery thresholds: 1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB;
- editable delivery data;
- polygon storage/sanitation;
- point-in-polygon resolver verified with synthetic inside/outside tests;
- DaData coordinate path;
- qc_geo fail-closed policy.

Not ready and intentionally deferred:
- exact client-approved production polygons;
- boundary-case QA against real geometry;
- final polygon -> threshold enforcement;
- courier zone/minimum enforcement.

Rules:
- NEVER invent real delivery polygons;
- courier enforcement stays OFF;
- continued site development is allowed and expected;
- later provide a client-safe free/open map layer if useful so the client can draw/correct polygons themselves;
- returning to this block later does not require rebuilding DaData/checkout.

## Important recovered discrepancy
Earlier anonymous checkout tests failed because WooCommerce Coming Soon hid Checkout Block. It was not a DaData failure. Staging bootstrap now enforces:
- `woocommerce_coming_soon=no`;
- `woocommerce_store_pages_only=no`;
while keeping `blog_public=0`.

## Current Phase 6 remaining items
- [x] full catalog / Gate B
- [x] DaData checkout suggestions + coordinate resolution
- [x] fail-closed geocode precision UX
- [x] moderated site reviews
- [ ] real WooCommerce email + Telegram order-notification delivery test
- [ ] final vacancy questionnaire — requires final client wording/input
- [~] exact polygons / courier enforcement — DEFERRED, NON-BLOCKING
- [ ] future integrations only when explicitly required

Existing notification architecture is already present: native WooCommerce email + asynchronous Telegram via Action Scheduler. Do not claim end-to-end delivery until a real staging recipient/Telegram configuration is tested.

## CURRENT NEXT ACTION
1. Inspect and validate the existing order-notification architecture against current WooCommerce/staging behavior.
2. Complete everything testable without exposing secrets.
3. Identify the exact smallest external input/credential required for a true Telegram/email delivery test.
4. If real notification delivery is externally blocked, do NOT stop development; move to the next independent payment/readiness work and return later.
5. Exact polygons remain deferred and must not regain critical-path status without a new owner decision.
6. Production remains untouched until full staging QA + explicit owner approval.

## Project No Loss rules
- approved baseline immutable;
- migration code stays separate from `main`;
- no secret values in chat or Git;
- no invented polygons/product facts/client wording;
- do not restore live staging to 5-product smoke catalog;
- factual GitHub/CI/runtime evidence outranks stale summaries;
- do not complete Todoist recovery task `6hf5v5J535WvjJx5` without explicit owner confirmation.

## New-chat recovery prompt
> RollsBar: восстанови состояние по Project No Loss. Не полагайся на память чата. Сначала прочитай `wordpress/docs/CURRENT_STATE.md` и текущий override в `wordpress/docs/MIGRATION_PLAN.md`, затем сверяй live HEAD `wordpress/migration-2026-10-01`, `main`, последние CI/runtime результаты и Todoist task `6hf5v5J535WvjJx5`. Фактический GitHub/CI выше старых summary. Не повторяй уже успешно завершённые операции. Полигоны сейчас DEFERRED/NON-BLOCKING.

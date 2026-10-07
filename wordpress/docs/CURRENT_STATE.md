# RollsBar — CURRENT STATE / Project No Loss handoff

Updated: 2026-10-07

## Purpose
This file is the explicit handoff checkpoint for continuing RollsBar in a new ChatGPT chat or agent session. Do not rely on chat memory alone. First verify this file against the live branch HEAD and recent CI before continuing.

## Source of truth order
1. GitHub branch + actual code + CI/runtime evidence
2. `wordpress/docs/MIGRATION_PLAN.md`
3. Project No Loss / Todoist checkpoint task `6hf5v5J535WvjJx5`
4. Historical chats/raw source only when provenance or a decision is disputed

## Current Git state
Working branch: `wordpress/migration-2026-10-01`.
The working branch now includes the DaData-first provider-evaluation update; always re-read its live HEAD before continuing.

Approved baseline remains:
`approved/site-2026-10-01 = a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Do not modify it.

Default branch `main` contains one infrastructure-only manual Actions launcher for address-provider evaluation. It does not contain migration code and does not deploy anything. The launcher checks out `wordpress/migration-2026-10-01`, uses environment `staging`, has `contents: read`, and only creates evidence artifacts.

A new session MUST read both the working branch HEAD and current `main` HEAD again because later commits may exist.

## Live staging
`https://staging.rollsbar.ru`

Verified state:
- isolated REG.RU staging site/database;
- trusted HTTPS;
- WordPress 7.1.2;
- WooCommerce 11.1.2;
- `rollsbar-theme` active;
- `rollsbar-core` active;
- staging remains non-indexed;
- production site/domain has not been migrated over staging.

## Catalog
Full approved catalog is promoted on staging:
- 118 product cards;
- 131 approved source rows;
- repeat import remains 118 products (stable-SKU/idempotency proven).

Do NOT restore the historical 5-product smoke state during routine deploys.

## Full live Gate B — PASS
Desktop and mobile browser tests have verified on the full 118-product catalog:
- HTTPS home/cart/checkout;
- add-to-cart and Store API session persistence;
- RUB currency/ruble prices;
- visible checkout control;
- checkout Additional Fields: entrance, door/intercom code, floor, apartment/office;
- phone starts with `+7` and leading `8` normalizes to `+7`;
- no manual delivery-zone selector;
- native WooCommerce Blocks Local Pickup visible;
- historical mobile sticky-cart / checkout-button overlap regression absent;
- no uncaught page JS errors.

## Delivery rules
Seven confirmed minimum/free-delivery thresholds remain canonical:
1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB.

They are editable from WordPress and rendered from the same source data.
No exact production polygon boundaries have been invented.

## Delivery polygons / map
Implemented in `rollsbar-core`:
- validated polygon storage;
- client-safe polygon editor shell in Rolls Bar -> Delivery;
- polygon vertex limit and coordinate sanitation;
- point-in-polygon resolver;
- clean runtime tests for inside/outside resolution;
- the existing Yandex editor adapter remains dormant until explicitly configured, so current checkout behavior is unchanged without a key.

## Address provider direction — DADATA FIRST
Owner clarified the business constraint on 2026-10-07: do not pay for Yandex/2GIS unless the low-cost path fails on real addresses.

Preferred checkout architecture is now:
`DaData Suggestions -> lat/lon -> RollsBar polygon resolver -> delivery tier/minimum`.

Important distinction:
- DaData `Suggestions` has a free tier up to 10,000 requests/day;
- selected address suggestions already expose `geo_lat`, `geo_lon` and `qc_geo`;
- therefore RollsBar does NOT need DaData's separately billed geocoding endpoint for the normal checkout flow;
- Yandex and 2GIS are fallback comparators only, not equal first-choice candidates.

Country-label requirement:
- production UI must NOT render provider country labels;
- do not render raw `country` / `country_iso_code` / unrestricted provider strings as customer-facing geography;
- build the visible checkout address only from approved local components such as locality/city, street and house;
- the backend may inspect provider country metadata only as a diagnostic/safety signal;
- before production integration, verify the real 25-address Crimean test set and reject/flag unexpected provider country classification rather than silently trusting it.

This is a product/UI handling rule, not a geopolitical assertion. Provider-returned metadata is treated as implementation data only.

## Provider evaluation harness — READY, LIVE DADATA RUN PENDING
Working branch contains:
- `wordpress/tools/compare_address_providers.py`;
- `wordpress/data/address-provider-test-addresses.json` with 25 publicly verified address probes spanning central Simferopol and outer delivery localities.

The evaluator is now DaData-first:
- DaData can be tested alone with `ROLLSBAR_DADATA_API_KEY`;
- Yandex/2GIS are optional fallback comparators if keys are available;
- DaData output records `country`, `country_iso`, `qc_geo`, coordinates and latency;
- any non-`RU` DaData country code is explicitly flagged as `COUNTRY_MISMATCH` in evidence;
- country fields are diagnostic only and must not be displayed in production checkout.

Default branch `main` contains:
- `.github/workflows/compare-address-providers.yml` as the manual launcher required for GitHub `workflow_dispatch` visibility.

The launcher:
- checks out only `wordpress/migration-2026-10-01` for actual test code/data;
- uses GitHub environment `staging`;
- has read-only repository permission;
- defaults to the verified 25-address repository set, with an optional JSON override;
- writes Markdown + JSON evidence artifacts;
- does NOT deploy, modify checkout or enable courier logic;
- never prints API secret values.

Expected staging secret names:
- preferred/required next: `ROLLSBAR_DADATA_API_KEY`;
- optional fallback comparison only: `ROLLSBAR_YANDEX_GEOCODER_KEY`;
- optional fallback comparison only: `ROLLSBAR_2GIS_API_KEY`.

## Important unresolved inputs / decisions
- DaData API key in client/user-controlled GitHub staging environment;
- DaData result on the 25-address Crimean test set, including country classification and coordinate precision;
- exact client-drawn polygon boundaries;
- whether a separate map-rendering layer is needed for client polygon editing after DaData address lookup is accepted;
- final vacancy questionnaire;
- source weights/volumes not present in approved source;
- owner/client decision whether checkout should split Street and House;
- no WOK remodel beyond the already approved model without a new explicit decision;
- real email/Telegram delivery test and production credentials;
- acquiring/payment phase later.

## NEXT ACTION
1. Create/use a DaData account on the free Suggestions tariff and place only its API key into GitHub environment `staging` as `ROLLSBAR_DADATA_API_KEY`. Never put the key in chat or Git.
2. Run GitHub Actions -> `Compare address providers`; leave the optional address override empty.
3. Review all 25 DaData results for: exact/locality precision (`qc_geo`), usable coordinates and country classification. Any non-RU code is a hard review flag.
4. If DaData passes, use it as the checkout address/coordinate provider and keep country hidden from customer-facing UI.
5. Only if DaData materially fails coverage/precision, evaluate paid Yandex/2GIS fallback.
6. Then live-test polygon editing on staging, have the client draw/correct exact polygons, and only after that enable `address -> coordinates -> polygon -> confirmed minimum threshold` courier logic.

## New-chat recovery protocol
In a new chat inside the same ChatGPT Project, the first instruction should be:

> RollsBar: восстанови состояние по Project No Loss. Не полагайся на память чата. Сначала прочитай `wordpress/docs/CURRENT_STATE.md` и `wordpress/docs/MIGRATION_PLAN.md`, затем сверяй текущий HEAD ветки `wordpress/migration-2026-10-01`, текущий `main`, последние CI/runtime результаты и Todoist task `6hf5v5J535WvjJx5`. Если есть расхождение, фактический GitHub/CI и канонические Project No Loss артефакты выше старых summary. Сначала покажи восстановленный checkpoint и NEXT ACTION, ничего успешного не повторяй, затем продолжай.

Project memory may help locate context, but it is not considered audit proof of No Loss.

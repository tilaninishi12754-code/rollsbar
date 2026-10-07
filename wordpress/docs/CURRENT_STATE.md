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
The working branch advanced through the provider-comparison harness and verified-address dataset work; always re-read its live HEAD before continuing.

Approved baseline remains:
`approved/site-2026-10-01 = a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Do not modify it.

Default branch `main` now contains one infrastructure-only manual Actions launcher for the provider comparison. It does not contain the migration code and does not deploy anything. The launcher explicitly checks out `wordpress/migration-2026-10-01`, uses environment `staging`, has `contents: read`, and only creates comparison evidence artifacts.

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

## Map/geocoder provider decision — OPEN
Do NOT assume Yandex is final merely because the first editor shell targets Yandex.

Current architecture intentionally keeps business logic provider-independent:
`address provider -> lat/lon -> RollsBar polygon resolver -> delivery tier/minimum`.

Before committing to a provider, compare Yandex Maps, 2GIS and DaData on:
- licensing/cost for a small commercial restaurant site;
- address accuracy in Simferopol and outer delivery areas;
- client-safe polygon editing;
- ability to reject low-accuracy geocodes rather than guess a zone;
- operational ownership under a client-owned account.

## Provider comparison harness — READY, NOT YET RUN WITH LIVE KEYS
Working branch contains:
- `wordpress/tools/compare_address_providers.py`;
- `wordpress/data/address-provider-test-addresses.json` with 25 publicly verified address probes spanning central Simferopol and outer delivery localities.

Default branch `main` contains:
- `.github/workflows/compare-address-providers.yml` as the manual launcher required for GitHub `workflow_dispatch` visibility.

The launcher:
- checks out only `wordpress/migration-2026-10-01` for the actual test code/data;
- uses GitHub environment `staging`;
- has read-only repository permission;
- defaults to the 25-address repository set, with an optional JSON override;
- compares whichever of Yandex / 2GIS / DaData credentials are present;
- records normalized address, coordinates, provider precision signal, latency and pairwise coordinate deltas;
- writes Markdown + JSON evidence artifacts;
- does NOT deploy, modify checkout, enable courier logic or choose a provider automatically;
- never prints API secret values.

Expected staging secret names:
- `ROLLSBAR_YANDEX_GEOCODER_KEY`;
- `ROLLSBAR_2GIS_API_KEY`;
- `ROLLSBAR_DADATA_API_KEY`.

The comparison is not complete until the workflow is run with actual provider credentials and its output is reviewed.

## Important unresolved inputs / decisions
- actual provider test credentials in client/user-controlled GitHub staging environment;
- provider comparison result on the 25-address set;
- exact client-drawn polygon boundaries;
- final map/geocoder provider + client-owned API account/key;
- final vacancy questionnaire;
- source weights/volumes not present in approved source;
- owner/client decision whether checkout should split Street and House;
- no WOK remodel beyond the already approved model without a new explicit decision;
- real email/Telegram delivery test and production credentials;
- acquiring/payment phase later.

## NEXT ACTION
1. Add whichever provider test credentials are available to GitHub environment `staging` under the secret names above. Never put keys in chat or Git.
2. From GitHub Actions run `Compare address providers`; leave the optional address override empty to use the verified 25-address set.
3. Preserve and review the Markdown/JSON comparison evidence.
4. Choose provider only after reviewing real address accuracy + official licensing/cost.
5. Configure the selected provider in a client-owned account/secret and live-test the WordPress polygon editor on staging.
6. Have client draw/correct exact polygons on staging.
7. Only then wire `address -> coordinates -> polygon -> confirmed minimum threshold` and enable courier logic.

## New-chat recovery protocol
In a new chat inside the same ChatGPT Project, the first instruction should be:

> RollsBar: восстанови состояние по Project No Loss. Не полагайся на память чата. Сначала прочитай `wordpress/docs/CURRENT_STATE.md` и `wordpress/docs/MIGRATION_PLAN.md`, затем сверяй текущий HEAD ветки `wordpress/migration-2026-10-01`, текущий `main`, последние CI/runtime результаты и Todoist task `6hf5v5J535WvjJx5`. Если есть расхождение, фактический GitHub/CI и канонические Project No Loss артефакты выше старых summary. Сначала покажи восстановленный checkpoint и NEXT ACTION, ничего успешного не повторяй, затем продолжай.

Project memory may help locate context, but it is not considered audit proof of No Loss.

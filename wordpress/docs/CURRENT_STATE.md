# RollsBar — CURRENT STATE / Project No Loss handoff

Updated: 2026-10-08

## Purpose
This file is the explicit handoff checkpoint for continuing RollsBar in a new ChatGPT chat or agent session. Do not rely on chat memory alone. First verify this file against the live branch HEAD and recent CI before continuing.

## Source of truth order
1. GitHub branch + actual code + CI/runtime evidence
2. `wordpress/docs/MIGRATION_PLAN.md`
3. Project No Loss / Todoist checkpoint task `6hf5v5J535WvjJx5`
4. Historical chats/raw source only when provenance or a decision is disputed

## Current Git state
Working branch: `wordpress/migration-2026-10-01`.

Approved baseline remains:
`approved/site-2026-10-01 = a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Do not modify it.

Default branch `main` contains one infrastructure-only manual Actions launcher for address-provider evaluation. It does not contain migration code and does not deploy anything. The launcher checks out `wordpress/migration-2026-10-01`, uses environment `staging`, has `contents: read`, and only creates evidence artifacts.

A new session MUST re-read both the working branch HEAD and current `main` HEAD because later commits may exist.

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

## Catalog / Gate B
- full approved catalog: 118 product cards from 131 approved source rows;
- repeat import remains 118 products;
- desktop + mobile Gate B PASS;
- do NOT restore the historical 5-product smoke state.

## Delivery rules
Seven confirmed minimum/free-delivery thresholds remain canonical:
1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB.

Validated polygon storage and point-in-polygon resolver exist. Exact production polygon boundaries have NOT been invented. Courier enforcement remains off.

## Address provider direction — DADATA FIRST
Owner constraint: do not pay for Yandex/2GIS unless the low-cost path materially fails.

Preferred checkout architecture:
`DaData Suggestions -> qc_geo safety gate -> lat/lon -> RollsBar polygon resolver -> delivery tier/minimum`.

DaData Suggestions is the intended address/coordinate source. Country metadata is diagnostic only; production checkout must not render provider country labels or raw unrestricted provider strings. Visible address should be built from approved local components such as locality/city, street and house.

Yandex/2GIS remain fallback options only if DaData coverage/precision proves inadequate.

## LIVE DADATA 25-ADDRESS EVALUATION — PASS WITH PRECISION CAVEAT
GitHub Actions run:
- workflow: `Compare address providers`;
- run ID: `37766333406`;
- event: `workflow_dispatch`;
- conclusion: `success`;
- launcher branch/head: `main` / `af6b829c6c58a072b7bd375af5b8515272c202e7`;
- tested migration commit: `d4ff3fcf2eb6ca31cbd519c83f4dea145d0dc193`;
- artifact: `rollsbar-address-provider-comparison` (artifact ID `11543779451`).

Observed results on the verified 25-address Simferopol / outer-area set:
- DaData returned a result for 25/25 addresses;
- country metadata returned `Россия` / `RU` for 25/25;
- non-RU country-code results: 0/25;
- `qc_geo=0`: 17/25;
- `qc_geo=2`: 5/25;
- `qc_geo=3`: 3/25;
- observed API latency: 233–737 ms, mean ~413 ms.

Examples of weaker precision from the evidence:
- Dubki — `qc_geo=2`;
- Molodyozhnoye (Crimean Spring St) — `qc_geo=3`;
- Agrarnoye (Parkovaya St) — `qc_geo=2`;
- Denisovka — `qc_geo=3`;
- Urozhaynoye — `qc_geo=2`;
- Fontany — `qc_geo=2`;
- Mazanka — `qc_geo=3`.

## Geocode precision policy — FIXED / FAIL-CLOSED
DaData documentation defines:
- `0` exact house;
- `1` nearest house;
- `2` street;
- `3` settlement;
- `4` city;
- `5` coordinates not determined.

RollsBar safety rule is now explicit and implemented in `RollsBar_Geocode_Policy`:
- `qc_geo=0`: may automatically resolve a polygon/zone once approved polygons exist;
- `qc_geo=1`: must NOT silently auto-assign; require customer confirmation or an approved map-pin flow;
- `qc_geo=2/3/4`: must NOT auto-assign; require address clarification or approved fallback/manual-point flow;
- `qc_geo=5`, missing or invalid: no zone lookup.

Default is fail-closed. Only exact-house precision can silently affect delivery-zone/minimum logic.

This guard is prepared before checkout integration. It does not enable courier delivery and does not change production behavior.

## Important unresolved inputs / decisions
- exact production polygon boundaries from the client;
- staging UX for low-precision address clarification / optional manual pin;
- whether a separate free/open map-rendering layer is needed for client polygon editing;
- checkout Street/House split decision;
- real email/Telegram delivery test and production credentials;
- acquiring/payment phase later.

## NEXT ACTION
1. Keep DaData as the preferred checkout address provider based on the successful 25/25 live run.
2. Wire DaData Suggestions into a staging-only address-selection UX while keeping courier enforcement OFF.
3. Test exact and low-precision selections against the new fail-closed policy.
4. Prepare a client-safe free/open map layer for polygon editing if practical, then have the client draw/correct exact delivery polygons.
5. Only after those checks wire `address -> coordinates -> polygon -> confirmed threshold` into checkout and enable courier logic.
6. Paid Yandex/2GIS should be considered only if the DaData precision caveat cannot be handled acceptably.

## New-chat recovery protocol
In a new chat inside the same ChatGPT Project, the first instruction should be:

> RollsBar: восстанови состояние по Project No Loss. Не полагайся на память чата. Сначала прочитай `wordpress/docs/CURRENT_STATE.md` и `wordpress/docs/MIGRATION_PLAN.md`, затем сверяй текущий HEAD ветки `wordpress/migration-2026-10-01`, текущий `main`, последние CI/runtime результаты и Todoist task `6hf5v5J535WvjJx5`. Если есть расхождение, фактический GitHub/CI и канонические Project No Loss артефакты выше старых summary. Сначала покажи восстановленный checkpoint и NEXT ACTION, ничего успешного не повторяй, затем продолжай.

Project memory may help locate context, but it is not considered audit proof of No Loss.

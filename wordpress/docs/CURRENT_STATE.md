# RollsBar — CURRENT STATE / Project No Loss handoff

Updated: 2026-10-08

## Purpose
This file is the explicit handoff checkpoint for continuing RollsBar in a new ChatGPT chat or agent session. Do not rely on chat memory alone. First verify this file against the live branch HEAD and recent CI/runtime evidence before doing any write or deploy.

## Source of truth order
1. GitHub branch + actual code + CI/runtime evidence
2. `wordpress/docs/MIGRATION_PLAN.md`
3. Project No Loss / Todoist checkpoint task `6hf5v5J535WvjJx5`
4. Historical chats/raw source only when provenance or a decision is disputed

## Current Git state
Working branch: `wordpress/migration-2026-10-01`.

Verified implementation checkpoint immediately before this documentation sync:
`df5f1f01c353e5dc75757e58ce321316bad5f7e9` (`fix: expose Woo checkout on staging for QA`).

Approved baseline remains immutable:
`approved/site-2026-10-01 = a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Do not modify it.

Default branch `main` remains infrastructure-only for the address-provider evaluation launcher. Last verified unchanged HEAD before this checkpoint:
`af6b829c6c58a072b7bd375af5b8515272c202e7`.

A new session MUST re-read the working branch HEAD and current `main` HEAD because this documentation commit itself and later commits may exist.

## Live staging — VERIFIED
`https://staging.rollsbar.ru`

Verified after deployment of `df5f1f01c353e5dc75757e58ce321316bad5f7e9`:
- isolated REG.RU staging site/database;
- trusted HTTPS;
- WordPress 7.1.3;
- WooCommerce 11.1.2;
- `rollsbar-theme` active;
- `rollsbar-core` active;
- full approved catalog preserved: 118 product cards from 131 source rows;
- RUB currency;
- native WooCommerce Blocks Local Pickup enabled;
- DaData API key configured server-side only;
- WooCommerce Coming Soon disabled on staging so anonymous QA can access Cart/Checkout;
- WordPress `blog_public=0`, so search-engine indexing remains disabled;
- production remains untouched.

Do NOT restore the historical 5-product smoke catalog.

## CI / runtime evidence — FINAL PASS FOR THIS CHECKPOINT
All four workflows triggered by implementation commit `df5f1f01c353e5dc75757e58ce321316bad5f7e9` completed successfully:
- `WordPress Staging Bootstrap Smoke` — run `37775581498` — success;
- `Build WordPress Staging Package` — run `37775581476` — success;
- `WordPress Migration Static Gate` — run `37775581514` — success;
- `Deploy REG.RU RollsBar Staging WordPress` — run `37775581480` — success.

The deploy runtime smoke reported:
- `ADDRESS SUGGESTIONS RUNTIME PASS`;
- exact probe: `qc_geo=0`, `allow_auto_zone=yes`;
- lower-precision probe: `qc_geo=2`, `allow_auto_zone=no`;
- `country_labels_exposed=no`;
- catalog still 118 cards;
- `blog_public=0`;
- `STAGING WORDPRESS DEPLOY PASS`.

Interactive checkout was then re-tested in a real anonymous browser session with a real Woo cart. Browser smoke rerun job `113306962222` in workflow run `37775215326` completed successfully and verified:
- product added to a real Woo Store API cart before checkout;
- checkout opened normally;
- staging DaData suggest/resolve endpoints were present;
- visible checkout address-line input existed;
- `Симферополь Гагарина 17` produced a suggestion, hid country labels, resolved at `qc_geo=0`, returned coordinates, and set `allow_auto_zone=1`;
- `Дубки Раздерина 12` produced a suggestion, hid country labels, resolved at `qc_geo=2`, set `allow_auto_zone=0`, and showed the clarification warning;
- no uncaught checkout JavaScript errors;
- production untouched.

## Important recovered discrepancy
During recovery after a connection interruption, the first browser checkout tests showed no checkout form. The actual cause was NOT DaData and NOT the fail-closed policy: WooCommerce Coming Soon was still enabled on the fresh staging store and anonymous visitors were seeing the store-under-development screen instead of Checkout Block.

The staging bootstrap now explicitly sets:
- `woocommerce_coming_soon = no`;
- `woocommerce_store_pages_only = no`;
while preserving `blog_public=0`.

This change is staging-only. It does not alter production.

## Catalog / prior Gate B
- full approved catalog: 118 product cards from 131 approved source rows;
- repeat import remains 118 products;
- prior desktop + mobile Gate B passed;
- historical mobile cart-overlay regression was absent in Gate B;
- do NOT restore the historical 5-product smoke state.

## Delivery rules
Seven confirmed minimum/free-delivery thresholds remain canonical:
1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB.

Validated polygon storage and point-in-polygon resolver exist. Exact production polygon boundaries have NOT been invented. Courier enforcement remains OFF.

## Address provider direction — DADATA FIRST
Owner constraint: do not pay for Yandex/2GIS unless the low-cost path materially fails.

Preferred architecture:
`DaData Suggestions -> qc_geo safety gate -> lat/lon -> RollsBar polygon resolver -> delivery tier/minimum`.

DaData Suggestions is now implemented on staging checkout as the address/coordinate source. The key remains server-side. Country metadata is diagnostic only; customer-facing suggestions/resolved addresses do not render provider country labels or raw unrestricted provider strings. Visible address is built from local address components such as locality/city, street and house.

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

Examples of weaker precision:
- Dubki — `qc_geo=2`;
- Molodyozhnoye (Crimean Spring St) — `qc_geo=3`;
- Agrarnoye (Parkovaya St) — `qc_geo=2`;
- Denisovka — `qc_geo=3`;
- Urozhaynoye — `qc_geo=2`;
- Fontany — `qc_geo=2`;
- Mazanka — `qc_geo=3`.

## Geocode precision policy — IMPLEMENTED / FAIL-CLOSED
RollsBar safety policy in `RollsBar_Geocode_Policy`:
- `qc_geo=0`: exact house; may automatically resolve a polygon/zone once approved polygons exist;
- `qc_geo=1`: must NOT silently auto-assign; require confirmation or an approved fallback/manual-point flow;
- `qc_geo=2/3/4`: must NOT auto-assign; require address clarification or an approved fallback/manual-point flow;
- `qc_geo=5`, missing or invalid: no zone lookup.

Default is fail-closed. Only exact-house precision can silently affect future delivery-zone/minimum logic. The browser smoke proves the staging UI follows this policy for `qc_geo=0` and `qc_geo=2`.

This policy does NOT enable courier delivery by itself.

## Country-label / customer-address rule — VERIFIED
- Customer-facing checkout does not render provider `country` or `country_iso_code` labels.
- It does not expose raw unrestricted provider strings as customer geography.
- Exact and low-precision browser probes both displayed no `Россия` / `Украина` country label in the suggestion/resolved address.
- Provider country metadata remains diagnostic/safety data on the backend only.

## Important unresolved inputs / decisions
- exact production polygon boundaries from the client — MUST NOT be invented;
- client-safe polygon editing / map-rendering layer if a visual editor is required;
- approved fallback/manual-pin UX if the client wants something stronger than address clarification for low-precision cases;
- real email/Telegram delivery test and production credentials;
- acquiring/payment phase later.

The earlier “wire DaData into checkout” item is DONE on staging and must not be repeated.

## NEXT ACTION
1. Obtain/confirm the client's exact delivery polygon boundaries; do not invent them.
2. If needed, provide a client-safe free/open visual map layer for drawing/correcting those polygons.
3. Load the approved polygons into staging and test `exact address -> coordinates -> polygon -> canonical threshold` across boundary cases.
4. Keep `qc_geo>=1` fail-closed; low-precision addresses must not silently choose a delivery zone.
5. Only after polygon QA explicitly enable courier zone/minimum enforcement on staging.
6. Production remains untouched until staging QA is complete and the owner explicitly approves transition.
7. Paid Yandex/2GIS remains fallback-only if DaData later proves materially inadequate.

## New-chat recovery protocol
In a new chat inside the same ChatGPT Project, the first instruction should be:

> RollsBar: восстанови состояние по Project No Loss. Не полагайся на память чата. Сначала прочитай `wordpress/docs/CURRENT_STATE.md` и `wordpress/docs/MIGRATION_PLAN.md`, затем сверяй текущий HEAD ветки `wordpress/migration-2026-10-01`, текущий `main`, последние CI/runtime результаты и Todoist task `6hf5v5J535WvjJx5`. Если есть расхождение, фактический GitHub/CI и канонические Project No Loss артефакты выше старых summary. Сначала покажи восстановленный checkpoint и NEXT ACTION, ничего успешного не повторяй, затем продолжай.

Project memory may help locate context, but it is not considered audit proof of No Loss.

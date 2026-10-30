# Rolls Bar — Checkout / Delivery Architecture

Updated: 2026-10-08
Status: STAGING IMPLEMENTATION — DADATA-FIRST, COURIER ENFORCEMENT STILL OFF

## Owner override — 2026-10-30 checkout policy

Known verified delivery minimums are now mandatory before native order submission (including current owner-authorized geographic rules). Unknown, missing, unsupported, ambiguous or low-precision/unresolved addresses remain phone+consent callback requests, with explicit manager clarification and no free-delivery promise. Pickup bypasses delivery minimums. Suggestions are restricted to Simferopol and its district; selecting a provider address persists signed metadata in the existing Woo session so reloading cannot discard a known minimum. Customer address remains native Woo storage. A completed successful Store API checkout clears only `store_api_customer_note`; failed/unfinished drafts retain it. Storefront HTML is no-store; native commerce HTML retains private/no-cache/must-revalidate/max-age=0, and content-versioned assets keep normal caching. Initial8/7 phone input immediately becomes+7. Native deferred email setting from RB-022 remains enabled. These later owner instructions supersede the earlier advisory-only commercial gate. Acceptance tracked in `CHECKOUT_POLICY_2026-10-30.md`.

## Current owner override — 2026-10-29 callback requests

Later owner override on the same date: restore the checkout map and use the prepared geographic draft on **staging now**, without waiting for client review. Exact table identities remain primary; exact-house qc_geo=0 may use a provisional geographic fallback, with locality footprints before city background. Existing ambiguous street splits and conflicts remain unresolved. These are informational free-delivery minimums, never tariffs or callback blockers. Map lives directly below the native address form and is hidden for pickup; phone + explicit consent remains the submission contract. Production remains forbidden. Acceptance evidence is maintained in `CHECKOUT_DELIVERY_MAP_2026-10-29.md`; earlier “no map/polygons” statements are historical where this later instruction conflicts.

Current staging application `a4d5e5a68c59bb7904c36749b2dfadf828c67a22` is browser_verified (apply 40856936705, finalization 40858251322). A complete phone and explicit consent are required; name/address and minimum are not submission prerequisites. Unchecked consent is highlighted, focused and scrolled into view. DaData/FIAS minimums remain strict as information, but no longer refuse a callback request; manager confirms fulfillment. One native Woo Checkout Block/Store API/session/order/COD path remains. No polygons/map/tariffs. See `CHECKOUT_PHONE_ONLY_REQUEST_2026-10-29.md` and RB-016. Older enforcement assumptions below are historical where they conflict.

## Accepted override — 2026-10-28

The owner-authorized Delivery Rules / Auto Minimum batch supersedes the older polygon prerequisite **for whole-street/locality minimum rules only**. Staging application `8568c10a14c2d74771f9f8fcc0e5b8a9c31acc3e` is browser_verified (apply 40718770624, finalization 40720499963).

Current flow: `DaData → verified FIAS house + exact locality/street identity → deterministic free-delivery minimum → native Store API pre-order validation`. Native Delivery/Pickup control is active; pickup requires name/phone only, delivery uses one address and optional details. Map hidden. Whole-identity rules do not use approximate coordinates to infer boundaries. Existing qc_geo safety for geographic/polygon decisions is unchanged. Polygons, geographic zone enforcement, delivery tariffs and outside-zone rules remain deferred. No price for delivery is invented; 1200–4000 ₽ are minimum goods amounts for free delivery. Unknown/ambiguous/unverified-house cases fail closed.

See `DELIVERY_RULES_AUTO_MINIMUM_2026-10-28.md` and RB-014 for exact fields, signed proof/native session architecture and final evidence. The architecture below is historical context where it conflicts with this override.

## Current architecture

Use:
- WooCommerce Checkout Block;
- official Additional Checkout Fields API for Rolls Bar order details;
- native Blocks Local Pickup for self-pickup;
- DaData Suggestions as the preferred address -> coordinate provider;
- RollsBar point-in-polygon resolver for delivery-zone lookup;
- a Rolls Bar courier-delivery method only after real client-approved polygons exist.

Target flow:

`address -> DaData Suggestions -> qc_geo safety gate -> coordinates -> polygon -> zone -> minimum/shortfall -> courier rate`

Country/provider geography metadata is diagnostic only. Customer-facing checkout must render only approved local address components such as locality/city, street and house, not provider country labels or raw unrestricted provider strings.

Yandex/2GIS are fallback providers only if DaData coverage/precision cannot be handled acceptably.

## Live DaData evidence

GitHub Actions run `37766333406` evaluated 25 verified Simferopol / outer-area addresses:
- 25/25 returned coordinates;
- 25/25 returned `RU` country metadata;
- `qc_geo=0`: 17/25;
- `qc_geo=2`: 5/25;
- `qc_geo=3`: 3/25.

Therefore DaData coverage is sufficient to continue, but lower-precision coordinates must never silently assign a delivery polygon.

## Geocode precision safety policy

DaData documents `qc_geo` as:
- `0` — exact house coordinates;
- `1` — nearest house;
- `2` — street;
- `3` — settlement;
- `4` — city;
- `5` — coordinates not determined.

RollsBar policy:
- `qc_geo=0`: automatic polygon/zone lookup is allowed once real polygons are approved;
- `qc_geo=1`: do not silently auto-assign; require explicit customer confirmation / approved map-pin flow before using the coordinate;
- `qc_geo=2/3/4`: do not auto-assign; ask the customer to clarify the address or use an approved fallback/manual-point flow;
- `qc_geo=5`, missing or invalid: no delivery-zone lookup is allowed.

The code guard lives in `RollsBar_Geocode_Policy`. Its default is fail-closed: only `qc_geo=0` can return `allow_auto_zone=true`.

This policy is intentionally implemented before checkout wiring so a later integration cannot accidentally trust street/settlement coordinates as house coordinates.

## Additional order fields

Registered in `rollsbar-core` via the WooCommerce Additional Checkout Fields API:
- Подъезд
- Код двери / домофона
- Этаж
- Квартира / офис

All four remain visible but optional by default. Client-requiredness remains editable under:

`Rolls Bar -> Основное -> Оформление заказа`

## Phone

Checkout prepares `+7 ` when the phone field is initially empty and normalizes a leading `8` to `+7` on blur. This has already passed live Gate B on staging.

## Pickup

Native WooCommerce Blocks Local Pickup is active on staging and passed desktop/mobile Gate B. Do not create a duplicate pickup implementation unless a concrete requirement exceeds WooCommerce core capability.

## Courier delivery safety

Courier enforcement remains OFF until all of the following are true:
- exact polygons are drawn/corrected and accepted by the client;
- address selection UX is live-tested on staging;
- low-precision DaData behavior follows the safety policy above;
- outside-zone behavior is explicitly accepted;
- cart minimum enforcement is tested against the real polygons.

Outside approved polygons the current intended behavior is pickup-only unless a later direct client decision changes it.

## Next staging work

1. Wire DaData Suggestions into a staging-only address-selection flow without enabling courier enforcement.
2. Verify real customer typing/selection behavior and `qc_geo` handling.
3. Replace or decouple the dormant Yandex-only polygon-editor renderer with a client-safe free/open map layer if practical.
4. Client draws/corrects exact polygons.
5. Only then enable `address -> coordinates -> polygon -> threshold` in checkout.

# Rolls Bar — Checkout / Delivery Architecture

Updated: 2026-10-08
Status: STAGING IMPLEMENTATION — DADATA-FIRST, COURIER ENFORCEMENT STILL OFF

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

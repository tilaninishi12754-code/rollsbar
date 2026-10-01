# Rolls Bar — Checkout / Delivery Architecture

Date: 2026-10-01
Status: PRE-STAGING IMPLEMENTATION DECISION

## Current-best evidence synthesis

### Official WooCommerce
- Checkout Blocks are the modern checkout surface.
- Additional fields belong on the Additional Checkout Fields API, registered with `woocommerce_register_additional_checkout_field()`.
- Modern Local Pickup is built into Checkout Blocks and provides the Delivery toggle + pickup locations without requiring a shipping address.
- Custom courier rates belong in a WooCommerce shipping method/plugin, not theme code.

### Current practitioner reality
A recurring 2025–2026 failure mode is carrying classic `woocommerce_checkout_fields` customizations into Block Checkout. Those hooks do not represent the modern field architecture and can silently disappear after switching checkout implementations.

### Rolls Bar best-fit
Use:
- WooCommerce Checkout Block;
- official Additional Checkout Fields API for Rolls Bar address details;
- native Blocks Local Pickup for self-pickup;
- a Rolls Bar courier-delivery method only after real polygons/rules exist;
- Yandex Maps/Geocoding as the address→coordinate layer once API credentials are available.

Do **not**:
- revert to classic checkout just to preserve legacy snippets;
- emulate real delivery rules using fake flat rates;
- create a duplicate custom pickup implementation when WooCommerce core already provides the correct block-native one.

## Implemented now

### Additional order fields
Registered in `rollsbar-core`:
- Подъезд
- Код двери / домофона
- Этаж
- Квартира / офис

All four remain visible but optional by default.

Client can change requiredness under:

`Rolls Bar → Основное → Оформление заказа`

This preserves the fields while avoiding the current UX error where a private house / office without a door code could be blocked from ordering.

### Phone
A checkout script prepares the phone input with `+7 ` when initially empty and normalizes a leading `8` to `+7` on blur.

This behavior must still be verified against the real Checkout Block on staging because the block UI is React/Store-API driven.

## Pickup

On staging:
1. Enable WooCommerce Blocks Local Pickup.
2. Create Rolls Bar pickup location using the verified store address.
3. Rename the customer-facing labels if needed.
4. Verify pickup checkout does not require delivery address.
5. Verify order admin clearly records pickup.

Do not install a second pickup plugin unless a concrete requirement exceeds WooCommerce core capability.

## Courier delivery

Courier delivery remains **intentionally disabled as a production-final rule** until these inputs exist:
- real polygons;
- minimum order for each zone;
- delivery fee/free-delivery thresholds;
- approved outside-zone behavior.

Target flow:

`address → Yandex geocode → coordinates → polygon → zone → cart minimum/shortfall → courier rate`

Outside approved polygons:
`pickup only`, unless a later direct client decision supersedes it.

## Pending staging tests

- Checkout Block renders all four fields.
- Admin requiredness toggles affect checkout.
- +7 helper does not fight WooCommerce/React state.
- additional values save to the order and appear in order admin/email.
- native Local Pickup works on mobile and desktop.
- no custom checkout field duplicates billing/shipping data.
- no legacy checkout hook dependency.

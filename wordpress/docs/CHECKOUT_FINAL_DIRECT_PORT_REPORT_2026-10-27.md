# Checkout Final Direct Port — accepted staging release

Status: **STAGING PASS / RB-006 DONE**. Closed 2026-10-28, Europe/Moscow. Batch specification: 2026-10-27.

## Release evidence

- Application and finalized staging marker: `529cbf3dc536b13dce40d74bbfbb8d054a9f2cfd`.
- Branch: `wordpress/checkout-visual-parity-2026-10-25`.
- [Apply and all live gates — 40583002012](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40583002012): success.
- [Manifest-bound finalization — 40585851050](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40585851050): success; installed native integration repeated, receipt `phase=browser_verified`, `DIRECT_PORT_STAGING_PASS`.
- Fresh backup before narrow deployment: `20261027T210114Z`; database, uploads, manifest/checksums and archives outside webroot verified. Historical protected snapshot preserved.
- Artifact `12771016021`, SHA256 `9005bbe162738a59f2634f28836042bdcf605f82b17030e290552532a71567a7`, downloaded and independently verified.
- Reviewed 32-image manifest: `589fada0f55ad80975b303e65cbbfe84546be17baa573f29c37c543ad0753615`.
- Native live browser proof: `3f3daaee-4873-4d82-a864-57ffa4a64c04`; independent post-green adversarial proof: `29185c9e-beec-473c-8487-d4a036d4f7ff`, same application SHA.

## Architecture and fields

`/checkout/` is the technical host for exactly one native Woo Checkout Block / Store API lifecycle. Its static ancestor supplies the approved fixed modal, backdrop and internal scroll. Native React inputs, cart, payment and submit controls are retained. The real submit button is positioned through measured presentation variables without cloning/remounting it. Close/Escape/backdrop return to the storefront; a one-use UI scroll key restores menu position without duplicating commerce state.

Immutable reference: `5e7836e22110ec076603bb1fa2b12f8bb90ee756:index.html`. Restored values include 1040px maximum width, viewport minus 24px, 92vh maximum height, 22px padding, 28px desktop radius, exact shadow and backdrop/blur. Source composition becomes one column at 1050px and bottom-aligned with 25px upper corners at 700px. Desktop retains the 360px summary lane.

- Required: **Имя, Телефон, Адрес**. Existing +7 preparation / leading 8 normalization preserved.
- Optional: **Населённый пункт, Подъезд, Домофон, Этаж, Квартира / офис, Комментарий к заказу**.
- No customer-facing surname, email/contact/guest copy, company/address2, country/state/postcode. Native country remains valid RU internally.
- Four optional extras use existing Additional Checkout Fields IDs/storage; comment uses one native customer note. Explicit required privacy consent and native legal/terms behavior remain.
- Native Local Pickup title: **Симферополь, Кечкеметская улица, 1**. Native COD remains selected/available; native totals remain authoritative.

## Email compatibility and proof

The exact official WooCommerce 11.1.2 source and installed native validators require a valid billing email independently of locale. A per-native-session HMAC identity `guest-<32hex>@checkout.rollsbar.invalid` supplies that internal contract. The reserved non-deliverable value is not a real customer contact. Native field configuration removes email from the UI; native customer/REST preparation and public cart-store actions preserve compatible email/RU values without bypassing schema validation.

Guest account creation, including delayed account prompts, is disabled. `pre_wp_mail` blocks technical destinations before transport. Operator mail remains available with technical Reply-To/contact removed. Presentation filters remove technical contact rows from native confirmation summary/customer details after native access checks; native order getters and validation remain unchanged.

Installed server fixtures invoke real email/address validators, actual REST schema/sanitization and route consent validation. Empty/malformed email and missing required fields are rejected; approved payload with optional locality absent is accepted. Actual Woo confirmation/template rendering and delayed-account feature state are tested on an **unsaved WC_Order with ID 0**. Browser proof exercises native guest COD submission assembly and stops before HTTP. **No placed order, account creation or customer mail was performed; no full placed-order/payment-side-effect test is claimed.** Country presentation hides a valid preset RU control, never an empty required email.

## Verification

| Gate | Result |
|---|---|
| Native Playwright, 1440 / 701 / 700 / 390 / 320 | 5/5 PASS |
| Original live storefront UX, desktop/mobile | 5/5 PASS |
| Original Interaction Stability, 320 / 390 / 430 / 701 / 900 / 1440 | 6/6 PASS |
| Independent post-green adversarial native/return check | PASS |
| Local checkout/release/method-override contracts | 18 PASS |
| Local PHP compatibility fixture; installed native integration | PASS |

Coverage includes geometry, overflow, body/modal scrolling, first activation, close/reopen, direct entry, focus/Escape, requiredness/visibility, hit targets, native summary/prices/totals, COD, optional fields/note, exact and lower-precision DaData/map state. Zero order submissions and JavaScript errors. Adversarial return verifies cart, search, fixed header and first back-to-top at 320px; cleanup verifies only the isolated test cart is empty.

All 30 immutable reference/candidate/raw diff screenshots and both DaData screenshots were actually inspected after automation, plus populated storefront stress screenshots at all six widths and returned storefront. Unmasked whole-image differences: 1440: 21.1%, 701: 20.74%, 700: 16.08%, 390: 19.12%, 320: 19.86%. These retain real native order contents/legal/payment controls and genuine map feedback instead of demo polygons; exact shell/composition geometry is independently asserted. No baseline, mask or tolerance was weakened. Map capture waits for the provider's actual final renderer/resources; no provider content is substituted.

The earlier all-green run 40577025861 was rejected by vision for an intermediate map capture and never promoted. Lifecycle evidence also corrected a forced-navigation test setup that left an initial home cart read unfinished; the original cleanup deadline and original storefront regression files remain unchanged. [Detailed investigation history at the pre-close commit](https://github.com/tilaninishi12754-code/rollsbar/blob/529cbf3dc536b13dce40d74bbfbb8d054a9f2cfd/wordpress/docs/CHECKOUT_FINAL_DIRECT_PORT_REPORT_2026-10-27.md).

## Scope and preservation

Application files changed:

- `wordpress/wp-content/plugins/rollsbar-core/assets/css/checkout.css`
- `wordpress/wp-content/plugins/rollsbar-core/assets/js/checkout.js`
- `wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php`

Supporting changes are checkout QA/native fixtures/request guard, staging browser diagnostics, dedicated deploy/native verification scripts, staging workflow and acceptance documentation. Every other plugin/theme file is hash-guarded against accepted application b481a6f. Original storefront UX and stress harnesses remain byte-for-byte unchanged.

A supported WordPress speculation-path filter excludes native cart/checkout/product documents, and speculative checkout requests do not seed customer state. This narrow correctness safeguard followed reproduced variation loss; other speculation rules, cache settings and storefront implementation remain unchanged.

Catalog **118 / 13 / 26 + 3 = 121**, Client Media Canon **36 assets / 45 identities**, business digest and unrelated app hashes remain verified. RB-001..RB-004 remain DONE. RB-005/RB-007/RB-008 performance/cache work remains deferred. Delivery is address → DaData → precision safety → coordinates → map; courier enforcement OFF. No polygons, tariffs, minimums or outside-zone rules were added.

Repository handoff uses a documentation-only descendant of application `529cbf3dc536b13dce40d74bbfbb8d054a9f2cfd`; the closing Worker message records its exact final Git HEAD after normal push and clean-tree verification. No reset, force or rebase. **Production access/mutation: no.**

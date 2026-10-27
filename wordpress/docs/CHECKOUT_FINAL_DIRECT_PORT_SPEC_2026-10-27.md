# RollsBar — Checkout Final Direct Port Spec

Status: APPROVED BY USER — 2026-10-27
Owner: RollsBar Coordinator

This is the durable implementation contract for the next checkout batch. It supersedes the prior assumption in Checkout Visual Parity V2 that email/surname/country/city-region-postcode were unavoidable customer-facing Woo differences. Do not silently revert to that older assumption.

## Accepted checkpoint before this batch

- Branch: `wordpress/checkout-visual-parity-2026-10-25`.
- Accepted Git HEAD before this spec commit: `14304ac661e05185b14543db8e94ab20acfc0ca2`.
- Accepted deployed application marker: `b481a6fa3d2db7a5524667c51d263ceb117a05d7`.
- Storefront Interaction Stability is verified PASS on staging; RB-001..RB-004 are DONE.
- Client Media Canon and catalog invariants must remain unchanged.
- Production mutation is forbidden without a later explicit production gate.

## Visual source of truth

Immutable approved checkout visual source:

`5e7836e22110ec076603bb1fa2b12f8bb90ee756:index.html`

The target is a direct port of the approved checkout shell/UX onto native WooCommerce behavior, not a redesign and not a route/page reinterpretation.

Required shell characteristics include the approved fixed modal/backdrop behavior, centered panel, approved radius/shadow/padding, desktop two-column form/summary composition, internal modal scrolling, close/dismiss behavior and responsive mobile composition. Recover exact values from the immutable source rather than copying approximate values from this spec.

## Native Woo authority

Preserve WooCommerce Checkout Block / Store API as the transaction authority. Preserve native cart/order totals, payment integration, validation, privacy/legal behavior, Additional Checkout Fields storage and existing DaData address-resolution safety.

Do not clone the demo's fake business logic. Port the visual/interaction shell and map the real Woo controls/data into it.

Do not create a second cart, second checkout state, custom order submission path or duplicate payment/pickup implementation.

## Customer-facing checkout fields — approved final UX

The customer-facing checkout must be simplified to the following business fields.

### Customer identity/contact

- `Имя` — visible and required.
- `Фамилия` — hidden/removed from customer UI and not customer-required.
- `Телефон` — visible and required. Preserve current `+7 ` preparation and leading `8` -> `+7` normalization unless a regression proves a supported improvement is required.
- `Email` — customer must NOT see or enter an email field. Remove the visible `Контактная информация / Email / Вы оформляете заказ как гость` experience.

### Woo email compatibility constraint

Woo Checkout Block / Store API currently validates a valid billing email. Therefore:

- DO NOT merely CSS-hide an empty required email field;
- first prefer any safe, supported current Woo mechanism that makes customer email unnecessary while preserving Store API checkout;
- if current Woo still requires an internal email for guest checkout, use the narrowest deterministic internal compatibility value/mechanism necessary so the customer never sees or enters email;
- any technical placeholder must be clearly marked internal, non-customer data, non-deliverable, must not create an account, must not be used as a real contact destination, and must not trigger customer-facing email notifications;
- prove checkout validation/contracts still work without customer email input;
- do not switch away from Checkout Block merely to avoid this constraint unless evidence proves no safer supported path exists.

### Address

- `Адрес` — visible and required. This is the exact customer address used for address resolution/map feedback.
- `Населённый пункт` — visible but optional, so a customer can explicitly identify a settlement outside Simferopol when relevant.
- Country — not customer-facing. Keep the required internal Woo country context fixed to Russia where needed for locale/Store API semantics.
- Region/state/district — not customer-facing and not customer-required.
- Postcode — not customer-facing and not customer-required.
- Company/address line 2 or other irrelevant native fields — not customer-facing unless a proven checkout dependency requires a hidden internal value.

Do not use CSS-only hiding when server validation still requires a customer value. Use Woo-supported locale/Block configuration or a documented compatibility mechanism and cover it with tests.

## Pickup location

Canonical restaurant / pickup address approved by the user:

**Симферополь, Кечкеметская улица, 1**

Where the checkout shows `Место выдачи`, display this exact address instead of an abstract `Rolls Bar` location title alone. Preserve native Local Pickup semantics; do not create a duplicate pickup method.

## Additional order information

Keep these optional order fields:

- `Подъезд`
- `Домофон` (existing internal label may currently be `Код двери / домофона`; customer-facing wording should be concise)
- `Этаж`
- `Квартира / офис`
- `Комментарий к заказу` — one ordinary optional free-text order note/comment field

Use native Additional Checkout Fields / native customer note where appropriate. Do not duplicate storage for the same information.

## Payment

Customer-facing payment method for this scope: **Оплата при получении / COD**.

Preserve the native Woo payment gateway. Do not implement acquiring or fake payment controls.

## Map / address feedback

Keep the existing address -> DaData -> coordinates -> map feedback flow and current geocode precision safety policy.

For now the map remains address verification/feedback. Current courier zone enforcement stays OFF.

Do not invent delivery polygons, prices, minimum order thresholds or outside-zone rules in this batch.

Current acceptable pre-zone message may continue to communicate that an exact address was determined and conditions are confirmed by the operator.

Automatic zone/tariff output belongs to a later dedicated Delivery Rules batch after client-approved polygons/rates/minimums exist.

## Explicitly deferred from this batch

- delivery-zone polygons and automatic delivery tariff selection;
- minimum-order enforcement by zone;
- outside-zone business rules;
- performance optimization of Add latency;
- image/CDN/cache optimization;
- production deployment.

## Preservation requirements

Do not regress:

- storefront cart first-tap behavior;
- back-to-top first-tap behavior;
- exact pizza variation `+` behavior and safe multi-size ambiguity;
- pending/race protection and native Woo session consistency;
- search;
- sticky header;
- phone/fixed controls;
- Client Media Canon: 36 canonical assets / 45 mapped identities;
- catalog invariant: 118 canonical / 13 variable parents / 26 variations + 3 hidden staging upsells = 121 published product posts;
- business-data digest unless this approved checkout configuration necessarily changes an explicitly documented checkout setting.

## Verification standard

Functional and visual verification are both mandatory.

### Functional

Use deterministic browser tests against real native Woo behavior. Cover at minimum:

- open checkout from cart;
- true modal opens on first activation;
- modal close/back behavior;
- body/background interaction and scrolling while modal is open;
- required `Имя`, `Телефон`, `Адрес`;
- optional locality;
- no visible customer email/surname/country/state/postcode fields;
- no guest-account/email copy;
- pickup address exactly `Симферополь, Кечкеметская улица, 1`;
- COD selected/available;
- optional entrance/intercom/floor/apartment/comment fields;
- DaData exact and lower-precision behavior remains safe;
- map corresponds to resolved address;
- native summary/totals/cart state remain correct;
- no duplicate checkout controls or submission path.

Do not create real orders during automated acceptance unless the Coordinator explicitly authorizes a dedicated disposable-order test.

### Visual

Use Playwright for deterministic viewport setup, DOM geometry, interaction, screenshots and screenshot comparison.

At minimum verify approved reference versus candidate at:

- 1440 desktop;
- 700/701 boundary where relevant;
- 390 mobile;
- 320 mobile.

Recover reference screenshots from immutable Git source, not from the candidate.

Large geometry/composition differences are failures. Do not classify a route page, missing backdrop, wrong modal geometry or major layout difference as an `acceptable responsive adaptation`.

After deterministic screenshot/diff checks, visually inspect the resulting screenshots with model vision. Automated geometry and machine-vision review are complementary; neither replaces the other.

## Release discipline

Local candidate -> functional tests -> Playwright visual gate -> screenshot review -> commit/push -> fresh verified staging backup -> narrow staging deploy -> live native Woo browser gate -> live screenshot/diff review -> update Issue Register/report.

Production remains untouched.

RB-006 may become DONE only after exact staging evidence proves both native functionality and the approved modal visual architecture.
# Delivery/pickup UX and automatic minimum — 2026-10-28

Status: **STAGING PASS**. RB-014 DONE; RB-006 preserved with the owner's updated field composition. Production access/mutation: **no**.

Application/verified deployed marker: `8568c10a14c2d74771f9f8fcc0e5b8a9c31acc3e`.
[Apply and automated evidence 40718770624](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40718770624); [inspected finalization 40720499963](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40720499963), receipt `browser_verified`, `DELIVERY_STAGING_PASS`. Fresh verified staging backup: `20261028T154410Z`, outside webroot under `/var/www/u3646545/data/rollsbar-backups/staging/20261028T154410Z`. DB/uploads/manifests/checksums/archive verification PASS before narrow deployment.

## Customer scenario and native authority

One existing Woo Checkout Block on `/checkout`, rendered in the approved fixed modal; one Store API/Woo session/cart and original native submission. First control: **Доставка / Самовывоз**. Native `rollsbar_delivery` method and existing Blocks `pickup_location` own fulfillment. No secondary checkout lifecycle, cart or order endpoint.

- Both modes require **Имя** and a complete **Телефон**; empty values and prefix-only `+7` are rejected. The prefix is a formatting hint, never seeded contact data. Supported `woocommerce_validate_phone` filter preserves native format validation and checks 10–15 digits.
- Pickup immediately displays **Симферополь, Кечкеметская улица, 1** after identity. Customer address/details are hidden and not required. An empty-cart receiving choice starts the native Woo guest session, so pickup survives a fresh request and first item addition.
- Delivery requires one **Город, улица и дом** field confirmed from DaData. Separate locality removed. **Подъезд / Домофон / Этаж / Квартира / офис** remain optional native Additional Checkout Fields, with no optional suffixes.
- **Комментарий к заказу** is always open, using native customer note storage; its disclosure checkbox is hidden. Privacy consent and native COD retained.
- Customer email/contact/guest-account copy, surname, country/state/postcode/company are absent from customer UX. Map deferred: no map iframe/resources, polygons, geographic zone enforcement or invented delivery charges.

## Rules and address integrity

Read-only client workbook `маршрут доставка.xlsx`, sheet `Лист1`, B:H rows 3:25, SHA256 `4093f02c4446de749102a6b1e82b7e65d1bd0855b99644e3e411f92a5097095f`. JSON retains all **92 source cells** and provenance. Seven minimum goods amounts for free delivery: **1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 ₽**. These are minimums, never fees. Amount uses native goods after discounts, excluding shipping/fees/taxes. Both duplicate Mazanka source rows use the confirmed **4000 ₽** override.

`DaData → verified house FIAS + exact administrative/street/locality identity → deterministic rule`. No fuzzy substring or coordinate-based boundary inference. Provider-confirmed source alias D14 ГРЭС = Грэсовский, settlement FIAS `d3f14746-73e5-4ad2-85b3-f76e1b3cbc5c`, 2000 ₽. Named neighbourhoods only match explicit provider planning-structure identity; surrounding streets are not inferred.

Unknown/unverified-house addresses and ambiguous boundary rules fail closed with a customer clarification. Do not guess ДКП→Автовокзал, Кечкеметская→Арабатская, Беспалова до/от Марьино. Central Market origin is the restaurant at Кечкеметская улица, 1; no approach boundary was invented. Five boundary source cells remain unresolved and do not block other matched addresses.

Precise FIAS house identity can support whole-street/locality text rules even with approximate provider coordinates (live examples Denisovka, Fontany, Urozhaynoye, Mazanka). Existing geocode policy is unchanged: non-exact coordinates still cannot assign a geographic zone. Street-only selection cannot authorize delivery.

DaData resolve signs identity/display/12-hour expiry with WP auth-salt HMAC. Canonical address is saved through public native Woo address setters and `updateCustomerData` before publishing proof. Store API checkout extension `rollsbar-delivery.address_proof` carries it; pre-order server validation verifies signature/expiry/exact submitted address and recomputes minimum/current native amount. Missing, edited, stale or forged proof fails closed. No client minimum is trusted and address/note storage is not duplicated.

## Email compatibility proof

Preserved native guest solution for installed WooCommerce **11.1.2**: per-session HMAC email `guest-{32hex}@checkout.rollsbar.invalid` is seeded before native schema validation, and the supported native field registry removes email from presentation. No CSS-hidden empty required email, account creation or customer input. Technical value is never a real contact: reserved recipients/CC are blocked through `pre_wp_mail`, Reply-To and operator body are scrubbed, confirmation contact rows omitted.

Installed-Woo fixtures validate actual native REST schema, sanitization/field callbacks, guest payload, email privacy/mail filters and full-phone validation without dispatching checkout. Browser captures native delivery and pickup POST assembly before HTTP; COD, `create_account=false`, technical email, note, consent, native fields and signed address are verified. No actual order/account/customer mail was created. Completed-order persistence and outbound mail delivery were intentionally not exercised; no live end-to-end order claim is made.

## Final evidence

All below refer to exact application `8568c10a14c2d74771f9f8fcc0e5b8a9c31acc3e` in apply run 40718770624, followed by installed-backend revalidation in finalization 40720499963.

| Gate | Result |
| --- | --- |
| Deterministic rule fixture | PASS: 92 source cells, seven tiers, exact/below-one-kopeck, aliases, Mazanka, unsupported/ambiguous, FIAS precision, proof tampering/edit |
| Installed native Woo integration | PASS: native method/schema/fields, required phone, email protection, minimum enforcement, pickup bypass, unknown mode rejection |
| Live native modal + functional | **5/5 PASS**, 1440 / 701 / 700 / 390 / 320 × 900; fields, requiredness, internal/body scroll, overflow, hit targets, COD, map absence, address edits, native presubmit |
| Cart totals | PASS: displayed product/totals compared independently to Store API; quantity and delivery/pickup transitions retain confirmed canonical address |
| Real provider addresses | **20/20 PASS**, at least two distinct exact addresses per tier, extra Грэсовский and Mazanka, unknown address, street-only and unresolved boundary cases |
| Final adversarial | **3/3 PASS**, 320 / 700 / 701: empty-cart pickup across fresh request/first add, cart first activation, empty identity/prefix rejection, native pickup pre-submit, focus/keyboard/Escape, cart-preserving close/reopen and low-precision refusal |
| Immutable visual source | **5/5 modal chrome PASS**, source `5e7836e22110ec076603bb1fa2b12f8bb90ee756:index.html` plus assets from same commit; panel/backdrop/shadow/padding/radius/max-height/alignment/summary lane checked |
| Original storefront regression | **5/5 PASS**, 1440×900 / 320×568 / 390×844 / 390×900 / 430×932 |
| Accepted no-shelf controls | **5/5 PASS**, 320 / 390 / 701 / 900 / 1440, empty/populated cart, nine-point hits, first cart/back-top activation, no overflow |
| Catalog/business/media | PASS: business digest unchanged, 118 / 13 / 26 + 3 = 121; Client Media Canon retained |
| Release/request guard unit checks | **9/9 PASS** |

Visual comparison retains **full unmasked** reference/candidate/diff images; masks `[]`, no tolerance/baseline relaxation. Full-content pixel equality is not claimed because the owner explicitly changed field composition and removed the map. Approved modal architecture, geometry and backdrop are preserved. All **35 PNGs** (10 mode screenshots, 7 address states, 3 adversarial states, 15 immutable reference/candidate/diffs) were actually inspected with vision after deterministic gates, plus desktop/320/390 storefront images. No modal/page-sheet, backdrop, clipping or composition defect found. Immediate native mode-transition captures can contain temporary native loading placeholders; settled totals are independently tested.

Reviewed screenshot manifest: `8fd3f8b66ddcb4be91ce8ceabf8157195ac0cc18d3232566536c7e67bad748fd`.
Artifact `12828339797`, ZIP SHA256 `57e41f0f7e0f6ba5e928d0e92a40734597fd880d83bc95bf11b772c73e5349bf`, verified before extraction. Local evidence: `qa/visual-results/final-delivery-40718770624/` including `vision-review.json` and labeled review sheets. CI artifacts retained 30 days.

Historical `qa/visual/interaction-stability.mjs` whole-bottom-band assertion is unchanged and intentionally incompatible with the owner's accepted shelf removal; **RB-010 remains DEFERRED**, no full historical stress-suite PASS claimed. Frozen `qa/visual`, original browser isolation helper and shadow baseline remain unchanged from 475a036. Earlier broad historical unit discovery also contains obsolete asset-version and fixture/runtime expectations; it is not reported as green. Current targeted release/request checks and the exact-release live gates above passed.

## Changed files and delivery state

Ten application files only, under `wordpress/wp-content/plugins/rollsbar-core/`:

- `data/delivery-minimum.json`
- `includes/class-rollsbar-delivery-minimum.php`
- `includes/class-rollsbar-delivery-checkout.php`
- `includes/class-rollsbar-native-delivery-method.php`
- `rollsbar-core.php`
- `includes/class-rollsbar-address-suggestions.php`
- `includes/class-rollsbar-checkout.php`
- `includes/class-rollsbar-cart-actions.php`
- `assets/js/checkout.js`
- `assets/css/checkout.css`

Supporting changes: new `qa/checkout/delivery_*` fixtures/browser gates, current `direct_port_fixture.php`, staging verification scripts/narrow apply workflow, this report/Issue Register and current architecture addendum. No theme storefront JS/CSS changes in this batch.

Final implementation corrections were evidence-driven: native canonical address persistence before proof, complete-phone validation, empty-cart native guest cookie plus pickup preference, and browser waits for actual native save/proof and scrolled controls. No unchanged failed run was blindly retried. No reset/force/rebase. Normal commits/push on `wordpress/checkout-visual-parity-2026-10-25`; final documentation commit descends from the verified application, with no application byte changes after acceptance. Production access/mutation: **no**.

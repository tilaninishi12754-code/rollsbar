# Callback request: phone and explicit consent — 2026-10-29

Status: **STAGING PASS**. RB-016 **DONE**. Production access/mutation: **no**.

Current application / verified deployed marker: `a4d5e5a68c59bb7904c36749b2dfadf828c67a22`. [Apply and exact-release checks 40856936705](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40856936705); [inspected finalization 40858251322](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40858251322), receipt `browser_verified`, `DELIVERY_STAGING_PASS`. Fresh verified backup **20261029T102229Z**.

## Current owner-approved contract

The owner's later instruction supersedes earlier required-name/address/minimum assumptions for request submission. In the existing non-empty-cart Woo checkout, a **complete phone number plus explicit checked privacy consent** are required. Name, address, entrance/intercom/floor/apartment, comment and reaching the free-delivery minimum are not submission prerequisites. Consent is never prechecked or fabricated.

Without consent: explanatory text next to the native CTA, native field error plus **red border/background** around the consent block, keyboard focus and internal-modal scroll to that block. The full marker is visible at all five widths, including 320px. Explicit checking clears the marker and error; request assembly then proceeds with empty name/address. Empty phone and prefix-only `+7` remain rejected.

DaData and seven minimum tiers remain advisory; unresolved/unverified-house/edited/missing-proof addresses and below-minimum carts can leave a callback request. Classifier/proof integrity and precision safety are unchanged: no guessed minimum or boundary is introduced. Manager confirms fulfillment details using the phone stored in the native Woo order contract. This changes submission policy, not the rule table or delivery price.

One existing Checkout Block / Store API / Woo cart-session / native COD path. Supported native field configuration makes name optional and keeps consent required. The commercial delivery pre-order refusal and frontend delivery validation error are removed; native selected-rate validation remains. Native internal guest email/country compatibility, no-account behavior, mail protection and native Additional Fields/customer note storage are retained. No alternate lead endpoint, second cart, map, polygon or tariff.

## Verification and evidence

Installed **WooCommerce 11.1.2 / WordPress 7.1.4** integration PASS. Actual native REST schema/field validator rejects unchecked consent; accepts full phone, empty name/address and checked consent. Native delivery callback is accepted without commercial proof/minimum refusal. Empty phone remains required through the native field validator. Server fixtures use unsaved orders; no order processing/dispatch performed.

Live Playwright native gate **5/5 PASS** at 1440 / 701 / 700 / 390 / 320:

- Empty phone cannot reach native POST assembly; incomplete prefix rejected.
- With valid phone but unchecked consent, no native POST assembly; message at CTA, focused checkbox, red computed marker, entire block in viewport.
- Explicit check clears marker, native callback payload contains true consent, full phone and empty name/address.
- Below-minimum goods still reach native POST assembly; valid populated payload/COD/native fields/comment/email contracts retained.
- Delivery/pickup, canonical address updates, cart totals, internal/body scroll, no overflow and no map regressions.

Real provider coverage **20/20 PASS**: all seven tier identities and unknown/ambiguous cases remain deterministic, with advisory UI and no delivery validation blocker. Adversarial **3/3 PASS** at 320 / 700 / 701: empty-cart pickup, guest/native contact, modal keyboard/Escape/cart-preserving close/reopen, unresolved delivery with required phone/consent, native pre-submit interception. Per-document capture is reinstalled after navigation; explicit consent is supplied for the new request. No order HTTP submitted.

Immutable modal geometry **5/5 PASS**, original storefront **5/5 PASS**, accepted no-shelf controls **5/5 PASS**. Frozen visual baselines/tolerances/masks unchanged. Full historical whole-band stress PASS is not claimed; RB-010 remains deferred. Catalog/business/media invariants preserved.

All **40 actual PNGs** inspected with vision after deterministic gates: standard 35 modal/address/adversarial/reference/candidate/unmasked-diff images plus five dedicated consent states. Desktop/320/390 storefront reviewed too. Clean independent reference captures retain approved modal/backdrop geometry. Full-content pixel equality is not claimed for owner-requested field/composition changes. Mode/adversarial snapshots after deliberately intercepted valid POST show Woo's synthetic submission-failure banner; it is not a failed normal callback attempt or a visual baseline mask. The independent clean captures and consent-before-submit captures have no such banner. Existing fallback email wording is recorded separately as RB-017.

Standard reviewed manifest: `6a48b3640a7a0dc05756f6ba635962dcd7305b5e9a66be807e0ecbe79f881ba6`.
Five consent-image manifest: `1114ff6a773fcac7b342a44bb413eb13df759a3bbd822c07a9dc40dc56bd7123`.
Artifact **12889638570**, ZIP SHA256 `bb2d5cff41e00520a7ac4fb91f289484a01d04fbe11c3b635bc4c1e8658ef1b2`, verified before extraction. Local proof: `qa/visual-results/callback-consent-40856936705/`, including `vision-review.json`, five `delivery-rules/consent-feedback/` originals and review sheets.

No completed checkout POST, account creation or customer email was performed by worker QA. Completed-order end-to-end dispatch was intentionally not exercised; native validators and actual native pre-submit assembly provide the scoped regression proof. Production untouched.

## Files / delivery

Four application files under `wordpress/wp-content/plugins/rollsbar-core/`: `includes/class-rollsbar-checkout.php`, `includes/class-rollsbar-delivery-checkout.php`, `assets/js/checkout.js`, `assets/css/checkout.css`. No classifier/rule-table or storefront theme changes in this batch. Supporting current-contract PHP fixtures, native browser/address/adversarial gates, narrow deploy preimage and documentation updated. QA expectations explicitly follow the owner's new business policy; strict rule matching and frozen visual reference checks are retained.

Normal commits/push on `wordpress/checkout-visual-parity-2026-10-25`; documentation commit descends from verified application with no application byte changes after acceptance. No reset/force/rebase. RB-016 closed only after inspected exact-release staging finalization.

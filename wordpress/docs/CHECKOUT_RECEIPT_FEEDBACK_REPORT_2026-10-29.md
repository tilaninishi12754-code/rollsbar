# Checkout receipt copy and delivery feedback — 2026-10-29

Status: **STAGING PASS**, RB-015 **DONE**. Production access/mutation: **no**.

Application / verified deployed marker: `53ade0760655cfdee392a2aeb4e34955f223552b`. [Apply and automated checks 40850856268](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40850856268); [inspected finalization 40852211597](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40852211597), receipt `browser_verified`, `DELIVERY_STAGING_PASS`. Fresh verified staging backup: **20261029T093647Z**.

## Owner-visible fixes

1. Native COD title is **Наличными или картой при получении**. Description and thank-you instructions: **Оплатите заказ наличными или картой при получении.** Applies to delivery and pickup; online acquiring is not introduced. Existing COD order titles are corrected at presentation via the native order getter, without rewriting order storage.
2. Native pickup confirmation shipping display is **Самовывоз: Симферополь, Кечкеметская улица, 1**, one address, with no mistranslated collection prefix. Uses supported `woocommerce_order_shipping_to_display` after Woo's own pickup display filter. Native shipping item, cost, structured tax address and historical metadata are retained. Other methods, multiple packages and paid pickup retain their native display.
3. Delivery blockers now appear **next to the native order button** as well as at the address. A blocked click brings the visible address/phone field into view and focuses it. No alternate submission path, no prevention of valid native checkout, and no bypass of minimum/address proof. Sidebar clearance follows actual native action height, including wrapped messages at 320px.
4. Pickup clears the delivery blocker and pending/visible address suggestions. Focusing an already confirmed address for minimum feedback does not reopen suggestions; editing still does. Hidden pickup address fields cannot render late suggestions over the fulfillment toggle.
5. For an exact but unmatched address, text now correctly says its delivery conditions are not yet defined and asks to call. It no longer asks for a house number already present. Coverage and rule classification remain unchanged; map/boundary work deferred by owner.

The reported 1190 ₽ pickup can proceed after native required fields/consent; delivery requires the applicable 1200–4000 ₽ minimum. A missing supported address or unmet minimum must remain blocked, with explicit feedback. No all-address delivery coverage claim is made.

## Evidence and practical limits

Installed Woo **11.1.2** integration PASS on actual staging WordPress **7.1.4**. Native COD gateway title/instructions and actual `thankyou_page()` renderer verified. Unsaved `WC_Order` + `WC_Order_Item_Shipping` fixture passes through the actual shipping display filter and native payment title getter; exact pickup string verified, both object IDs remain zero. No saved order, account or mail was created by worker QA. Completed live order submission was not exercised.

Live Playwright gate **5/5 PASS** at 1440 / 701 / 700 / 390 / 320: explanation beside CTA, blocked-click address focus and viewport visibility, no stale message/popup on pickup, native payment label, full prior native field/session/cart-total/presubmit contracts. Valid delivery payload is assembled through native Woo and intercepted before HTTP. Native POST/schema/signed-proof validation remains authoritative.

Real-address gate **20/20 PASS**, all seven tiers and unknown/ambiguous cases retained. Final adversarial **3/3 PASS** at 320 / 700 / 701, including unresolved-address click rejection before native POST assembly. Immutable modal geometry **5/5 PASS**; original storefront **5/5 PASS**; accepted no-shelf controls **5/5 PASS**. Catalog/media/business invariants retained. Full historical whole-band stress suite is not claimed; RB-010 remains deferred and frozen visual baselines are unchanged.

All **35** CI modal/address/adversarial/reference/candidate/unmasked-diff PNGs inspected with vision after deterministic gates; desktop/320/390 storefront reviewed too. Four supplementary actual CTA-area screenshots at **320/1440**, unresolved and below-minimum, were captured and inspected: explanation and native button both in viewport, no clipping/overlap. Owner-changed content is retained; full-content pixel equality is not claimed, no masks/tolerance relaxation. Native validation screenshots intentionally show unchecked consent errors; native transition screenshots may show temporary loading placeholders, while settled totals have independent Store API assertions.

Reviewed manifest: `2fdc154060eb7aadc652ee1a368062ccafd857b1c09ae74550ab4c976c770558`.
Artifact **12887945450**, ZIP SHA256 `e85490e1e8924750b461c520f1c75dc7af8d662183b2839dd84a5a74b8e11eb7`, verified before safe extraction.
Local evidence: `qa/visual-results/checkout-followup-40850856268/` (including `vision-review.json`, labeled review sheets), supplementary `qa/visual-results/checkout-feedback-2026-10-29/`.

## Scope and release observations

Four application files under `wordpress/wp-content/plugins/rollsbar-core/`: `includes/class-rollsbar-checkout.php`, `includes/class-rollsbar-delivery-minimum.php`, `assets/js/checkout.js`, `assets/css/checkout.css`. No rule-table, storefront theme, cart authority, delivery pricing, map or polygon changes.

Support: native receipt fixtures and live blocked-click checks in `wordpress/deploy/verify-delivery-rules.php`, `qa/checkout/delivery_scenario.py`, `qa/checkout/delivery_adversarial.py`; narrow apply preimage/diagnostics and backup guard; payment-readiness verifier expected copy aligned with the newly approved title; Issue Register/report.

First apply 40849757147 stopped before application mutation because staging independently moved from WP 7.1.3 to **7.1.4**. Read-only run 40850025161 proved actual WP 7.1.4, Woo 11.1.2 and historical backup files present. Backup guard now explicitly accepts only these known WP patches; URLs/environment/Woo version, archives, hashes and historical backup protection remain intact. Worker did not upgrade WordPress. Next live gate exposed lingering suggestions from feedback focus; implementation corrected, then local five-width and full exact-release staging gates passed. No unchanged failed run was blindly retried.

Branch: `wordpress/checkout-visual-parity-2026-10-25`; normal commits/push only. Documentation/QA-copy commit follows the accepted application with no application byte changes. Production untouched; no worker-created orders/accounts/customer mail.

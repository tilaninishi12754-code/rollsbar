# Checkout loading — 2026-10-29

Status: **SAFE ASSET CLEANUP STAGING PASS; COLD LATENCY OPEN**. Production access/mutation: no.

Final application/marker `fb0fb54cb4c9e4015e163f016d5dc0a8252c57df` (application files identical to measured365d95e). Apply [40950660265](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40950660265) success; fresh verified backup **20261029T203821Z**. Inspected finalization [40952441600](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40952441600) success, `phase=browser_verified`, `DELIVERY_STAGING_PASS`. This confirms functional/visual acceptance of the small cleanup, not stable cold-load performance acceptance.

Final gates: native modal/fields/phone/consent/COD/pre-submit5/5, real provider20/20, exact map5/5, adversarial320/700/7013/3, immutable modal chrome/unmasked diffs5/5, original storefront5/5, no-shelf controls5/5, installed native email/COD/geography/catalog/media checks PASS. One Checkout Block / Store API transaction authority, phone plus explicit consent contract, pickup address and guest internal-email compatibility unchanged. No real orders, account creation or client mail.

All45 checkout and30 storefront PNGs actually viewed, plus full desktop/320 stable map originals. Reviewed manifest `6463df18c5c45366e9bebb9c2d54eaf0ce3f5043c5e201c1f7dcafcd717721b0`; screenshot artifact12930594843, verified ZIP SHA256 `b4dedf1008f28087101cf4016bbd098caae32e2b6a35f22b3beacb9c2bf89e51`. Review record `CHECKOUT_LOADING_SCREENSHOT_REVIEW_2026-10-29.json`. Synthetic submit-failure banners retain existing RB-017 explanation; clean reference/map captures confirm normal form. No masks/baselines/tolerances weakened.

Owner reports long cart → checkout and form startup. Actual isolated browser observations reproduced cold form startup around 5.9–11.8 seconds, with HTML TTFB around 0.8–1.1 seconds. Most time was native script transfer/startup. Native assets have public max-age=3888000; blanket Woo/session caching is neither needed nor introduced.

Woo 11.1.2 `src/Blocks/AssetsController.php::add_resource_hints()` speculates on separate cart-page dependencies on checkout. These requests were visible in browser resource timings. A document-only local transform removed them, reducing captured resource entries from up to112 to79, but did not establish a stable form-time improvement. Speculative warm-up on cart activation also failed to establish a stable improvement and is not shipped.

Narrow implementation: suppress prefetch/prerender hints only on active checkout, preserving connection hints and other documents; dequeue the classic `wc-checkout` script at enqueue time only when the designated checkout contains the native Checkout Block. The classic script was observed loading alongside native blocks. Woo's block-render callback schedules its own dequeue after the classic theme's enqueue/head phase, so the earlier hook applies the intended native asset policy in time. No native dependency removal, script bundling, URL changes, field/map/order/validation changes, API caching, session changes or new business rules.

Local behavioral fixture verifies native-only removal, other-route/receipt/classic exclusions and connection hints. Real Woo 11.1.2 email/phone/native contracts PASS; unchanged offline native five-width gate PASS; release-gate tests8 PASS. `qa/checkout/checkout_loading.py` is a separate real-cache timing probe, with isolated cart cleanup and no submit interaction. Functional submission guards and baseline tolerances remain unchanged.

Initial diagnostic5.9–11.8s observations used functional-gate routing, which disables browser HTTP caching. The dedicated un-routed real-cache probe establishes the actual comparable pre-change baseline: desktop1440 cold3.751s / warm1.079s, mobile390 cold6.138s / warm1.050s. Both documents contain51 speculative links and66 external script tags;129 resource entries captured. TTFB0.833s /1.623s respectively. Two samples are observations, not a percentile/service-level guarantee. No native customer fields were filled and no order submission occurred; both isolated carts were cleaned. Evidence: `qa/visual-results/checkout-loading-before/evidence.json`.

Application `365d95e248c42cd32ffd0bb5e18ee5c8a5a257ed`, staging apply40948665799. The deployed probe verifies0 speculative hints and no classic checkout script; external scripts66→62, captured resource entries129→74. Normal-cache observations:

| Viewport | Before cold | After cold | Before warm | After warm |
| --- | --- | --- | --- | --- |
|1440|3.751s|6.528s|1.079s|0.967s|
|390|6.138s|4.355s|1.050s|0.812s|

Desktop did not improve in this sample; mobile did. TTFB also varied (desktop0.833→1.374s, mobile1.623→0.978s). Do not attribute the mobile difference entirely to this change or claim stable cold latency PASS. The cleanup removes proven redundant work; cold native startup remains OPEN. Two initial-state screenshots inspected: mobile map visible, desktop iframe still loading at early timing capture, with form already usable. These are timing snapshots; stable map and visual acceptance use the separate unchanged five-width map/reference gates.

Resource entries are not distinct network transfers: measured transfer bytes742169→719040 (about23KB less), with no duplicate nonzero transfers for the same URL in either baseline or candidate. Do not represent129→74 entries as a43% download-byte reduction or claim that shared prefetch dependencies were downloaded twice. Native dependency download/startup and variable network/server latency remain. Broader concatenation/CDN/hosting work is outside this narrow fix.

Measurement summary with source-evidence hashes: `CHECKOUT_LOADING_MEASUREMENTS_2026-10-29.json`. Actual order submissions0; both isolated carts cleaned.

First apply40948665799 reached backend_verified, backup20261029T202517Z; native form5/5, real provider20/20 and map5/5 PASS. Adversarial320/700 passed,701 timed out waiting for iframe `rollsbarMapReady`30s; no overall acceptance. Unchanged assertion with local added iframe diagnostics then passed320/700/701 on the deployed app; current701 iframe was connected, visible at y363.6px, URL correct, readyState interactive then ready. This does not establish the original timeout's cause. Add persistent request/error/current-frame diagnostics to the same30s assertion before another instrumented CI attempt; no timeout/tolerance increase, production or application workaround. The failure remains explicitly recorded rather than called a successful original run.

Instrumented final apply40950660265 passed the same assertion at all three widths and all remaining gates. Original timeout remains an untriaged observation under RB-020; no claimed application fix or invented cause. RB-019 remains OPEN for cold first-entry latency; broader performance work was not expanded into bundling/CDN/hosting changes.

Changed application: `includes/class-rollsbar-checkout.php` only. QA/report/release additions: `qa/checkout/checkout_loading.py`, `checkout_loading_fixture.php`, diagnostic-only `delivery_adversarial.py`, verified before-image update in `wordpress/deploy/apply_delivery_rules_staging.py`, this report/measurements/review and Issue Register. Normal commits/pushes only; final documentation commit does not alter accepted application files.

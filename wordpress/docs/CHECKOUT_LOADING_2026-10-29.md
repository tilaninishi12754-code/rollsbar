# Checkout loading — 2026-10-29

Status: VERIFY, staging only. Production access/mutation: no.

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

Measurement summary with source-evidence hashes: `CHECKOUT_LOADING_MEASUREMENTS_2026-10-29.json`. Actual order submissions0; both isolated carts cleaned. Final screenshot review/finalization pending.

First apply40948665799 reached backend_verified, backup20261029T202517Z; native form5/5, real provider20/20 and map5/5 PASS. Adversarial320/700 passed,701 timed out waiting for iframe `rollsbarMapReady`30s; no overall acceptance. Unchanged assertion with local added iframe diagnostics then passed320/700/701 on the deployed app; current701 iframe was connected, visible at y363.6px, URL correct, readyState interactive then ready. This does not establish the original timeout's cause. Add persistent request/error/current-frame diagnostics to the same30s assertion before another instrumented CI attempt; no timeout/tolerance increase, production or application workaround. The failure remains explicitly recorded rather than called a successful original run.

# Checkout loading — 2026-10-29

Status: VERIFY, staging only. Production access/mutation: no.

Owner reports long cart → checkout and form startup. Actual isolated browser observations reproduced cold form startup around 5.9–11.8 seconds, with HTML TTFB around 0.8–1.1 seconds. Most time was native script transfer/startup. Native assets have public max-age=3888000; blanket Woo/session caching is neither needed nor introduced.

Woo 11.1.2 `src/Blocks/AssetsController.php::add_resource_hints()` speculates on separate cart-page dependencies on checkout. These requests were visible in browser resource timings. A document-only local transform removed them, reducing captured resource entries from up to112 to79, but did not establish a stable form-time improvement. Speculative warm-up on cart activation also failed to establish a stable improvement and is not shipped.

Narrow implementation: suppress prefetch/prerender hints only on active checkout, preserving connection hints and other documents; dequeue the classic `wc-checkout` script at enqueue time only when the designated checkout contains the native Checkout Block. The classic script was observed loading alongside native blocks. Woo's block-render callback schedules its own dequeue after the classic theme's enqueue/head phase, so the earlier hook applies the intended native asset policy in time. No native dependency removal, script bundling, URL changes, field/map/order/validation changes, API caching, session changes or new business rules.

Local behavioral fixture verifies native-only removal, other-route/receipt/classic exclusions and connection hints. Real Woo 11.1.2 email/phone/native contracts PASS; unchanged offline native five-width gate PASS; release-gate tests8 PASS. `qa/checkout/checkout_loading.py` is a separate real-cache timing probe, with isolated cart cleanup and no submit interaction. Functional submission guards and baseline tolerances remain unchanged.

Staging apply, exact before/after timings, screenshots and final verification pending. Do not claim that the underlying cold native download cost has been eliminated.

# RollsBar Issue Register

Status owner: RollsBar Coordinator
Last updated: 2026-10-28

This file is the durable source of truth for unresolved / deferred RollsBar defects and follow-up work. New confirmed issues should be recorded here instead of living only in chat. Do not reopen items marked DONE without new evidence.

## Workflow

For each issue keep: status, priority, observed evidence, intended batch, acceptance criteria, and final evidence when closed.

Statuses:
- `OPEN` — confirmed and not yet fixed.
- `IN PROGRESS` — assigned to the current batch.
- `DEFERRED` — intentionally postponed; not lost.
- `VERIFY` — implemented but awaiting the required evidence.
- `DONE` — verified and closed.

Priority order unless Coordinator explicitly changes it:
1. Storefront interaction correctness / cart-state reliability.
2. Checkout Final Direct Port / immutable visual parity.
3. Performance and caching.
4. Remaining hardening / deferred project debt.

---

## Current accepted checkpoint

- Branch: `wordpress/checkout-visual-parity-2026-10-25`.
- Checkout Final Direct Port and Storefront Interaction Stability: verified PASS on staging (2026-10-28), apply run 40583002012, finalization 40585851050.
- Deployed application marker: `921698e085263f23493e8f757aa0e7c1b561946c`, receipt `browser_verified`, fresh verified backup `20261027T213818Z`; CSS-only no-shelf controls acceptance run 40588306513. Checkout application bytes remain identical to accepted 529cbf3.
- Client Media Canon `client-media-2026-10-21`: 36 canonical assets, 45 mapped product identities, 57 applied rows, 4 deferred rows preserved.
- Catalog invariant: 118 canonical products / 13 variable parents / 26 variations + 3 hidden staging upsells = 121 published product posts.
- Production remains forbidden without an explicit production gate and authorization.

---

# P0 — completed batch: STOREFRONT INTERACTION STABILITY

## RB-001 — Cart sometimes opens only on the second tap

Status: `DONE`
Priority: `P0`
Scope: storefront / mobile + desktop cart interactions

Observed:
- User reports that after adding a product, tapping the fixed/mobile cart sometimes does nothing on the first tap and opens on the second.
- Intermittent; not every attempt reproduces it.

Investigate:
- DOM rerender replacing an element after Woo/cart mutation;
- stale event handlers versus delegated handlers;
- invisible overlays/backdrops/pointer interception;
- pending cart mutation / race conditions;
- duplicate handlers or click suppression.

Acceptance:
- first intentional tap/click opens the cart reliably after add, reload, and repeated add/decrement operations;
- no double-tap requirement on tested mobile/desktop viewports;
- no regression to cart/session persistence.

Staging investigation: run 40375058146 reproduced fragment/click ordering failure at 701 px. Snapshot application now follows delegated click handling; final run 40463955833 passed at all six widths.

Final evidence: run [40463955833](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40463955833), application b481a6f. Original live UX 5/5 and repeated interaction/hit-target checks at 320/390/430/701/900/1440 all PASS. Local Chromium/WebKit stress 12/12 and original UX 10/10 PASS. Live screenshots reviewed. See `STOREFRONT_INTERACTION_STABILITY_2026-10-26.md`.

## RB-002 — Back-to-top sometimes reacts only on the second tap

Status: `DONE`
Priority: `P0`
Scope: storefront controls

Observed:
- User reports `.client-back-top` intermittently ignores the first tap and works on the second.

Investigate together with RB-001 because a shared pointer/overlay/rerender cause is plausible.

Acceptance:
- first tap always initiates the intended smooth scroll when the control is active;
- no invisible element intercepts pointer events;
- phone/cart/back-to-top controls remain mutually non-overlapping and clickable.

Final evidence: run [40463955833](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40463955833), application b481a6f. Original live UX 5/5 and repeated interaction/hit-target checks at 320/390/430/701/900/1440 all PASS. Local Chromium/WebKit stress 12/12 and original UX 10/10 PASS. Live screenshots reviewed. See `STOREFRONT_INTERACTION_STABILITY_2026-10-26.md`.

## RB-003 — Pizza storefront `+` can reopen selector instead of incrementing the already selected size

Status: `DONE`
Priority: `P0`
Scope: Woo cart snapshot / pizza variation storefront control

Observed:
- User had an already-added pizza variation and pressed `+` on the catalog card.
- Instead of incrementing the same selected size, the product/size selector opened again.
- User reports other pizzas often work normally; issue may depend on cart-state interpretation.
- Screenshot showed a pizza card in an aggregate `N в корзине` state while another pizza had explicit `− N +`.

Required behavior:
- if the card/cart state identifies exactly one existing variation/cart line for that pizza, `+` MUST increment that exact variation directly;
- reopening the selector is only valid when the action is genuinely ambiguous (for example, multiple different sizes of the same pizza are present and no exact target is known);
- never mutate an arbitrary variation.

Acceptance:
- single-size pizza: first `+` increments the exact existing cart line;
- persisted/reloaded single-size cart behaves the same;
- multiple-size case remains safe and unambiguous;
- server Woo cart remains the sole authority.

Additional confirmed cause: run 40378432571 observed a removed line reappearing in the next server read. Native Woo session persistence ran after WordPress output flush. Explicit native save before success/error JSON now passes a 193-check AJAX-boundary regression (old code fails) and the full live acceptance. No alternate cart authority was introduced.

Final evidence: run [40463955833](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40463955833), application b481a6f. Original live UX 5/5 and repeated interaction/hit-target checks at 320/390/430/701/900/1440 all PASS. Local Chromium/WebKit stress 12/12 and original UX 10/10 PASS. Live screenshots reviewed. See `STOREFRONT_INTERACTION_STABILITY_2026-10-26.md`.

## RB-004 — Interaction controls can visually overlap on mobile in some states

Status: `DONE`
Priority: `P0`
Scope: fixed storefront controls

Observed:
- User supplied mobile screenshot where fixed/cart/back-to-top/product controls occupy the same lower viewport area and can visually crowd/overlap content.
- Previous 701–900 px back-to-top clearance fix passed automated tests, but new real-use evidence requires interaction-state coverage rather than geometry-only assumptions.

Acceptance:
- fixed cart, phone, back-to-top and product/card controls remain clickable and visually non-conflicting across real populated-cart states;
- test at least 320, 390, 430, 701 and 900 px widths where relevant;
- include pointer hit-testing, not only screenshots.

Final evidence: run [40463955833](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40463955833), application b481a6f. Original live UX 5/5 and repeated interaction/hit-target checks at 320/390/430/701/900/1440 all PASS. Local Chromium/WebKit stress 12/12 and original UX 10/10 PASS. Live screenshots reviewed. See `STOREFRONT_INTERACTION_STABILITY_2026-10-26.md`.

## RB-005 — Add-to-cart has noticeable ~1–1.5 s feedback delay

Status: `DEFERRED`
Priority: `P1`
Target batch: PERFORMANCE / CART LATENCY

Observed:
- User notices about 1–1.5 s between pressing Add and seeing the cart state update.

Important:
- This is not currently treated as a functional correctness blocker if the native Woo mutation completes correctly.
- In the current P0 batch, ensure the pending period cannot cause duplicate/ignored interactions and has clear UI feedback.
- Actual latency profiling/optimization belongs to the performance batch.
- Completed safety subset in b481a6f: visible pending feedback, disabled duplicate mutation, immediate cart opening while pending, response consistency and error recovery. Verified by live run 40463955833; latency optimization remains deferred.

Future acceptance:
- instrument request/server/UI timings;
- reduce unnecessary cart fragments/payload/work where evidence supports it;
- provide immediate unambiguous pending feedback without inventing a second cart state.

---

# P1 — CHECKOUT FINAL DIRECT PORT

## RB-006 — Checkout visual implementation does not match immutable approved checkout

Status: `DONE`
Priority: `P1` after RB-001..RB-004
Target batch: `CHECKOUT FINAL DIRECT PORT`

Immutable visual source:
`5e7836e22110ec076603bb1fa2b12f8bb90ee756:index.html`

Resolved mismatch (before this batch):
- earlier staging checkout behaved like a route/page sheet;
- approved source is a true fixed modal overlay with backdrop, centered panel, internal scrolling and modal dismissal behavior;
- earlier broad visual PASS was invalid because large differences were classified as acceptable adaptations.

Required approach:
- direct-port the approved shell rather than redesigning it;
- preserve native Woo Checkout Block / Store API / Local Pickup / COD / privacy / Additional Checkout Fields / DaData behavior;
- strict screenshot/reference comparison at desktop and mobile widths;
- no self-waiver of large visual differences as merely acceptable responsive adaptation.

Final acceptance: [apply 40583002012](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40583002012) and [finalization 40585851050](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40585851050), application/marker `529cbf3dc536b13dce40d74bbfbb8d054a9f2cfd`, receipt `browser_verified`, backup `20261027T210114Z`. Native modal 5/5, original storefront UX 5/5, Interaction Stability 6/6, independent post-green adversarial checks PASS. All 32 reference/candidate/diff/map images inspected; reviewed manifest `589fada0f55ad80975b303e65cbbfe84546be17baa573f29c37c543ad0753615`. Approved field set, native email validation/guest mail protection, exact pickup and COD verified. No orders created and production untouched. See `CHECKOUT_FINAL_DIRECT_PORT_REPORT_2026-10-27.md`.

---

# P2 — PERFORMANCE / CACHE

## RB-007 — Product images do not all appear quickly on first load

Status: `DEFERRED`
Priority: `P2`
Target batch: `PERFORMANCE / MEDIA DELIVERY`

Observed:
- client product photos can visibly load progressively rather than appearing quickly together.

Investigate with measurement:
- actual rendered dimensions versus source/served dimensions;
- WordPress responsive image `srcset/sizes` usage;
- thumbnail generation / correct card-size derivative;
- WebP/AVIF where appropriate;
- eager loading only for above-the-fold/LCP images;
- lazy loading below the fold;
- HTTP/browser caching and CDN viability;
- transfer size, server TTFB and image decode timing.

Do not replace Client Media Canon source-of-truth semantics while optimizing delivery derivatives.

## RB-008 — Post-deploy stale CSS/JS may persist in embedded/in-app browser sessions

Status: `DEFERRED`
Priority: `P2`
Target batch: `PERFORMANCE / CACHE`

Observed:
- after the mobile header fix, a clean URL load in the normal browser displayed correctly;
- an already-open/embedded Google browser session could still show old behavior.

Likely area to verify:
- static asset versioning/cache-busting;
- browser/proxy/CDN cache headers;
- whether deploy changes always produce new CSS/JS URLs/versions.

Acceptance:
- a new release references a deterministic new asset version when bytes change;
- stale long-lived clients do not silently keep incompatible application JS/CSS indefinitely.

---

# DEFERRED DATA / PROJECT DEBT

## RB-009 — Customer products `Охотничья` and `Салями` have no canonical source IDs

Status: `DEFERRED`
Priority: `P3`

Preserved in Client Media Canon:
- 4 spreadsheet rows;
- 2 product identities;
- customer images/assignments retained;
- no new Woo products created.

Requires a later explicit catalog decision; do not guess IDs.

## RB-010 — Back-to-top / other approved historical elements must remain covered by regression tests

Status: `DEFERRED`
Priority: `P3`

The control has been restored. Keep regression evidence so later checkout/performance changes do not silently remove it again.

2026-10-28 UI follow-up: client requested removal of the full-width control shelf. Focused five-width control/hit/first-tap proof passes at application 921698e. The historical whole-band occlusion assertion remains unchanged; a future approved QA contract migration must reconcile it with the new visible-catalog-between-controls requirement. No full legacy stress PASS is claimed for this CSS-only follow-up.

## RB-011 — Public `/wp-content/debug.log` hardening tail

Status: `DEFERRED`
Priority: `P3`

Previously identified project hardening debt. Verify/remove public exposure before production readiness if still applicable.

## RB-012 — WooCommerce update available but intentionally not auto-applied

Status: `DEFERRED`
Priority: `P3`

Accepted current Woo version during prior staging work. Do not combine a Woo core/plugin update with functional/checkout fixes unless explicitly scheduled with regression coverage.

---

## RB-013 — Full-width white shelf obscures the lower catalog

Status: `DONE`
Priority: `P1`

Client screenshots showed an unwanted white bottom band on desktop/mobile. CSS-only removal hides the shelf and preserves individual back-to-top/cart/phone controls and scroll clearance. Staging run [40588306513](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40588306513), application `921698e085263f23493e8f757aa0e7c1b561946c`, fresh backup `20261027T213818Z`, receipt `browser_verified`. Focused 320/390/701/900/1440 empty/populated-cart checks PASS, nine-point control hit tests and first cart/back-top activations PASS. Desktop/mobile staging screenshots inspected. Checkout bytes unchanged; no production access. See `CONTROLS_NO_DOCK_2026-10-28.md`.

---

# Closed / accepted context

## RB-014 — Delivery/pickup scenario and automatic free-delivery minimum

Status: `IN PROGRESS`
Priority: `P1`

Owner authorized the combined 2026-10-28 batch. Implemented locally: native fulfillment toggle, conditional customer address/details, one address field, always-open native comment, hidden map; 92-cell source rule registry and signed DaData identity with pre-order Store API enforcement. Mazanka = 4000. Unknown/ambiguous/approximate addresses fail closed. Local deterministic and native five-width browser gates PASS; fresh staging deploy/live address coverage and final regressions pending. Existing RB-006 acceptance remains historical and does not certify this new candidate. See `DELIVERY_RULES_AUTO_MINIMUM_2026-10-28.md`.

Do not reopen without new evidence:

- `CLIENT PRODUCT MEDIA CANON`: PASS — 57 applied / 4 deferred / 61 preserved.
- `STOREFRONT UX FINAL FIXES`: PASS for its original acceptance set.
- mobile sticky header: clean fresh browser load reported correct by user; stale embedded-session behavior is tracked separately as RB-008.
- checkout native Woo safety and Final Direct Port modal/field acceptance are PASS; RB-006 is DONE with exact-release staging evidence.

---

# Planned execution order

1. `STOREFRONT INTERACTION STABILITY` — RB-001, RB-002, RB-003, RB-004. RB-005 only gets pending-state/race-safety work here; latency optimization remains deferred.
2. `CHECKOUT FINAL DIRECT PORT` — RB-006.
3. `PERFORMANCE / MEDIA / CART LATENCY / CACHE` — RB-005, RB-007, RB-008.
4. Final cross-site QA and production-readiness gate.
5. Remaining P3 debt as explicitly scheduled.

# RollsBar Issue Register

Status owner: RollsBar Coordinator
Last updated: 2026-10-29

This file is the durable source of truth for unresolved / deferred RollsBar defects and follow-up work. New confirmed issues should be recorded here instead of living only in chat. Do not reopen items marked DONE without new evidence.

## RB-019 — Checkout cold loading and redundant assets

Status: VERIFY. Priority: P2. Owner-authorized narrow checkout latency investigation, 2026-10-29.

Reproduced cold cart → checkout form5.9–11.8s, HTML TTFB0.8–1.1s; script transfer dominates. Remove active-checkout speculative cart assets and the classic checkout script on the native block route. No blanket cache/session changes. Local five-width native/contract fixtures PASS; live acceptance and measured improvement pending. Full evidence: `CHECKOUT_LOADING_2026-10-29.md`. Broader RB-005/RB-007/RB-008 work remains deferred.

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
- Current deployed application marker: `a4d5e5a68c59bb7904c36749b2dfadf828c67a22`, receipt `browser_verified`, fresh backup `20261029T102229Z`; callback/required-consent apply 40856936705, inspected finalization 40858251322. Required customer input: phone plus explicit consent; name/address/minimum advisory. Native 5/5, addresses 20/20, adversarial 3/3, immutable geometry 5/5, storefront 5/5 and controls 5/5 PASS. All 40 modal/reference/consent images inspected. See `CHECKOUT_PHONE_ONLY_REQUEST_2026-10-29.md`; earlier acceptance is historical.
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

Owner-requested 2026-10-28 follow-up: delivery/pickup field composition and hidden map are verified at application `8568c10a14c2d74771f9f8fcc0e5b8a9c31acc3e`, apply 40718770624/finalization 40720499963. Immutable modal chrome remains 5/5 PASS, all 35 current screenshots inspected. This supersedes prior field composition only; original acceptance remains historical. See RB-014 and its report.

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

Status: `DONE`
Priority: `P1`

Owner-authorized combined batch verified on staging: native Delivery/Pickup first, pickup name/phone only plus exact restaurant address; delivery uses one address field, optional details and always-open native comment, map hidden. All 92 source cells retained; seven automatic free-delivery minimums enforced server-side before native Store API checkout. Mazanka = 4000. Unknown/unverified-house and unresolved boundary identities fail closed without invented thresholds.

Final evidence: [apply 40718770624](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40718770624), [finalization 40720499963](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40720499963); application/marker `8568c10a14c2d74771f9f8fcc0e5b8a9c31acc3e`, receipt `browser_verified`, fresh verified backup `20261028T154410Z`. Native five-width gate 5/5, real addresses 20/20 (two per tier plus exceptions), adversarial 320/700/701 3/3, immutable modal geometry 5/5, original storefront 5/5 and accepted no-shelf controls 5/5 PASS. All 35 reference/candidate/diff/address/modal/adversarial PNGs inspected; reviewed manifest `8fd3f8b66ddcb4be91ce8ceabf8157195ac0cc18d3232566536c7e67bad748fd`. Native COD, Additional Fields, totals, email privacy and guest contracts PASS without creating an order/account/mail. Production untouched. RB-010 historical whole-band QA migration remains deferred. See `DELIVERY_RULES_AUTO_MINIMUM_2026-10-28.md`.

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


## RB-015 — Receipt payment/pickup copy and silent delivery validation

Status: `DONE`
Priority: `P1`

Owner's 2026-10-29 screenshots resolved on staging: native COD consistently says cash/card at receipt; native pickup receipt has one address and no collection mistranslation. Delivery address/minimum blocker is visible next to CTA; click focuses/scrolls to the problem, valid native submit retained. Pickup clears pending suggestions, eliminating a pointer interception exposed by live QA. Exact unmatched-address wording corrected; minimum rules/coverage not relaxed.

[Apply 40850856268](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40850856268), [finalization 40852211597](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40852211597); application/marker `53ade0760655cfdee392a2aeb4e34955f223552b`, receipt `browser_verified`, fresh backup `20261029T093647Z`. Installed native receipt renderer/order-display fixtures PASS without saving orders; live five-width feedback/native gate 5/5, addresses 20/20, adversarial 3/3, immutable geometry 5/5, storefront 5/5 and no-shelf controls 5/5 PASS. All 35 CI screenshots + four CTA closeups and storefront images inspected. Manifest `2fdc154060eb7aadc652ee1a368062ccafd857b1c09ae74550ab4c976c770558`. No worker-created order/account/mail; production untouched. Map/boundaries and RB-010 remain deferred. See `CHECKOUT_RECEIPT_FEEDBACK_REPORT_2026-10-29.md`.


## RB-016 — Callback submission with phone and explicit consent

Status: `DONE`
Priority: `P1`

Owner's updated 2026-10-29 contract: complete phone + explicit consent required; name/address/details/comment and free-delivery minimum do not block a callback request. No fabricated consent. Unchecked consent gets CTA explanation, red block/background, focus and scroll into view; marker clears after checking. Native Store API/order/session/COD/email safety retained, delivery rule matching remains advisory and does not invent thresholds.

[Apply 40856936705](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40856936705), [finalization 40858251322](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40858251322); application/marker `a4d5e5a68c59bb7904c36749b2dfadf828c67a22`, browser_verified, fresh backup `20261029T102229Z`. Installed native validators PASS; live 5/5 covers phone-only-with-consent assembly, absent-name/address, below-minimum acceptance, unchecked-consent rejection/marker/focus/clear. Address 20/20, adversarial 3/3, geometry 5/5, storefront 5/5 and no-shelf controls 5/5 PASS. All 35 standard + five consent PNGs inspected. Standard manifest `6a48b3640a7a0dc05756f6ba635962dcd7305b5e9a66be807e0ecbe79f881ba6`; consent manifest `1114ff6a773fcac7b342a44bb413eb13df759a3bbd822c07a9dc40dc56bd7123`. No completed order POST/account/customer mail by QA; production untouched. Earlier required-name/address/minimum acceptance is historical. See `CHECKOUT_PHONE_ONLY_REQUEST_2026-10-29.md`.

## RB-017 — Native submission-failure fallback mentions email in phone callback UX

Status: `DEFERRED`
Priority: `P2`

Observed during deliberate QA pre-submit rejection: Woo's generic failure banner says to check email, although this guest flow has no customer email. Normal fresh checkout/consent-error captures do not show it; actual native callback assembly passes. This is existing failure-copy debt, not a commercial validation blocker. Keep native error/retry protection; a later narrow copy change should explain retry/contact by phone without claiming the request was accepted when submission failed. Do not hide real errors or fabricate success. Evidence: intercepted POST mode/adversarial snapshots in run 40856936705. Outside RB-016 minimal consent/required-fields scope.

## RB-018 — Geographic delivery boundaries need client review

Status: `DONE — OWNER-AUTHORIZED ADVISORY MAP ON STAGING`
Priority: `P2`

Owner initially requested a review-only map from the existing table: `delivery-draft-2026-10-29/index.html`. All 92 source cells retained; 83 geographically linked, five ambiguous section rows and four unlocated landmarks remain explicitly unresolved. All seven minimums represented, Mazanka = 4000. Geographic matching and inferred city territories do not prove client-confirmed commercial boundaries; no delivery radius or delivery fee invented.

Later owner instruction explicitly authorized using the draft now without waiting for client review. Delivered on staging: map below native address, hidden for pickup; exact table identities before provisional exact-house geographic fallback; all seven free-delivery minimum levels; marker clears on edit; popup and modal Escape work. Phone + explicit consent remain the only submission prerequisites. Approximate/ambiguous/outside-geography cases remain manager clarification without refusing a callback. The user's 2nd Collective Gardens street/34 example still has provider qc_geo=2 and receives no invented house minimum.

Application/marker `6a44a669045dfd40491b3f37f90c6548cf2d1b85`; [apply 40939565647](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40939565647), [finalization 40941633703](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40941633703), browser_verified, fresh verified backup `20261029T192407Z`. Native five widths 5/5, provider addresses 20/20, map/popup/Escape 5/5, adversarial 3/3, immutable modal geometry 5/5, original storefront 5/5 and no-shelf controls 5/5 PASS. All 45 checkout + 30 storefront PNGs inspected; manifest `b22cac1f048ae8f2424227e5417d996627a50a3a711d02dcde61055dcdda67bc`. No completed order POST/account/customer mail performed by QA; production untouched. Full report `CHECKOUT_DELIVERY_MAP_2026-10-29.md`. Client-verified business boundaries remain a known future refinement, not an assertion made by this advisory release.

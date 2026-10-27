# Storefront interaction stability — 2026-10-26

Status: PASS — exact-release staging acceptance verified on 2026-10-27.

## Reproduced mechanisms

- RB-001: releasing an add response between native pointer down/up replaces the visible round cart with the order bar. Before fix, drawer remained hidden; the pointer-up target was the new total element.
- RB-002: the same response moves back-to-top upward 12 px. A pointer down five pixels inside its lower edge then misses at pointer up. Before fix, scroll remained 1000.
- RB-003: the storefront snapshot never refreshed after another window/native Woo changed its cart. A two-size card kept its aggregate selector even after the server had only one line. A fresh server read before an aggregate action now selects the exact sole existing line, or keeps genuine ambiguity safe. Focus/visibility return also reconciles with Woo. These are proven mechanisms, not a claim to have captured the user's original device session.
- Normal isolated staging add probes succeeded for all 12 pizzas. No evidence of duplicate representations or zero lines in those native Woo snapshots; no speculative backend grouping change was made.

## Implementation

The latest server snapshot waits until a native pointer gesture completes before replacing targets. Native click remains the only activation event; no synthetic retries, guessed timers, global pointer blocking, or optimistic cart state. Cart opens immediately during a pending mutation and receives its queued canonical response. Pending feedback and duplicate suppression preserve server authority; failure reconciles without replaying the mutation.

Application changes are app.js/app.css and the native cart AJAX response boundary. Checkout, catalog data and Client Media Canon are unchanged. RB-005 latency work remains deferred.

## Verification

- `qa/visual/interaction-stability.mjs`: Chromium + WebKit at 320/390/430/701/900/1440; controlled response between down/up for cart/back-top, four repeated mutation/open/close/back-top cycles, reload, single pizza plus, two sizes, external two-to-one transition, removal/re-add, duplicate suppression and failed-response recovery. Screenshots plus elementFromPoint evidence for empty/populated cart, phone and back-top.
- `qa/visual/storefront-ux.mjs`: original ten engine/viewport combinations PASS, including simple/detail quantities, options, exact pizza lines, drawer, search and header.
- PHP cart 133, storefront 158, B12 870 checks; media canon contract PASS. Deployment scope/backup/proof tests PASS.
- Local screenshots inspected at 320/390/430. An opaque bottom dock now separates fixed controls from scrolling card actions. Hit-test sampling across the dock rejects any catalog target beneath it; native document scrolling, modal placement and header behavior are preserved. Screenshots at 320/390/430 were inspected.

## Release

Completed by run 40463955833. The dedicated `interaction-stability` operation requires a fresh verified backup, allows only three application files against accepted application 328cb664d1d6e6a63b300e6788a984497fa1320d, preserves all other application hashes and business digest, and requires both original live UX acceptance and six-width stress proof before marking the release browser_verified.

Production access/mutation: no. No checkout orders. Checkout Final Direct Port not started.

## Staging investigation

- Run 40324792261: fresh backup 20261026T124458Z and original live UX PASS; stress failed when an expected pizza line was absent from the next read. No browser_verified marker was written. A local live 320 px diagnostic rerun passed; this observation is retained rather than erased.
- Run 40375058146: original live UX PASS; stress 320/390/430 PASS, 701 failed because a native cart click navigated to /cart/. Response journal showed a correct single simple-product line and no drawer read. Local reproduction using the old application and Woo-style fragment replacement deterministically reproduced this exact navigation.
- Root cause of the latter failure: a microtask queued by a capture listener can execute before delegated click listeners. It detached the fragment child, so closest() no longer found the cart trigger and preventDefault was skipped. Snapshot application now runs after the module's delegated click handlers. Local regression now includes fragment DOM replacement; the ordinary fixture previously omitted that Woo behavior.
- Next release preflight uses the inspected 2c4b1bf backend files, while keeping the two-file scope check against accepted 328cb664. Final marker remains unchanged until complete live acceptance.

- RB-004 review found a genuine 430 px back-top/card-action overlap in live screenshots. The fixed controls now have an opaque bottom dock, below their z-index and above catalog content, with bottom scroll clearance. No invisible blocking layer, pointer-events workaround, or alternate cart state was added. The regression samples the dock area with elementFromPoint as well as the fixed controls themselves.
- Browser harness waits for completed navigation before imposing a test scroll position; this avoids WebKit's late reload history restoration undoing the test's setup scroll. Mutation response races are still deliberately exercised between native pointer down/up.
- Updated original UX: 10 PASS; B13 visual gate: 10 PASS / 6 existing skips; normal-motion back-top: four first taps in each engine PASS.

- Run 40378432571: backup 20261026T183211Z, backend verified at 7e584a2; original UX failed at 390x900 when a removed pizza line reappeared in the immediate server read. Marker was not advanced.
- Installed WooCommerce 11.1.2 saves session at shutdown priority 20, while WordPress 7.1.3 flushes output at priority 1. Explicit native session save now precedes success/error JSON; totals populate native session first. This fixes response/read consistency without changing cart keys or introducing a second authority.
- Official source: https://github.com/woocommerce/woocommerce/blob/11.1.2/plugins/woocommerce/includes/class-wc-session-handler.php and https://github.com/WordPress/wordpress-develop/blob/7.1.3/src/wp-includes/default-filters.php .
- New real AJAX-boundary fixture fails the previous implementation with “Response published before native session persistence”; patched implementation passes 193 checks, four add/read/plus/error/remove/read cycles and 32 saves before response. The final deployment guarded observed 7e584a2 backend files and permits only the three named application files against accepted 328cb664.

## Final acceptance — 2026-10-27

- Run: https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40463955833 (success).
- Application and finalized staging marker: `b481a6fa3d2db7a5524667c51d263ceb117a05d7`; receipt `phase=browser_verified`, `UX_RELEASE_PASS`.
- Fresh backup: `20261027T065607Z`, verified before mutation. Business digest unchanged: `f6ac2c1c227e658b06b50e5a6b6abfa5680e00d3c5030b521c35726e3cc71068`.
- Original live UX: 5/5 PASS. Live interaction stress: 6/6 PASS at 320/390/430/701/900/1440, four repeated interaction cycles per width plus controlled pointer/response races, reload, exact pizza and true multi-size cases, remove/re-add and error recovery. Every reserved-dock hit sample passed.
- Local browser evidence: stress 12/12 Chromium/WebKit, original UX 10/10, B13 10 PASS / 6 pre-existing skips. New native persistence boundary: 193 checks / 32 saves before JSON; release guard tests: 5 PASS.
- Catalog 118 / 13 / 26 + 3 and media 36 assets / 45 identities remain verified. Checkout code unchanged; no orders created. Production access/mutation: no.
- Downloaded evidence artifact `12715622946`; SHA256 `22da61036e7930d9380aed117eb5a61727b42bfe37869e977fdffe38f6de7f28` matches GitHub digest. Local extracted evidence: `qa/visual-results/interaction-staging-final/`.
- Visually inspected populated screenshots at every stress width, empty 900, pending 390, original 320x568 controls and 430 product detail. Fixed controls are separated from catalog hit targets; pending acknowledgement is visible. Two lazy-loaded images in the first 900 screenshot are present in the subsequent empty-cart screenshot; media mapping/hash gate passes.
- RB-001/002/003/004: DONE. RB-005: DEFERRED for latency; pending/race-safety subset DONE. Checkout Final Direct Port not started.
- Final follow-up commit changes documentation only; deployed application remains b481a6f.

## Checkout Final Direct Port regression — 2026-10-28

Application/marker `529cbf3dc536b13dce40d74bbfbb8d054a9f2cfd`, apply run [40583002012](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40583002012), finalized by [40585851050](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40585851050). Original live UX 5/5 and unchanged Interaction Stability 6/6 at 320/390/430/701/900/1440 PASS; populated screenshots at all six widths inspected. Independent post-green checkout/return smoke also PASS. Storefront application files remain unchanged; checkout's native commerce speculation exclusions prevent background session interference. Catalog/media and business guards PASS. RB-001..RB-004 remain DONE, RB-005 latency work deferred. No orders created; production untouched. See `CHECKOUT_FINAL_DIRECT_PORT_REPORT_2026-10-27.md`.

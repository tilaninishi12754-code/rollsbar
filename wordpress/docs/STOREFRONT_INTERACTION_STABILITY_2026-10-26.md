# Storefront interaction stability — 2026-10-26

Status: VERIFY — local acceptance passed; exact-release staging acceptance pending.

## Reproduced mechanisms

- RB-001: releasing an add response between native pointer down/up replaces the visible round cart with the order bar. Before fix, drawer remained hidden; the pointer-up target was the new total element.
- RB-002: the same response moves back-to-top upward 12 px. A pointer down five pixels inside its lower edge then misses at pointer up. Before fix, scroll remained 1000.
- RB-003: the storefront snapshot never refreshed after another window/native Woo changed its cart. A two-size card kept its aggregate selector even after the server had only one line. A fresh server read before an aggregate action now selects the exact sole existing line, or keeps genuine ambiguity safe. Focus/visibility return also reconciles with Woo. These are proven mechanisms, not a claim to have captured the user's original device session.
- Normal isolated staging add probes succeeded for all 12 pizzas. No evidence of duplicate representations or zero lines in those native Woo snapshots; no speculative backend grouping change was made.

## Implementation

The latest server snapshot waits until a native pointer gesture completes before replacing targets. Native click remains the only activation event; no synthetic retries, guessed timers, global pointer blocking, or optimistic cart state. Cart opens immediately during a pending mutation and receives its queued canonical response. Pending feedback and duplicate suppression preserve server authority; failure reconciles without replaying the mutation.

Only app.js/app.css are application changes. Checkout, catalog data and Client Media Canon are unchanged. RB-005 latency work remains deferred.

## Verification

- `qa/visual/interaction-stability.mjs`: Chromium + WebKit at 320/390/430/701/900/1440; controlled response between down/up for cart/back-top, four repeated mutation/open/close/back-top cycles, reload, single pizza plus, two sizes, external two-to-one transition, removal/re-add, duplicate suppression and failed-response recovery. Screenshots plus elementFromPoint evidence for empty/populated cart, phone and back-top.
- `qa/visual/storefront-ux.mjs`: original ten engine/viewport combinations PASS, including simple/detail quantities, options, exact pizza lines, drawer, search and header.
- PHP cart 133, storefront 158, B12 870 checks; media canon contract PASS. Deployment scope/backup/proof tests PASS.
- Local screenshots inspected at 320/390/430. An opaque bottom dock now separates fixed controls from scrolling card actions. Hit-test sampling across the dock rejects any catalog target beneath it; native document scrolling, modal placement and header behavior are preserved. Screenshots at 320/390/430 were inspected.

## Release

Pending. The dedicated `interaction-stability` operation requires a fresh verified backup, allows only two application files against accepted application 328cb664d1d6e6a63b300e6788a984497fa1320d, preserves all other application hashes and business digest, and requires both original live UX acceptance and six-width stress proof before marking the release browser_verified.

Production access/mutation: no. No checkout orders. Checkout Final Direct Port not started.

## Staging investigation

- Run 40324792261: fresh backup 20261026T124458Z and original live UX PASS; stress failed when an expected pizza line was absent from the next read. No browser_verified marker was written. A local live 320 px diagnostic rerun passed; this observation is retained rather than erased.
- Run 40375058146: original live UX PASS; stress 320/390/430 PASS, 701 failed because a native cart click navigated to /cart/. Response journal showed a correct single simple-product line and no drawer read. Local reproduction using the old application and Woo-style fragment replacement deterministically reproduced this exact navigation.
- Root cause of the latter failure: a microtask queued by a capture listener can execute before delegated click listeners. It detached the fragment child, so closest() no longer found the cart trigger and preventDefault was skipped. Snapshot application now runs after the module's delegated click handlers. Local regression now includes fragment DOM replacement; the ordinary fixture previously omitted that Woo behavior.
- Next release preflight uses the inspected 2c4b1bf backend files, while keeping the two-file scope check against accepted 328cb664. Final marker remains unchanged until complete live acceptance.

- RB-004 review found a genuine 430 px back-top/card-action overlap in live screenshots. The fixed controls now have an opaque bottom dock, below their z-index and above catalog content, with bottom scroll clearance. No invisible blocking layer, pointer-events workaround, or alternate cart state was added. The regression samples the dock area with elementFromPoint as well as the fixed controls themselves.
- Browser harness waits for completed navigation before imposing a test scroll position; this avoids WebKit's late reload history restoration undoing the test's setup scroll. Mutation response races are still deliberately exercised between native pointer down/up.
- Updated original UX: 10 PASS; B13 visual gate: 10 PASS / 6 existing skips; normal-motion back-top: four first taps in each engine PASS.

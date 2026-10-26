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
- Local screenshots inspected at 320/390/430. Fixed controls remain visually separated; scrolling catalog content naturally passes behind visible fixed controls. Real target checks, rather than screenshot-only acceptance, guard activation.

## Release

Pending. The dedicated `interaction-stability` operation requires a fresh verified backup, allows only two application files against accepted application 328cb664d1d6e6a63b300e6788a984497fa1320d, preserves all other application hashes and business digest, and requires both original live UX acceptance and six-width stress proof before marking the release browser_verified.

Production access/mutation: no. No checkout orders. Checkout Final Direct Port not started.

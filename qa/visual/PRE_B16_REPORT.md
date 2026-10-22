# PRE-B16 responsive and cross-browser QA

Status: **PASS**. Dedicated local QA batch. **B16 NOT STARTED**.

## Preflight

- First Git command: `git rev-parse --show-toplevel` → `C:/AI/Rolls Bar Project`.
- Branch: `wordpress/visual-parity-2026-10-14`.
- Starting HEAD: `548ad7e9e75216807a4161a0a778b6efeb08c614`; initial tree CLEAN.
- Approved ref: `refs/remotes/origin/approved/site-2026-10-01` →
  `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
- Read targeted B6B report/geometry, current baseline manifest, accepted exceptions,
  runner/config and B11–B15 interaction/measurement helpers. No history reread.

## Runtime and local environment

| Runtime | Version | Playwright revision |
|---|---|---|
| Node | v24.19.0 | — |
| Playwright | 1.64.1 | locked, unchanged |
| Chromium | 156.0.8078.4 | 1248 |
| Firefox | 157.0 | 1555 |
| WebKit | 27.2 | 2370 |

Firefox/WebKit were absent and installed with the existing Playwright CLI, without
dependency/package upgrades. Chromium was already installed. Browser paths and
actual launched versions are recorded in the JSON evidence. The sandboxed Firefox
process failed to connect to Playwright within 180 seconds; outside that restricted
environment it launched and ran successfully. Full browser QA uses that local
execution environment. No external testing service is involved.

## Original Chromium gate and protected images

Before QA infrastructure/application edits, the unmodified normal command passed:
**166 passed /18 explicit skips /0 failed**, no retries. Independent verification
confirmed all **285/285** protected PNG SHA256 values. The initial result summary
was preserved under ignored `qa/visual-results/pre-b16/initial-gate.json`.

Final normal gate: **166 passed /18 explicit skips /0 failed**, no retries or
flaky tests (184 tests, 5.2 minutes). All **285/285 protected hashes preserved**;
the screenshot manifest and all old expected images remain unchanged. **0 new
baseline screenshots; 285 final total**. Diagnostic failure PNGs from probe runs
are ignored artifacts, not screenshot baselines; the final successful matrix
produced no screenshots.

## Dense geometry/behavior layer

Command: `node qa/visual/pre-b16.mjs` (`npm run pre-b16-qa`).

The exact grid is the union of `320 + 20*n`, `n=0..56`, and explicit 390/breakpoint
neighbors: **69 widths**, inclusive **320–1440**, maximum gap **20 CSS px**.
Required neighbors include 699/700/701, 899/900/901, 1023/1024/1025,
1049/1050/1051 and 1439/1440. Every point uses an isolated deterministic local
cart/browser context. No screenshot comparison or capture occurs on success.

The same reusable flow runs at every sampled width:

- Global overflow, actual body/html overflow styles, visible header controls and
  pairwise collisions; promo/grid/card containment; sticky category geometry.
  The existing header border can meet the sticky region by its 1px border.
- All 126 card representations before and after representative counters:
  footer/action containment, rectangle and price-ink overlap, clipping and actual
  painted price bounds. Existing B11 narrow wrapping and B6B geometry remain.
- Details open/close, panel bounds/internal scrolling, reachable close button,
  Escape/focus restoration and exact page-scroll restoration.
- Native variable selector, WOK sauce and shrimp sauce selection/add, native
  controls and selector CTA bounds, closure, focus and body unlock.
- Simple add/increment/decrement/remove-to-zero; Catalog/Hits synchronization;
  large-price/accent counters; header/mobile totals compared with local cart state.
- Exactly one visible cart trigger in empty/populated states; order bar visibility
  on either side of 700px, header/mobile routing on either side of 900px.
- Drawer plus/minus/remove, reachable controls and close; long cart with 15 seeded
  canonical simple products, real internal vertical scrolling and bottom controls.
- Search open/query/result → canonical details; no-results Escape, opener focus,
  panel/input/result containment; body/inert restoration.
- True page-bottom footer/link reachability and hit testing while cart is populated;
  links above the fixed mobile control; final empty-cart keyboard access.
- Uncaught application errors and console warnings must both be zero. The existing
  local harness's deliberately aborted external-resource load messages are excluded.

Actual per-width metrics, failed state/exception and JS lists are written
incrementally to `PRE_B16_RESPONSIVE_CROSS_BROWSER.json`. Diagnostic runs cannot
produce a full PASS status. Full completion verifies exact engine/width membership
and protected hashes again. An interrupted earlier run is retained separately as
ignored evidence; the acceptance run starts fresh and completes the entire matrix.

Result: **69/69 PASS, 0 failed**. All required breakpoint neighbors passed.
Horizontal overflow, clipping/off-screen critical-control failures and application
JS errors/warnings: **0**. Body/html horizontal overflow suppression: **absent**.

## Firefox and WebKit

Each engine runs the entire representative flow above at **1440 /1051 /1050 /1024
/701 /700 /390 /320**. No comparison against Chromium rasterization is used.
Each context independently checks exact canonical identity membership, **118
products /126 cards /8 Hits /13 variable parents /26 variations /6 WOK /18 WOK
choices /3 shrimp choices**. Representative native selection/mutation flows use
nuggets, chicken udon and shrimp. Exhaustive business choice paths remain covered
by existing Chromium/PHP regressions.

- Firefox: **8/8 PASS**, overflow/clipping/off-screen critical-control failures
  **0**, application JS errors/warnings **0**, no application/browser exceptions.
- WebKit: **8/8 PASS**, overflow/clipping/off-screen critical-control failures
  **0**, application JS errors/warnings **0**, no application/browser exceptions.

The completed acceptance JSON contains **85 PASS rows /0 FAIL**, ten completed
flow states per row and **285/285** protected hashes verified before/after.
An independent readback checked all 85 completed rows, card/price failure lists,
JS lists and exact details scroll-restoration positions. No earlier diagnostic
or interrupted result is included in this acceptance matrix.

Browser differences handled in QA, without application styling changes:

1. Firefox returns a positive `scrollWidth` for inline contact links with
   `clientWidth=0` (e.g. 142px text inside the viewport). B15's shared overflow
   helper now checks inline client rectangles rather than subtracting a nonexistent
   client box. Block/scroll container checks remain; viewport bounds and hit tests
   remain mandatory. Native inline metrics are preserved in the JSON evidence.
2. Playwright WebKit may scroll the opener before dispatching a click behind
   sticky navigation. Details restoration is compared with scroll position at the
   actual opening event, recorded in capture phase, rather than pre-action position.
   Application scrolling, panel geometry and exact restoration are still asserted.

No browser-specific screenshot allowance or application CSS exception was added.

## Narrow application correction

`wordpress/wp-content/themes/rollsbar-theme/assets/js/app.js`: search Escape could
leave focus on the now-hidden search input in all three engines. On close, when no
other overlay is active and focus is still within search, return it to the search
opener with `preventScroll:true`. Background/inert/modal behavior and business
semantics stay unchanged. The new flow checks this focus return at every width.
No application CSS, catalog, prices, Woo provisioning or templates were changed.

QA changes: new standalone runner and package command, README, B15 inline geometry
measurement correction, this report and JSON evidence. Existing normal screenshot
configuration, accepted exceptions and baseline manifest are untouched.

## Static and regression checks

- PHP lint: **33 files PASS**.
- B11 PHP cart contract: **133 assertions PASS**.
- B12 PHP contract: **812 assertions PASS**, 148 line paths, 13/26 variations,
  18 WOK and 3 shrimp choices, canonical/hidden-product separation.
- B15 PHP contact contract: **22 assertions PASS**.
- Changed application JS, new runner and changed helper Node syntax: **PASS**.
- `git diff --check`: **PASS** (line-ending notices are not diff errors).
- Full existing Chromium gate: **166 passed /18 explicit skips /0 failed**.
  B1–B15 accepted state and B6B CLOSED/PASS are preserved. Existing B6B tests
  retain ordinary/accent 17px/23px desktop lower insets and measured mobile
  geometry. B11/B12 exhaustive choice, synchronization and recovery tests,
  B13 totals/transitions, B14 canonical search and B15 footer regressions pass.

## Preservation and limits

All browser requests/mutations are localhost fixture work. No staging/production
access or mutation, live Woo database verification, deployment, push, checkout,
reset, merge or rebase. AGENTS.md and skills are untouched. No broad overflow
suppression, clipping, hidden controls, reduced coverage or tolerance increase.
Existing B7 containment, B9 accessibility, B11 wrapping, B13 capture isolation,
B15 broken-logo handling and B6B ordinary/accent lower-inset distinctions remain
subject to the unchanged Chromium visual gate.

The three hidden upsell-only products remain outside the canonical 118. Their
20 RUB demo seed is **PROVISIONAL**, requiring owner/client confirmation before
production. Local adapters do not verify live Woo prices/availability/provisioning.

## Commit and next

Exactly one local PRE-B16 commit is allowed after full PASS; its SHA/final clean
HEAD will be returned in the completion message (avoiding a self-referential SHA).
Return the report to Coordinator. **Do not start B16 automatically.**

No PRE-B16 QA blockers remain. The provisional upsell price and live Woo/backend
verification above remain deferred business/runtime work and are not closed here.

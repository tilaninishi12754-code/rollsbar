# Batch 11 acceptance — 2026-10-22

Status: PASS (local only). One batch; B12+ not started; B6B remains open.

## Preflight

First Git command: `git rev-parse --show-toplevel` → `C:/AI/Rolls Bar Project`.
Branch `wordpress/visual-parity-2026-10-14`; starting HEAD
`e11ee14576ae8f3d832287b469060a05810a2b18`; initial porcelain status empty.
`refs/remotes/origin/approved/site-2026-10-01` resolved to
`a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.

Initial normal Visual Gate: 80 tests PASS / 96 screenshot assertions.
`npm` was absent from PATH, so all gate runs used the README's equivalent bundled
Node invocation, `node qa/visual/run.mjs test`.

## Approved evidence and implementation

Read immutable objects with `git show`, and captured the approved page through
the existing `git archive` preview. No approved checkout/reset occurred.

- Approved `client-fixes.html:289–318`: canonical cart-derived counts, original
  add/minus forwarding, simple icon → counter; decrement to zero restores icon.
- Approved `client-fixes.html:323–387`: first valid selector choice by default,
  selected variant/option labels forwarded to original add; successful add closes
  selector. Variable/custom-option card control remains a chooser after adding.
- Approved `index.html:957–989`: option-dependent line identity, selected price,
  repeated identical choices increment their line, removal at zero.
- Approved `demo.html` final action CSS: 42px desktop/38px mobile cart icons;
  counters use 34/30/34px desktop and 30/27/30px mobile columns. No separate
  post-add success toast exists in this path.

Application files changed:

- `plugins/rollsbar-core/includes/class-rollsbar-cart-actions.php` (new), plus
  plugin bootstrap registration: nonce-protected Woo AJAX action; native
  `WC()->cart->add_to_cart()` / `set_quantity()`; server product/parent/variation
  and exact custom-option validation; native validation filters; canonical count
  snapshot; existing Woo fragments; error notices. Selected options are native
  cart-item data, participate in Woo line identity/session persistence, appear in
  item data and are copied to order-line metadata. No browser price is trusted.
- Theme `functions.php`: generated Woo endpoint/nonce configuration.
- Theme `assets/js/app.js`: one server-derived count map indexed by source ID;
  all duplicate controls render from it. In-flight actions are guarded, failures
  reconcile with a read without retrying a possibly committed mutation. Valid
  selector actions submit selected variation/options; success closes the panel.
  Errors remain visible near the action; success has screen-reader status and
  approved counter/close feedback. Keyboard focus survives control replacement.
- Theme `front-page.php`: remove obsolete disabled-CTA tooltip.
- Theme `assets/css/app.css`: approved controls and enabled CTA; real footer
  wrapping resolves narrow geometry without clipping/masking cards/pages.

Official API reference consulted:
[Woo WC_Cart](https://woocommerce.github.io/code-reference/classes/WC-Cart.html),
[Woo AJAX source](https://woocommerce.github.io/code-reference/files/woocommerce-includes-class-wc-ajax.html).

## Deterministic functional proof

Extended the existing PHP catalog preview rather than replacing the template or
rebuilding the storefront. The localhost endpoint executes the production plugin
mutation seam against a test native-cart API adapter; this is NOT a running
WordPress/Woo database/backend verification. Header subtotal fixture remains zero.

- `cart-contract.php`: 133 assertions PASS; 13 parents/26 variation choices;
  six WOK products/18 choices and shrimp/3 choices; native variation attributes;
  option item/order metadata; repeat merge, decrement/remove and repeat-zero;
  wrong source, missing/foreign/unavailable variation, unknown/nested option,
  invalid action and native validation-filter rejection without cart mutation.
- Browser exhaustive mutations PASS at 1440 and 320: all 47 choices, all eight
  Hits mappings, synchronized duplicate simple counts, both duplicate selector
  entry points, invalid selection, server rejection, failure/recovery, keyboard,
  X/backdrop/Escape, focus restore/reset, detail add and simultaneous activation.
- Geometry and 126 representations/118 identities checked at all eight widths.
- Uncaught JS errors and application console warnings/errors: zero. Deliberately
  aborted external resource console messages are excluded from the local fixture.
- PHP lint: seven changed/new PHP files PASS. Node syntax: application JS and
  three gate modules PASS. `git diff --check`: PASS.

## Visual Gate and geometry

New expected images were generated ONCE by the explicit approved-only path
`node qa/visual/run.mjs baseline b11`: 16 tests / 48 screenshot assertions.
Normal mode has snapshot updates disabled. The runner now rejects changes to
already-manifested baseline hashes even in explicit generation mode.

Final normal gate: **106 PASS, 6 explicit skips, 0 unexpected, 0 flaky**.
There are 144 screenshot assertions: original 96 PASS + new B11 48 PASS.
The six skips are only exhaustive mutation duplicates at intermediate widths;
visual assertions and geometry run at every width.

| Width | Original visuals | B11 visuals | Page overflow | Card action overflow | Selector/action overflow |
|---:|:---:|:---:|---:|---:|---:|
| 1440 | PASS | PASS | 0px | 0px | 0px |
| 1051 | PASS | PASS | 0px | 0px | 0px |
| 1050 | PASS | PASS | 0px | 0px | 0px |
| 1024 | PASS | PASS | 0px | 0px | 0px |
| 701 | PASS | PASS | 0px | 0px | 0px |
| 700 | PASS | PASS | 0px | 0px | 0px |
| 390 | PASS | PASS | 0px | 0px | 0px |
| 320 | PASS | PASS | 0px | 0px | 0px |

All original 96 file SHA256 values were independently compared with both the
starting HEAD manifest and current file bytes: unchanged. Existing tolerances
are unchanged. New snapshots cover simple add / quantities 1 and 2, variable
chooser, valid enabled selector CTA and post-add chooser state at all widths.

One exact B11 exception: `b11-simple-counter.png` and `b11-simple-repeat.png`,
320px only. Each measures **38 differing pixels**, verified with the pinned
Playwright comparator at its default 0.2 threshold and zero diagnostic allowance.
Those pixels are the approved adjacent price contaminating the upper-left rounded
corner where its unwrapped footer overlaps the counter. Current wrapping removes
that obstruction. Cap 38, identical dimensions; all other B11 targets cap 0.
No baseline rewrite, screenshot mask or broad overflow suppression was used.

Normal JSON/HTML/trace results are disposable under ignored
`qa/visual-results/normal/`; per-width `overflow.json` attachments contain the
measured values above. No diagnostic scripts/runtime output is committed.

## Preservation / deferred

B1–B10 preserved by unchanged data/identity/media/price paths and passing original
gate; 17px/23px bottom insets untouched. B6B exact footer parity remains OPEN.
No B12 cart drawer, B13 header/mobile total redesign, B14 search, B15 footer or
B16 final audit. Live prices/stock/backend remain NOT LIVE-VERIFIED. No database
catalog changes, staging/production operation, push/deploy/merge/rebase, or
AGENTS/skill modification. Return this batch to Coordinator; do not start B12.

# Batch 13 — Header / mobile cart totals

Status: **PASS — full B13 local deterministic acceptance**.
Final normal gate: **134 passed / 18 explicit skips**, no snapshot updates.
The original 12 skips remain; six additional B13 exhaustive-mutation copies at
intermediate widths are explicit because geometry and approved states run at all
eight widths and the shared mutation implementation runs at 1440 and 320.
Local deterministic acceptance only;
staging and production were not accessed.

## Preflight

- First Git command: `git rev-parse --show-toplevel` → `C:/AI/Rolls Bar Project`.
- Branch: `wordpress/visual-parity-2026-10-14`.
- Starting HEAD: `dcfcc1ab1ce9f992f1ab837fbe2c1a65a3d82ed2`.
- Initial working tree: CLEAN.
- Approved ref: `refs/remotes/origin/approved/site-2026-10-01`.
- Approved SHA: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
- Initial gate: **124 passed / 12 explicit skips**, no snapshot updates.
- All **224** original manifest entries and PNG SHA256 values verified against
  starting HEAD before application edits and again after B13 baseline generation.

`npm run visual-test` was attempted first, but this host has no npm executable.
The exact package script, `node qa/visual/run.mjs test`, was run with the bundled
Node executable instead. No package installation or package-script change.

## Immutable approved B13 evidence

All source references in this section are to Git objects at the approved SHA,
read without checkout. Baseline mode archives that SHA into a temporary folder,
serves its unmodified `demo.html > client-fixes.html > index.html` iframe chain,
and disables current-theme rendering.

- `demo.html:26–33`: Russian quantity pluralization, including teens.
- `demo.html:84–96`: full-width floating order bar, icon, count, hint, total;
  desktop total divider/font and approved cart-button treatment.
- `demo.html:98–113`: order bar visible only through 700px, 86px bottom page
  reservation, desktop total hidden on mobile; 701px starts the hidden-bar range.
- `demo.html:118–130`: desktop total appended to the existing header button;
  mobile labels `Перейти в корзину`, `Открыть корзину` and bag SVG.
- `demo.html:133–169`: quantity is the sum of line quantities, total comes from
  the existing cart summary; floating bar only for a nonempty cart with cart UI
  closed; clicking it delegates to the existing drawer trigger.
- `index.html:188–225`: empty mobile cart is a 54px circular red control at
  right/bottom 14px, cart SVG and white quantity badge; mobile actions through 700px.
- `index.html:786`: ru-RU monetary grouping and ordinary space before the ruble sign.
- `index.html:995–1029`: canonical demo count/subtotal and drawer open/close.

Desktop header remains the accepted B2 structure. It shows `Корзина`, quantity
badge and subtotal, including `0 ₽` when empty. The existing header hides through
900px. At 701–900px the prior accepted B12 fallback drawer control remains available;
the approved order bar is never invented at 701px. Through 700px, empty state uses
the circular cart control; populated state uses the approved order bar instead.
The order bar hides while the drawer is open and returns on close when nonempty.

## Implementation

- Theme `assets/js/app.js`: one presentation function consumes the existing B12
  snapshot after every canonical cart response, including fragment replacement.
  Quantities come from server-backed lines; money remains the server subtotal.
  Only whitespace is adapted to approved ru-RU grouping; no price calculation,
  monetary parsing, optimistic count, second store or polling observer is added.
- Drawer open/close and viewport resize reproject that same snapshot. New order-bar
  clicks use B12's request queue, fresh read and existing drawer. Final removal
  returns focus to a visible empty control if the original order-bar opener vanishes.
- Incomplete error replies cannot replace confirmed header/mobile totals; the
  existing B11 error message and recovery path remain intact.
- Theme `footer.php`: cart controls only, outside footer content; approved empty
  SVG and separate populated order bar. The SVG survives Woo inner-fragment replacement.
- Theme `assets/css/app.css`: scoped approved control rules and 700px switch.
  No B2 header layout, mascot/logo/phone/search/menu/sticky/category offsets changed.
- Theme `functions.php`: decode Woo subtotal entities before safely escaping
  initial/fragment header text, avoiding literal HTML entities in the visible total.
- QA: `gate.spec.mjs`, `run.mjs`, `b12-overflow.mjs`, manifest, exception record,
  this report and **24** new approved-only PNGs.

## Coverage and results

- B11 PHP regression: **133 assertions PASS**.
- B12 PHP contract: **812 assertions PASS**, 148 line paths; 118 main products,
  3 separate hidden upsells, 13 variable parents / 26 variations, 6 WOK products /
  18 choices, shrimp / 3 choices. Confirmed shrimp values remain
  `чесночный`, `сырный`, `томатный`.
- B13 browser cases compare header/badge/order-bar values against an independent
  server read after every mutation: empty, simple card add, repeated quantities
  1–25 with pluralization, card decrement, Catalog/Hits duplicates, native pizza
  variation, WOK option, confirmed shrimp option, drawer plus/minus/remove, upsell,
  final removal, keyboard trigger, Escape, opener disappearance and focus fallback.
- Both desktop and narrow-mobile mutation runs traverse every required breakpoint
  with a populated cart, reopen the B12 drawer and verify current totals and focus.
- Existing B11/B12 browser coverage retains all 8 Hits mappings, every canonical
  variation/option, rejection handling, lost-response reconciliation, scroll/body
  locks, inert state and drawer/selector transitions.
- Width matrix: **1440 / 1051 / 1050 / 1024 / 701 / 700 / 390 / 320**, height 900,
  DPR 1. Geometry at all eight; exhaustive mutation at 1440 and 320.
- 24 new PNGs: one-item, quantity-two, selected pizza + WOK multi-item at four
  desktop and three mobile widths (21), plus empty circular control at three mobile
  widths (3). Existing eight empty-header snapshots remain the desktop empty proof.
  At 701px there is no approved visible header/order bar to capture; visibility,
  geometry and retained B12 fallback behavior are checked functionally.
- Populated 15-line cart overflow QA: **0px page / header / mobile control / drawer /
  drawer content / card action / selector** at all eight widths; internal vertical
  drawer scrolling present; JS errors zero.
- PHP lint, application/test/runner Node syntax and `git diff --check` PASS.

Final full Visual Gate: **134 passed / 18 explicit skips**, all 152 tests accounted
for. Application JS errors/warnings: **0**. Protected original **224/224** hashes
match the starting HEAD; all **248** current manifest hashes pass. No old PNG was
modified and normal mode generated no expected screenshots.

## Narrow capture exception

Only `b13-empty-mobile.png` uses a white **54×54** backing plate immediately behind
the circular control in both sources. This isolates the underlying deferred page
rows visible at the button's rounded corners. Unisolated measured differences:
700px = 0, 390px = 76, 320px = 166 raster pixels. All control pixels, SVG, badge,
position and dimensions remain tested. No masks or pixel allowances are introduced;
new screenshots require zero differing pixels. All earlier exceptions stay intact.

## Preservation and deferred items

- B1–B12 acceptance retained; final full gate PASS.
- Protected PNGs: **224 unchanged + 24 new = 248**; manifest provenance unchanged.
- Main catalog: **118 canonical / 126 DOM representations including 8 Hits**.
- Three upsell-only entities remain outside those 118. Their **20 RUB** remains
  provisional approved-demo data, requiring owner confirmation before production.
- B6B remains **OPEN**. B14 Live Search, B15 footer/contacts and B16 not started.
- Delivery/payment/checkout business rules unchanged. No live Woo database claim:
  local adapter executes the real theme and plugin seams, not a deployed WordPress DB.
- No staging/production access, checkout/reset/merge/rebase/push/deploy.
- AGENTS.md and skills untouched.

The only production prerequisites retained from B12 are owner confirmation of
upsell prices and normal environment-specific native Woo provisioning/verification.
No additional B13 product-data decision is introduced.

Exactly one local B13 commit is permitted only after full acceptance; its SHA and
final clean-tree evidence belong in the completion response.

Next: return this report to Coordinator; do not start B14 automatically.

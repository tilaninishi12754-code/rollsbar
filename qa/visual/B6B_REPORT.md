# Batch 6B — Product-card footer / action-row parity

Status: **PASS — B6B CLOSED**. B6B only; local deterministic acceptance.

## Preflight

- First Git command: `git rev-parse --show-toplevel` → `C:/AI/Rolls Bar Project`.
- Branch `wordpress/visual-parity-2026-10-14`.
- Starting HEAD `af7773955101eed006447a43c56de69f74cebc71`; initial tree CLEAN.
- Approved ref `refs/remotes/origin/approved/site-2026-10-01` resolved to
  `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
- Before application edits: normal Visual Gate **158 passed / 18 explicit skips**.
  Independently verified all **268/268** starting PNG hashes. npm unavailable;
  used the unchanged package script through the proven bundled Node executable.

## Immutable approved contract

Evidence read with `git show` and the existing approved-only `git archive` preview,
without checkout or ref changes. Final cascade is demo → client-fixes → index.

- `demo.html:52–58,68–81`: card overflow hidden; body padding 14px/15px/16px;
  footer full body width, row flex, center alignment, space-between, 8px gap,
  minimum height 44px. Price starts at the footer's left edge; its box is 42px high
  at y=1px. `client-fixes.html:79`: 18px bold price, line-height 1; old price hidden.
- Ordinary desktop footer: x=16px inside card, width=card−32px, bottom inset=17px.
  Accent: `client-fixes.html:85–94`, outer padding 10px, body sides/bottom 12px:
  footer x=23px, width=card−46px, bottom inset=23px. The 6px difference is approved.
- `demo.html:74,77–81`: action wrapper minimum height 42px; add/chooser 42×42px,
  radius 15px, 1px border, approved gradient/shadow, centered 21px cart icon.
  `client-fixes.html:100–106`: counter columns 34/30/34px plus border =100×40px;
  buttons 34×38px, 19px heavy minus/plus, 12px heavy quantity, pill radius.
  Variable prefix is 12px/800/#777, baseline aligned immediately before the amount.
- `demo.html:105–111`, `client-fixes.html:183–194`, `index.html` mobile footer rule:
  at/below 700px, price 16px, box 38px high at y=3px; actions 38×38px at y=3px,
  radius 14px, 20px icon; counter 30/27/30 columns plus border =89×37px.
  Footer stays at least 44px high; margin-top=8px replaces bottom auto alignment.
  Accent outer padding becomes 7px, footer x=20px, width=card−40px.
  The measured accent lower gap is 22.5px for the representative pizza, and a
  taller neighboring title can add whitespace. These existing mobile effects stay.
- `client-fixes.html:269–274,395–410`: highlight only the first approved copy;
  canonical simple counters and option/variation chooser delegation.

Approved visual geometry is reused around current Woo controls. No demo cart state,
static prices or duplicate selector implementation was imported.

## Implementation and coverage

Application change: **only** theme `assets/css/app.css`. Restore body-width footer,
44px minimum row height, approved native price typography/baselines, control wrapper
height and card-level approved clipping. Preserve B6A bottom padding. Retain B11
counter wrapping when price and quantity cannot fit. Add/chooser/counter pixels,
PHP markup, pricing logic, Woo actions and application JS remain canonical.

QA changes: `gate.spec.mjs`, new `b6b-card-helpers.mjs`, runner B6B target, README,
`accepted-exceptions.json`, baseline manifest, 17 new PNGs, this report and
`B6B_GEOMETRY.json`. No package/dependency or browser-infrastructure change.

The new suite measures all **126 representations / 118 identities / 8 Hits** at
each width. Ordinary simple, accent simple (soup/set), ordinary variable (nuggets),
accent variable (pizza), options (six WOK + shrimp), add/counter, actual Hits,
largest canonical price (Мега сет, 3200 RUB), long titles/compositions and existing
missing/fallback media are included in the real rendered grid. No accent option
product exists in the canonical catalog; none was invented.

## Geometry and exceptions

All values are CSS pixels. Full actual/approved card, footer, price, action bounds,
separations, counter states and overflow evidence: **B6B_GEOMETRY.json**.

| Width | Ordinary card W×H | Footer top within card | Footer W | Accent footer W | Ordinary bottom | Accent bottom | Add/chooser | Counter | Ordinary counter row H |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|1440|280×423.72|362.72|248|234|17|23|42×42|100×40|44|
|1051|237.75×401.19|340.19|205.75|191.75|17|23|42×42|100×40|44|
|1050|300×443.72|382.72|268|254|17|23|42×42|100×40|44|
|1024|300×443.72|382.72|268|254|17|23|42×42|100×40|44|
|701|209.67×373.11|312.11|177.67|163.67|17|23|42×42|100×40|44|
|700|330.5×399.11|338.11|298.5|290.5|17|22.5|38×38|89×37|44|
|390|175.5×277.53|216.53|143.5|135.5|17|22.5|38×38|89×37|44|
|320|140.5×246.28|185.28|108.5|100.5|17|22.5|38×38|89×37|83|

**17/23 B6A distinction preserved: YES.** Mobile values are explicitly measured,
not normalized to a fabricated 17px accent inset.

Narrow declared exceptions; **no new screenshot tolerance, masks or global cap**:

1. At 320px, a 108.5px footer cannot fit 41.56px price +8px gap +89px counter.
   Approved shrinks the price box to 11.5px; its actual text extends underneath
   the counter (measured text/action rectangle intersection 816.31px²). Retain
   B11's wrapping: footer 83px, counter y=46px, bottom inset still 17px; current
   glyph overlap/clipping zero. Accent/long-price counters similarly wrap when
   needed. Existing protected B11 narrow counter images/cap remain unchanged;
   new counter-row screenshot uses the exact approved desktop geometry.
2. Preserve accepted canonical accent styling on both Catalog/Hits copies.
   Approved accents only the first representation; corresponding current copies
   compare against the approved accent geometry. All other Hits compare by section.
3. Component capture origins rounded within half a CSS pixel; no style/size changes.
   Width comparison allows 0.02px for one 1/64px grid-column allocation unit at
   701px. Native price NBSP shaping can differ by about 0.02px in bounds; all new
   screenshot comparisons remain zero differing pixels. At 320px the accent price
   flex box differs by 0.44px while its painted price/action pixels match exactly.
4. First final full run: 165 passed /18 skips /1 failure, exclusively two pixels at
   x=17/18,y=0 in protected 320px `b13-one.png`. Restored B6B row placement exposed
   different content through the order bar's rounded corner, outside its fill.
   B13 capture-only isolation now reuses its existing white backing technique in
   the exact 292×64px populated-bar rectangle at 320px, underneath the control in
   both sources. All control pixels, geometry, totals and application CSS remain
   unchanged; backing is removed before functional checks. No masks, allowances
   or old PNG/hash changes. Other widths retain their existing captures.

Neighbor alignment: desktop footer bottoms follow their ordinary/accent insets;
mobile retains approved top margin and neighboring-title whitespace. Card clipping
matches approved rounded bounds and cuts only decorative shadow; real actions,
price glyphs, counters and focus paths remain usable.

## Functional / static QA

- B6B targeted suite: **8/8 PASS**, with 17 exact screenshot comparisons.
- Existing B11/B12/B13/B14/B15 tests run unchanged in the final full gate:
  simple add/repeat/plus/minus/zero; all 47 variation/option choices; Catalog/Hits
  synchronization; rejection/recovery; details and selectors; drawer/header/mobile
  totals; search → details → cart; keyboard/focus/Escape/body-scroll restoration.
- PHP B11 contract **133 assertions PASS**; B12 **812 assertions PASS**, 148 line
  paths, 13 parents/26 variations, six WOK/18 choices, shrimp/3 choices; B15 **22 PASS**.
- Existing populated-drawer helper passes all eight widths with 15 lines and
  internal vertical scrolling intact. Independent all-card checks include actual
  price text paint bounds and card scroll widths, beyond action rectangles.
- PHP lint, application/test/helper/runner Node syntax and `git diff --check`: PASS.
- Application JS errors/warnings: **0**; external aborted-resource messages are
  filtered by the existing local harness. Node FORCE_COLOR/NO_COLOR runner notices
  are not application warnings.
- Local PHP/Woo adapters execute the real template and mutation seam. They do not
  claim live WordPress/Woo/database verification. No backend environment accessed.

At **1440 /1051 /1050 /1024 /701 /700 /390 /320**, all of these are **0px**:
page horizontal overflow; card horizontal overflow; action-row overflow; price
paint outside card; current price/action overlap; lower-row/action clipping;
header/search; mobile cart/order controls; populated drawer/content; selectors;
website footer/content. No page-wide overflow suppression was added.

## Visual Gate / preservation

- Initial: **158 passed /18 explicit skips**. Final full normal gate:
  **166 passed /18 explicit skips /0 failed** (184 tests, no retry).
  B13 targeted after capture isolation: **10 passed /6 explicit skips**.
- **268/268 original PNG/hash values unchanged**, independently compared with
  starting HEAD manifest; **285** final manifest entries valid.
- **17 new** approved-only PNGs: six footer classes × desktop/narrow, one desktop
  counter row, ordinary/accent lower frame × desktop/narrow. Actual `#hits` scoped
  capture is explicit. No expected image was generated from current rendering.
- B1–B15 preserved; canonical 118 / DOM 126 / Hits 8 preserved. B8 native min price
  (`get_variation_price('min', true)` → `wc_price()`), B10 selection data/flows and
  B11 native Woo cart semantics untouched. Three hidden upsells remain excluded
  from canonical/search; their 20 RUB seed remains PROVISIONAL and outside B6B.
- pre-B16 responsive/WebKit/Firefox gate NOT started; B16 NOT started.
- No delivery/checkout/payment/notifications/MAX/email/analytics/business-data work.
  No staging/production, checkout/reset/merge/rebase/push/deploy. AGENTS/skills untouched.

## Commit / next

Exactly one local B6B commit follows final PASS. Its SHA and final clean
HEAD are returned in the completion message, avoiding a self-referential report SHA.
Return this report to Coordinator. Do not start the pre-B16 gate or B16 automatically.

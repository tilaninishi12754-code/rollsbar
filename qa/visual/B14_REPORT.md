# Batch 14 — Live Search only

Status: **PASS — full B14 local deterministic acceptance**.
Final normal gate: **150 passed / 18 explicit skips**, no snapshot updates.
Local deterministic acceptance; staging and production were not accessed.

## Preflight and initial gate

- First Git command: `git rev-parse --show-toplevel` → `C:/AI/Rolls Bar Project`.
- Branch: `wordpress/visual-parity-2026-10-14`.
- Starting HEAD: `d54588e931985766cd317b6c72ec8097ea2590ac`; initial tree CLEAN.
- Approved ref: `refs/remotes/origin/approved/site-2026-10-01`.
- Approved SHA: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
- Initial normal gate: **134 passed / 18 explicit skips**.
- All **248** starting PNG SHA256 values verified before edits.
- This host exposes no npm executable. Ran the unchanged package script
  `node qa/visual/run.mjs test` through the existing bundled Node executable;
  no dependency installation or package/script repair.

## Recovered approved contract

All locations below refer to immutable Git objects at the approved SHA, read
without checkout. Baselines run its original `demo.html > client-fixes.html >
index.html` iframe chain with current-theme rendering disabled.

- `index.html:358–392`: search geometry, input/result styling, 760px desktop
  panel, 92px desktop top padding; through 700px, 72px top padding, 8px sides,
  22px panel radius, smaller result media. Search remains available in the header
  at every tested width; the 900px rule changes its toggle size.
- `index.html:505–518`: backdrop, dialog, native `type=search` input, close button,
  metadata and scrollable results. No extra submit button or custom clear control.
- `index.html:1145–1169`: local product array, Russian category labels; lowercase,
  ё→е, punctuation→spaces, collapsed whitespace; opening renders the retained query,
  locks body scrolling and focuses/selects the input after 40ms. Close button,
  backdrop and Escape close; another active modal retains its scroll lock.
- `index.html:1170–1194`: exact title 100, title prefix 80, title substring 65,
  category substring 45, composition substring 30. Highest matching rule wins.
  Sort descending score, then `localeCompare(name,'ru')`; cap at 16.
  Empty normalized query shows the first eight canonical products in source order.
  Metadata and no-results copy are reproduced literally.
- `index.html:1196–1225`: each result is a button with media, name, category and
  composition, and base price. Click closes search and opens existing product
  details after 40ms. Enter activates the first result; no results means no action.
  Native Tab/Shift+Tab remains native; no arrow navigation or search focus trap.
  Input events render immediately: no debounce, endpoint, fuzzy matching,
  highlighting or invented token matching.
- `index.html:786,831–837`: approved money/media presentation. Closing with the
  button/backdrop retains the query. Chromium's native search-input Escape also
  clears its value; this is verified against the running approved UI.

## Implementation and changed files

- Theme `header.php`: homepage-only approved dialog markup. Existing header
  layout/toggle and non-homepage native product-search form remain intact.
- Theme `front-page.php`: tiny read-only search membership/category/composition
  JSON. Source-order records join the already-filtered public Woo products by
  `_rollsbar_source_id`; names, prices and images reuse existing detail data.
  The existing `_rollsbar_upsell_only` exclusion and canonical membership prevent
  all three hidden upsells from entering search. Hits does not create new records.
- Theme `assets/js/app.js`: approved normalization/scoring/sorting/rendering and
  lifecycle. Result actions delegate to the existing canonical product link,
  preserving B9 details, B10 selectors and B11/B12 native cart actions. Search
  price presentation removes only the catalog's “от” label from Woo's existing
  minimum-price markup; no cart calculation or product data is changed.
- Theme `assets/css/app.css`: scoped approved search styles, 700px breakpoint,
  inherited typography and B7 media containment. No header redesign or broad
  page overflow suppression.
- QA: `gate.spec.mjs`, `b14-search-helpers.mjs`, `run.mjs` (B14 targeting only),
  `accepted-exceptions.json`, baseline manifest, this report and **10 new PNGs**.
  Package files, Woo/core plugin, product/category/business data are unchanged.

## Functional and regression evidence

- B14 targeted browser suite: **16/16 PASS**.
- At every width, **133 queries** are executed against both current and the
  unmodified approved UI, including all **118 exact canonical titles**. Result
  identity, order, count, title, category/composition text and displayed price
  must match. Every exact title must return its own canonical ID.
- Membership is exactly the 118 packaged public IDs in approved order; all 126
  DOM cards map onto that same set. No duplicate search IDs, including Hits;
  no hidden `upsell-*` IDs, even for queries matching their names.
- Empty/whitespace/punctuation, exact/partial/mixed case, Cyrillic, ё/е,
  category/composition, multiple/zero matches, clearing by input and keyboard,
  retained query, selection on reopening, native Escape behavior, Enter with and
  without results, native Tab/result activation, close/backdrop/repeated cycles.
- Ordinary simple, variable and Hits product results open the canonical detail;
  simple add and variable/option selection/add retain accepted cart behavior.
  Drawer opening/closing, category navigation, scroll restoration and removal
  of modal inert state are exercised after search transitions.
- **Application JS errors/warnings: 0**. Node runner environment color warnings
  are unrelated to application/browser JS. External image requests are blocked
  consistently by the established local QA harness.
- B11 PHP contract: **133 assertions PASS**.
- B12 PHP contract: **812 assertions PASS**, 148 line paths, 118 main products,
  3 hidden upsells, 13 variable parents/26 variations, 18 WOK choices and the
  three previously confirmed shrimp choices.
- PHP lint, application/helper/test/runner Node syntax, `git diff --check`: PASS.

## Geometry, screenshots and overflow

All eight viewports use height 900, DPR 1. Unmodified current/approved search
geometry is compared for empty starters, pizza results, variable/no-image result
and no results: panel/head coordinates and sizes, every result row, visibility
and overflow. Shared result implementation is captured at desktop/mobile extremes.

| Width | Page | Header/search | Panel/results | Drawer/content | Card action | Selector |
|---:|---:|---:|---:|---:|---:|---:|
| 1440 | 0px | 0px | 0px | 0px | 0px | 0px |
| 1051 | 0px | 0px | 0px | 0px | 0px | 0px |
| 1050 | 0px | 0px | 0px | 0px | 0px | 0px |
| 1024 | 0px | 0px | 0px | 0px | 0px | 0px |
| 701 | 0px | 0px | 0px | 0px | 0px | 0px |
| 700 | 0px | 0px | 0px | 0px | 0px | 0px |
| 390 | 0px | 0px | 0px | 0px | 0px | 0px |
| 320 | 0px | 0px | 0px | 0px | 0px | 0px |

Drawer/action/selector measurements rerun the existing `b12-overflow.mjs` with
15 server-backed cart lines; internal vertical drawer scrolling remains present.
Search evidence is attached as `b14-contract.json` in each Playwright project.

New snapshots: eight no-results panels (including input/header geometry), plus
two complete two-result Tyahan panels at 1440/320. All generated exclusively from
the immutable approved source. Zero new differing-pixel allowance and no masks.

Narrow capture exception: only the search backdrop is #f3f4f5 with no blur in
both sources during B14 screenshots. Unisolated corner-background differences
were **8/1/107/107/126/0/28/151 pixels** in width-matrix order. This isolates
deferred page content at rounded corners; actual search geometry uses the
unmodified backdrop. No panel/result/input styles are normalized for captures.

B7 preservation detail: approved `index.html:281,835` positions a no-image
fallback absolutely without positioning its search-media parent. For “Наггетсы”
the approved fallback covers **760×225px** at 1440 and **304×205px** at 320,
obscuring the dialog. The required existing B7 resolver/containment is retained:
current fallback is exactly its **72×64px / 62×58px** media box. All eight widths
measure this explicitly. Useful approved result snapshots therefore use existing
local Tyahan sprites; no-image/variable/starter behavior still receives complete
functional and geometry coverage. This existing B7 behavior is not regressed to
the approved source's unintended full-panel placeholder overlay.

Final full normal gate: **150 passed / 18 explicit skips**, all 168 tests
accounted for. All previous 18 skips remain unchanged; B14 adds no normal-mode
skips. All **248/248** starting-HEAD PNG hashes remain unchanged; all **258**
current manifest hashes pass. Normal mode generated no expected screenshots.

## Preservation and scope

- 118 canonical public products / 126 DOM cards / 8 Hits; three hidden upsells
  remain separate. Product/category/business data and cart totals semantics unchanged.
- B1–B13 protected states remain under the full gate; B6B remains **OPEN**.
- B15 footer/contacts and B16 final parity were not started. No delivery,
  acquiring/payment, checkout administration or new catalog administration work.
- No staging/production access, checkout/reset/merge/rebase/push/deploy.
  AGENTS.md and skills untouched.
- Existing production prerequisites remain: owner confirmation of provisional
  upsell prices and environment-specific native Woo provisioning/verification.
  This local adapter executes actual theme/plugin seams, not a deployed Woo DB.

Exactly one local B14 commit is permitted after full PASS; commit SHA and final
clean-tree evidence belong in the completion response.

Next: return report to Coordinator. Do not start B15 automatically.

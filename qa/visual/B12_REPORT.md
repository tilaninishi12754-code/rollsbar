# Batch 12 — Cart Drawer

Status: **PASS — local deterministic B12 acceptance**. Final normal gate:
**124 passed / 12 explicit skips**, snapshot updates **none**. The six original
B11 skips plus six B12 exhaustive-mutation copies at intermediate widths are
intentional; geometry and screenshots run at all eight widths.

## Preflight and baseline protection

- Physical root: `C:/AI/Rolls Bar Project` (first Git command was `git rev-parse --show-toplevel`).
- Branch: `wordpress/visual-parity-2026-10-14`.
- Starting HEAD: `17d0a3013b2dd0fb44d227344b9b47a3323e26f5`.
- Resumed dirty tree matched the six saved B12 draft files; nothing reset, stashed or discarded.
- Approved ref: `refs/remotes/origin/approved/site-2026-10-01`.
- Approved SHA: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
- Initial normal gate: **106 passed / 6 explicit skips**, no snapshot updates.
- All existing **144** manifest entries and PNG SHA256 values matched before work.
- After approved-only B12 generation: **144 unchanged + 80 new = 224** images.
- Protected hashes were compared against the starting HEAD manifest as well as the files; zero mismatches.

## Approved behavior and evidence

All references below are to immutable approved Git objects, read without checkout.

- `index.html:100`: fixed overlay; right panel, width `min(470px,100%)`, full height, white background, shadow. Backdrop rgba(0,0,0,.46), blur 4px.
- `index.html:104`: head/close/body/list/quantity/remove/upsell/summary/footer rules. Body scrolls internally; the head and checkout region sit outside it.
- `index.html:253`: 68px cart media, sprite/image handling.
- `index.html:687`: exact empty copy, upsell section, receiving-mode labels, totals and checkout copy.
- `index.html:889`: three demo upsells (soy sauce, ginger, wasabi), 20 RUB each.
- `index.html:959`: selected option/variation becomes a distinct cart identity and a suffix in the line title.
- `index.html:982`: minus-to-zero removes; plus increases; explicit remove deletes a line.
- `index.html:995`: unit price displayed per line; subtotal/total sum quantities; empty content reappears after final removal. Upsells, summary and checkout region remain present when empty. Empty checkout does not proceed.
- `index.html:1025`, `1029`, `1415`: cart triggers, body lock, X/backdrop/Escape closure. On full-width mobile there is no exposed backdrop to click.
- `client-fixes.html:24`: final soft surface token `#f3f4f5`.
- `client-fixes.html:325`, `381`: selector label and pending-selection handoff to the canonical approved cart.
- `demo.html`: outer approved layer remains part of the rendering chain; its header/mobile totals are B13, not implemented here.

Approved focus behavior is strengthened using the existing B9/B10 pattern: inert background,
keyboard focus trap, opener focus return and exact page scroll/overflow restoration.
Opening a drawer closes an active product selector/detail; opening a product panel closes
the drawer. No stale B9/B10 overlay or lock remains.

## Implementation

- `class-rollsbar-cart-actions.php`: extends the existing B11 snapshot with server-derived
  lines, actual cart-item keys, parent/variation identities, persisted option labels,
  unit prices, native subtotal and native upsells. Keyed plus/minus/remove share the
  same Woo mutation endpoint, update validation and stock/sold-individually checks.
- `class-rollsbar-catalog-importer.php`: separate native hidden-upsell provisioning
  through `WC_Product_Simple`, Woo CRUD and the existing `sku_for` identity convention.
- `template-parts/cart-drawer.php`, `footer.php`, scoped drawer CSS: approved panel,
  empty/list/upsell/summary/checkout structure and responsive geometry.
- `assets/js/app.js`: renders only server results, serializes requests, synchronizes
  B11 counters and duplicate Catalog/Hits cards, reconciles lost responses without
  retrying an add, preserves keyboard focus and body lock/scroll state.
- `front-page.php`: explicit exclusion of `_rollsbar_upsell_only=yes` from the main
  custom catalog, even if an administrator later assigns a main category.
- `qa/visual`: narrow adapter/session/provisioning extension, 80 approved-only images,
  additional browser tests, PHP contract, manifest provenance and documentation.

The existing mobile cart control is accessible with an empty cart below 900px because
the accepted header control is hidden there. No new total, quantity badge design,
or B13 header/mobile presentation was added.

## Three hidden native Woo products

Local/development command: `wp rollsbar catalog upsells` (`--dry-run` supported).
It provisions `Соевый соус`, `Имбирь`, `Васаби` with persistent source IDs
`upsell-soy-sauce`, `upsell-ginger`, `upsell-wasabi`. These are separate products,
not demo `u-*` IDs, not numeric Woo ID constants and not JS-only products.

Catalog visibility is **Hidden**; `_rollsbar_upsell_only=yes` keeps them outside the
canonical catalog. The main JSON remains **118 unique products / 126 DOM cards**
including the eight Hits representations. The three extras are outside those 118.

Repeat provisioning preserves existing admin edits to price, title, image and stock,
and fails on SKU identity conflicts. The drawer reads current Woo product fields.
Uploaded Woo images retain priority in the existing image resolver.

**20 RUB is provisional from the approved demo for B12/local testing only, not a
client-confirmed business price. Client confirmation is required before production.**
Each seed records this provenance. Provisioning rejects non-local/development
environments; it is not automatic on plugin activation or page loads.

The actual provisioning method was executed against the local deterministic Woo
CRUD adapter. No real WordPress database was created or modified; this is not a
live Woo database verification. Staging and production were not accessed.

## Functional and visual QA

- B11 PHP regression: **133 assertions**, PASS.
- B12 PHP contract: **812 assertions**, PASS; 118 main products, 3 hidden upsells,
  13 variable parents / 26 variations, all 6 WOK products / 18 choices, shrimp / 3
  choices; 148 line paths, keyed mutation isolation, separate incompatible lines,
  stock/validation rejection, subtotal/empty state, provisioning idempotence and
  preservation of administrator edits.
- Browser scenarios at 1440/320: simple add, keyed +/-/zero/remove, all corresponding
  card counters including Hits, two distinct native variations, two incompatible WOK
  choices, shrimp metadata, missing-image confinement, all three upsells, totals,
  persisted receiving preview, long internal scroll, lost-response reconciliation,
  recovery, selector/drawer coordination, empty final transition and checkout navigation.
- Geometry, keyboard open/close/trap, focus and page-scroll restoration at all widths.
- Matrix: **1440 / 1051 / 1050 / 1024 / 701 / 700 / 390 / 320**, height 900, DPR 1.
- 80 new screenshots: ten states at each width (empty, simple, quantity, selected
  pizza variation, WOK option, multiple option lines, pickup preview, upsell, long
  top and long bottom). Only immutable approved source generated expected pixels.
- No new masks or B12 pixel allowances. Existing global policy/B9/B10/B11 exceptions
  are unchanged. Normal mode forces snapshot updates off.
- PHP lint and JS/Node syntax checks PASS. `git diff --check` PASS.
- Additional `node qa/visual/b12-overflow.mjs` PASS: a real server-backed 15-line
  cart at every width has **0px page / drawer / content / card-action / selector
  horizontal overflow**, internal vertical scrolling present, JS errors zero.
- Full gate's application JS errors/warnings: **0**; B1–B11 regression PASS.

Approved shrimp choices are pending, so no approved confirmed-shrimp screenshot
exists to generate. Its canonical confirmed choices are verified functionally.
Approved nuggets' absolute fallback covers the whole drawer; pizza is the visual
variation representative. Current fallback remains confined to its media, rather
than copying that approved defect. These are explicit coverage boundaries, not
pixel tolerances or source modifications.

## Preservation and deferred scope

- B6B remains OPEN / DEFERRED; no footer/action-row parity refactor.
- B13/B14/B15/B16 not started. Existing B7 media exceptions unchanged.
- Main product prices, stock, SKUs, variation definitions and canonical options unchanged.
- Receiving-mode buttons retain the approved indicative labels in Woo session only;
  native checkout owns fulfillment/rates. No shipping rules or pickup discount logic added.
- Live backend prices/availability remain **NOT LIVE-VERIFIED**.
- No staging/production changes, push, deploy, merge or rebase. AGENTS and skills untouched.
- Exactly one local B12 commit follows this full acceptance; its resulting SHA
  and final clean-tree verification are recorded in the completion message.

Remaining before production: client confirmation of the three provisional prices,
then ordinary environment-specific Woo provisioning/verification outside this local batch.

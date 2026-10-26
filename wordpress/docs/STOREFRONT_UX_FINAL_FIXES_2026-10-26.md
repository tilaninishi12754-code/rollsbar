# Storefront UX final fixes — 2026-10-26

Status: **PASS** on staging. Production access/mutation: **no**. Checkout Final Direct Port was not started; checkout visuals and business data were not changed.

## Release

- Branch: `wordpress/checkout-visual-parity-2026-10-25`.
- Main implementation: `2ad7e69c690b21bb33ff48c6c92119b01ea8a218`.
- Final application SHA and verified deployed marker: `328cb664d1d6e6a63b300e6788a984497fa1320d` (701–900 px back-to-top clearance).
- Full staging run: https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40296055375 — PASS; verified backup `20261026T085936Z`.
- Final focused staging run: https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40318179335 — PASS; fresh verified backup `20261026T115225Z`; final phase `browser_verified`, `UX_RELEASE_PASS`.
- Backup database/uploads archives and manifest checksums passed before mutation. Release guards verified the final change was exactly the appended CSS rule; other application files retained their accepted hashes. Full browser acceptance was inherited from the main implementation, without repeating passed suites.
- This report is a subsequent documentation-only commit; application marker intentionally remains the SHA above. Final Git HEAD is the commit containing this report, normally pushed to the same branch; final hash/tree verification is recorded in the delivery message.

## Outcomes

- Simple, variable pizza and option-product details allow quantity selection, default/minimum 1. Server validates an integer quantity and invokes native Woo validation/add once with that quantity.
- Pizza counters reflect the server cart. A single size changes the exact line/variation; multiple sizes show a total and open the selector without choosing an arbitrary line. Existing simple-product and cart-drawer behavior passed regression checks.
- Search uses AND matching across normalized name/category/description, with name priority. Passed: `пицца цезарь`, `цезарь пицца`, `пицца четыре сыра`, `четыре сыра`, `ролл филадельфия`, `филадельфия`, mixed case/extra spaces and ё/е. The existing product name `4 сыра Чеддер` is handled without changing catalog data.
- Approved phone link `tel:+79786882288` and back-to-top after 650 px are restored. Fixed controls clear the mobile cart at tested widths, including the corrected 701/900 boundaries. Floating controls naturally overlay scrolling catalog content.
- Header evidence showed a stale 66 px category offset versus measured 67 px header. Mobile header now anchors at viewport top with a measured spacer/category offset and ResizeObserver; no unexplained negative offset. Scroll/modal cycles passed. The original physical iOS Safari browser-chrome gap was not reproduced, so its device-specific root cause is not claimed as proven; physical Safari remains an explicit verification limitation.

## Verification retained from completed work

- PHP: cart 133, B12 870, storefront 158 assertions; media contract and deployment tests PASS. Syntax checks PASS.
- Local UX: Chromium + WebKit, five viewports each — 10 PASS. Historical visual regression: 157 initially passed, nine corrected failures passed targeted rerun, 18 explicit skips; 166 accepted tests total. B16 assembled checks: eight widths PASS.
- Intentional quantity-panel changes use quantity/overflow contracts in place of the old full-panel screenshot. Reviewed 320 px native-selector antialias exception: 34 pixels; baseline PNGs and global tolerances unchanged.
- Full live Woo browser acceptance: 1440×900, 390×844, 390×900, 430×932, 320×568 — PASS, including native cart/session, quantity, exact pizza lines, multi-size handling, search, header and controls; no orders created. Final focused live checks at 701×900 and 900×900 passed empty/populated cart, drawer, back-to-top and overflow assertions.
- Client Media Canon `client-media-2026-10-21`: 45 mapped products, 36 canonical assets preserved; live asset hashes checked. Охотничья / Салями remain deferred.
- Catalog unchanged: 118 canonical, 13 variable parents, 26 variations, three hidden upsells, 121 published product posts. Business-data digest unchanged: `f6739d6e2f493ddf8a258eb2a51c6bda0ed7ef20a59e16935f260b2ba8d46d8f`.

## Evidence and visual inspection

Local evidence under `qa/visual-results/`:

- `storefront-ux/`: local browser acceptance and regression-first/followup JSON.
- `storefront-ux-staging-full/`: apply/finalize logs, catalog/media/browser JSON, 15 screenshots. Visually inspected desktop quantity, 320 quantity/search, 390×844 controls, 390×900 quantity and 430 controls. Real canonical media appears in product detail/search; unmapped catalog items retain existing placeholders. The 320 detail screenshot is scrolled within its panel, with quantity and add action visible.
- `storefront-ux-staging-controls/`: final apply/finalize logs and browser JSON, four screenshots; all four inspected. Back-to-top is above the fixed cart on both widths and cart states.
- GitHub artifacts: `12639040997` (full), SHA-256 `da77ecd945ab47500df13ed39ec8568e90cf64b33774d9bdbba534a53656c753`; `12647314326` (focused), SHA-256 `ab07eec0e9d1a830509dbb8dfa80f46354a6d48ade0d5ae36f9f9f15088c04ea`. Download checksums verified.

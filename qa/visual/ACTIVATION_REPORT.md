# Playwright Visual Gate — activation PASS

Date: 2026-10-22 (Europe/Moscow). This is the infrastructure batch between
accepted B10 and future B11. No prior worker-chat memory was used.

## Source of truth / preflight

- First Git command: `git rev-parse --show-toplevel`.
- Physical root: `C:/AI/Rolls Bar Project` — PASS.
- Branch: `wordpress/visual-parity-2026-10-14` — PASS.
- Starting HEAD: `7aa7ca183b02691a569d0a5b166446e2e978f909` — PASS.
- Initially staged, unstaged and untracked: empty — CLEAN.
- Approved ref: `refs/remotes/origin/approved/site-2026-10-01`.
- Approved SHA: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61` — PASS.
- Authority: actual Git state, targeted source reads, approved local archive,
  baseline-manifest hashes and local native Playwright reports.

## Targeted discovery

Root package files were absent. Existing `qa/package.json`,
`qa/playwright.config.mjs` and `qa/tests/store.spec.mjs` were found. The existing
suite targets an external WP base URL and includes cart scenarios, so it remains
unchanged. Existing Playwright dependency declaration was reused. No reusable
local PHP/approved preview helper was found in the targeted qa/wordpress-tools
inventory. No full Project No Loss/history reconstruction was read.

New test-only helpers: `preview.php` executes unchanged theme templates with a
fixed catalog adapter; `server.mjs` serves current/immutable approved locally;
`run.mjs` separates baseline generation from normal verification. No application
HTML, PHP, CSS, JS, catalog data or business behavior was changed.

## Installation / architecture

- Playwright 1.64.1; local `qa/node_modules/@playwright/test`.
- Chromium 156.0.8078.4, revision 1248; executable successfully launched.
- Node 24.19.0; PHP 8.5.12 NTS x64, official archive SHA256 verified.
- Root `package.json`: two command aliases. Existing qa configuration retained.
- `qa/pnpm-lock.yaml`: reproducible dependency resolution.
- Config/tests: `qa/visual/playwright.config.mjs`, `gate.spec.mjs`.
- Baselines: 96 PNGs in `qa/visual/baselines/w<width>/`, with SHA256 provenance
  in `baseline-manifest.json`. Total PNG size approximately 3.3 MB.
- Normal: `npm run visual-test` (equivalent executed locally:
  `node qa/visual/run.mjs test`). No baseline rewriting; exit 0/non-zero.
- Explicit baseline: `npm run visual-baseline` (equivalent:
  `node qa/visual/run.mjs baseline`).

Approved rendering uses `git archive` of the literal immutable SHA into an OS
temporary directory, then `demo.html → client-fixes.html → index.html` through
their real iframe chain. Normal cleanup deletes only this temporary extraction.
No checkout, ref/index update, reset, merge, rebase, push or deploy is involved.
Baseline mode disables the current homepage route. Current uses the actual
working-tree theme templates, app CSS/JS, catalog fixture and packaged assets.
The read-only WP/Woo adapter has synthetic IDs and fixed availability/cart state;
live prices/availability remain NOT LIVE-VERIFIED.

## Determinism and coverage

Fixed viewport height 900, DPR 1, widths below; same headless Chromium/runtime,
ru-RU, Europe/Moscow, light color scheme. Animations, transitions and smooth
scroll are disabled; fonts/eager images and stable layout are awaited. Pointer
and accidental focus are neutralized. Technical-cookie notice is pre-acknowledged;
remote maps/product requests are aborted in both sources. All selected media
comes from embedded/local assets or intentional source-empty-image fallback.
Component-origin alignment, modal-backdrop normalization and narrow exceptions
are documented in README and `accepted-exceptions.json`.

| Width | Tests | Screenshot assertions | Positive | Final |
|---:|---:|---:|:---:|:---:|
|1440|10|12|PASS|PASS|
|1051|10|12|PASS|PASS|
|1050|10|12|PASS|PASS|
|1024|10|12|PASS|PASS|
|701|10|12|PASS|PASS|
|700|10|12|PASS|PASS|
|390|10|12|PASS|PASS|
|320|10|12|PASS|PASS|

Targets: header, categories, promo, catalog heading, upper card shell, ordinary
media/title (`rolls-filadelfiya-s-krevetkoy`), variable media/title and selector
heading/choices (`snacks-naggetsy`), B9 details panel (`tyahan-chicken`). Desktop
and mobile states open the same canonical product and initial selection.

## Accepted exceptions and precise limits

- Global allowance is **0 pixels**. No dimension mismatch is allowed.
- Details, all widths: **20 pixels** for accepted subpixel component/control
  rasterization; measured ordinary desktop deltas were 14–17 pixels.
- Selector heading, all widths: **1 pixel**, measured native close glyph.
- Selector choices: 34 pixels at 1440/1050/1024/700/390, 22 at 1051/701,
  **0 at 320**; native Woo price-label rasterization. Exact normalized labels,
  quantities, prices and selected index are separately required in both sources.
- Media/title targets: capture origin only is aligned by at most half a CSS
  pixel in both sources; no size/internal-layout modification or pixel allowance.
- Modal component positions/backdrops are excluded, accommodating accepted
  scroll-lock/focus/inert differences. Only backdrop color/blur is normalized.
- Selector CTA is outside snapshots and asserted disabled in current B10.
- Product footer/actions remain outside captures: deferred B6B, native B8
  pricing, B11-owned 320px action overflow are preserved.
- The three known B7 media exceptions and B9 broken-image/long-word cases are
  outside these representative targets; they are not declared fixed or covered.

## Positive / negative / final proof

Positive normal run: **80 passed, 0 failed, 96 screenshot assertions**, exit 0,
38.1 seconds. Archived JSON: `qa/visual-results/proofs/positive-results.json`.

Negative proof: temporary Playwright-only `background:#00ff00!important` on the
current header. Native screenshot assertion failed in **all 8 viewports**, exit
1, 10.0 seconds. Differing pixel counts: 1440=94536; 1051=63808; 1050=63726;
1024=61672; 701=46094; 700=41559; 390=20789; 320=16625.

Representative evidence under
`qa/visual-results/negative/results/gate-header-w1440/`:

- expected: `header-expected.png`
- actual: `header-actual.png`
- diff: `header-diff.png`
- trace: `trace.zip`
- report: `qa/visual-results/negative/report/index.html`
- JSON: `qa/visual-results/negative/results.json`

The injected mutation and temporary negative execution mode were **removed**
before final verification. They are not committed. Source scan confirms no
negative-mode/injected-green code in the delivered helpers/tests.

Final normal run after removal and viewport-specific choice caps:
**80 passed, 0 failed, 96 screenshot assertions**, exit 0, 38.4 seconds.
Report: `qa/visual-results/normal/report/index.html`.
JSON: `qa/visual-results/normal/results.json`. Logs: `positive.log`,
`negative.log`, `final.log` under `qa/visual-results/`.
All baseline hashes remained valid. Runtime artifacts are intentionally ignored.
No manual model review of successful screenshots was required.

## Preservation / result / next

Application behavior changed: NO. B10 acceptance preserved. B11 started: NO.
B6B closed: NO. Staging/production touched: NO. Push/deploy/merge/rebase: NO.
Only test infrastructure, package aliases/lock, approved baselines, ignore rules
and infrastructure documentation are included. Final full staged diff must be
reviewed before the single authorized local infrastructure commit. Its SHA and
final CLEAN status are supplied in the Coordinator handoff response.

Return this report to Coordinator. Do not start B11 automatically.

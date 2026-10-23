# I1-E / Integration I1 — PASS acceptance

Local integration only; no production-readiness claim. This report accompanies
the local two-parent merge. Its SHA/parents are available from git log on the
integration branch; final commit verification is also saved in ignored I1-E evidence.

## Preflight and continuity

First Git command: `git rev-parse --show-toplevel`.
Root: `C:/AI/Rolls Bar Project`; branch: `wordpress/integration-2026-10-23`.
Starting HEAD / migration parent / origin/wordpress/migration-2026-10-01:
`421d3db121e8fa3fcbb3f2fa06751858821de674`.
Starting MERGE_HEAD / Visual parent / wordpress/visual-parity-2026-10-14:
`5e7836e22110ec076603bb1fa2b12f8bb90ee756`.
Approved refs/remotes/origin/approved/site-2026-10-01:
`a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Expected active merge, no textual conflicts, rebase or cherry-pick.

I1-D state matched: 342 staged paths; one substantive accepted Delivery workflow
correction; three historical JSON status flags with empty diffs; existing untracked
I1 report. All 520 tracked raw hashes matched I1-D. No unexplained changes.
Source refs remained unchanged before finalization.

## Baseline environment and actual font preflight

I1-D PASS established **ENVIRONMENT/HARNESS DRIFT PROVEN**: the same Chromium
binary selects Segoe UI in Codex Windows sandbox and Inter in host-user context.
I1-D reproduced 60/60 byte-identical approved captures, 285/285 hashes and
pixel-identical Visual/Integration representative states under Segoe UI.
The root-cause investigation was not reopened.

Canonical command: `npm run visual-test`, or `node qa/visual/run.mjs test` when
npm is unavailable, from repository root in the existing Codex Windows sandbox
(`exec_command`, `sandbox_permissions: use_default`). This reuses I1-D's successful
execution context. No font configuration, application presentation or browser
stack is substituted. An incompatible context fails before screenshot workers.
README documents the profile and environment-only diagnosis.

Actual normal font: **Segoe UI / SegoeUI**, weight 400.
Actual price font: **Segoe UI / SegoeUI-Bold**, weight 700.
Computed stack: `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif`.
Playwright **1.64.1**; Chromium **156.0.8078.4**, revision **1248**; Node **24.22.1**.
Widths **1440,1051,1050,1024,701,700,390,320**, height **900**, DPR **1**.
No dependency/browser/font installation or upgrade.

## Implementation

- `qa/visual/environment.mjs`: CDP CSS.getPlatformFontsForNode reads rendered
  footer paragraph and price bdi. Missing/empty/incompatible samples, wrong weights
  or runtime drift fail closed. Compact startup fingerprint plus ignored JSON.
  No injected presentation CSS or replacement text.
- `qa/visual/playwright.config.mjs`: global setup guards even direct CLI execution
  before workers and screenshot comparisons.
- `qa/visual/run.mjs`: environment-only preflight path; normal interface preserved.
  Normal test mode still forces snapshot updates off and rejects CLI overrides.
- `qa/visual/README.md`: repeatable profile and separate Inter robustness record.
- `qa/visual/I1_REPORT.md`: this report.

The accepted `.github/workflows/wordpress-migration-static-gate.yml` Delivery
assertion correction remains byte-identical to I1-D. Additional application changes:
**NONE**. Baseline/manifest/exception/tolerance/mask changes: **NONE**.

## Negative proof

`node qa/visual/run.mjs preflight` in known host-user/escalated context detected
**Inter / Inter-Regular**, returned **exit 1**, and stopped during environment
verification. No screenshot suite ran; protected files remained unchanged.
Diagnostic directs the worker to the canonical sandbox profile. Host fonts unchanged.

## Positive proof

One full canonical `node qa/visual/run.mjs test`, exit 0:
**166 passed /18 skipped /0 failed /0 flaky**, Chromium duration 328.828 seconds.
Global setup reported Segoe UI/SegoeUI and Segoe UI/SegoeUI-Bold before workers.
Normal runner's B16 assembled follow-up: **8/8 PASS**.
Protected hashes: **285/285**, no baseline regeneration.
Full run w390 B6B geometry attachment: integration counter footer-relative
**y=3.5**. No B6B CSS edit. Historical B16_ASSEMBLED JSON restored byte-for-byte
with current evidence saved separately.

## Inter robustness record

I1-D reproduced B6B390 under Inter on both accepted Visual HEAD and Integration,
both y=46. Segoe UI needs 138.5625px within the 143.5px footer; Inter needs
144.578125px and triggers existing populated-footer wrapping. Classification:
**pre-existing environment-triggered wrapping**, not an integration regression or
stale assertion. Separate frontend robustness follow-up retained; no application
edit, baseline exception, or additional launch blocker introduced.

## Previous I1 evidence

Still valid: canonical 118/126/8; 13/26; WOK 6/18; shrimp 3; B11 133; B12 812;
B15 22; PHP lint 39; JS 15; additional PHP contracts 36; assembled 8/8;
dense responsive 69/69; Firefox 8/8; WebKit 8/8; application JS errors/warnings 0;
backend preservation; static/package/deploy-script checks.
No shared helper/application/contract implementation changed; no independent prior
suite invalidated. Chromium and normal runner's assembled follow-up ran as above.

## Final adversarial reconciliation

All 119 WordPress files are byte-identical to I1-D's candidate. No parent file
missing; migration-unique changes preserved; both parents' core includes and
initializers occur exactly once. Against accepted Visual, WordPress differences
are only migration's two source-of-truth documents, SMTP implementation and core
loader/version union. No unresolved integration defect found.

Migration checkout, Woo Blocks, Local Pickup, DaData, reviews, admin, order workflow,
notifications/SMTP, security, backups/recovery, deploy, SEO and legal/payment preserved.
Visual B1–B16, Header/Categories/Promo, catalog/Hits, cards, Details, selectors,
counters, Cart Drawer/totals, Search, Delivery, Contacts/Footer, responsive and
accessibility protections preserved.

Source of truth: MAX future/pending; staging e-mail E2E READY; delivery ambiguity
unresolved/fail-closed; courier enforcement OFF; acquiring/Metrica deferred;
payment `Оплата при получении`; WooCommerce 11.1.2.

## Evidence, boundaries and deferred work

Ignored evidence under `../visual-results/i1-e/`: negative-environment.json,
positive-environment.json, full-verification.log, chromium-results.json, b6b390.json,
B16_ASSEMBLED.json, reconciliation.json and final-git.json.
I1-D: `../visual-results/i1-d/I1-D_REPORT.md` and controlled captures.
Earlier I1: `../visual-results/i1/summary.json`, parent-audit.json and static,
backend and Delivery-negative logs. Prior BLOCKED report preserved as
`../visual-results/i1-e/I1_REPORT.before.md`; its unknown cause/Chromium blocker
are superseded by I1-D and I1-E evidence above.

Push NO; staging touched NO; staging DB touched NO; production touched NO;
secrets changed NO; notifications sent NO; global Git identity/config changes NO.

Deferred: Inter-specific B6B390 robustness; provisional upsell business values;
live Woo price/stock/provisioning; MAX; delivery-rule ambiguity; acquiring;
analytics; staging route/runtime proof; remaining external launch inputs.

Next: return report to Coordinator. Staging work is a separate batch.

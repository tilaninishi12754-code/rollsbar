# CHECKOUT PARITY V2 — REMOTE AUTOPILOT

STATUS: PASS — candidate verified without deployment. Ready for Coordinator
review and a separate backup-gated deployment. This report does not claim that
the candidate is deployed.

## Preflight and source truth

First Git command: `git rev-parse --show-toplevel` returned
`C:/AI/Rolls Bar Project`. Branch:
`wordpress/checkout-visual-parity-2026-10-25`. Initial tree CLEAN.
Starting HEAD: `8273df1835346be6d852fd212e1876321ea6bd77`.

| Source | Exact SHA |
| --- | --- |
| Approved site | a5e524392abcf89ffd5ace2a18218a6b59ed3b61 |
| Immutable checkout visual | 5e7836e22110ec076603bb1fa2b12f8bb90ee756 |
| Accepted V1 | 5c5310070ef43d31b58d4e3c5973f0e1242ff52e |
| Initial feature HEAD | 8273df1835346be6d852fd212e1876321ea6bd77 |
| Deployed application marker, verified before/after every remote run | 88826907fc7ffe805a7c47f36c35a74c0049e08e |
| Final browser-tested commit | ac0e6e8e774b89f41f82119e5f7af14e0d973d09 |

The previous local `net::ERR_NETWORK_ACCESS_DENIED` is an environment limitation.
No local staging-browser attempt was repeated. Local browser tests fulfill
requests offline; immutable reference capture serves a local Git source.

## Remote route and workflow safety

Extended the existing dispatch-only `.github/workflows/gate-b-browser.yml`.
Normal Gate B stays intact. Only this feature ref gets the existing checkout
shadow preview and artifact upload. Both local CSS and JS response substitutions
are recorded with URL, byte count and SHA-256. Their final hashes were separately
compared to `git show <tested-commit>:<asset>` bytes and matched.

The existing read-only marker helper accepts a full, validated lowercase SHA
override. The feature workflow expects exact `88826907...`; its default and
normal historical verification remain unchanged. The reader executes only
`cat`, `printf` and `test` for this feature; no WordPress/config/catalog writes.

All 38 workflow files are `.yml` and parsed successfully by the existing audit.
Every automatic push trigger is limited to `wordpress/migration-2026-10-01`.
No feature push matches; no indirect workflow-run/call/scheduled triggers.
Only normal fast-forward pushes to the authorized feature ref were performed.
Only `gate-b-browser.yml` was dispatched. Deploy triggered=no.

One baseline dependency download took 7m54s for 25.9 MB from the Ubuntu mirror;
Python packages took about 7s. The log showed Chromium runtime libraries and
Liberation fonts already installed. Subsequent feature runs install Chromium
without reinstalling OS dependencies; startup, Gate B and shadow preview all
passed. Other refs retain the existing `--with-deps` setup.

## Remote runs

| Run | Commit | Gate B | Shadow | Diagnosis / next action |
| --- | --- | --- | --- | --- |
| [40209955619](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40209955619) | 3482b8684f1a54e29e7630d4138e2e9f9cdf7bf7 | PASS | PASS | Fresh V1 baseline and harness proof before product edits |
| [40211406235](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40211406235) | 2ee0682b28a3a1b83481b13773b96f93d1dcec9d | PASS | FAIL | QA HARNESS: new stale-response check assumed interception within 100ms; replaced with request observation and bounded route-event wait |
| [40211810131](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40211810131) | b6bb671dd7f7c94d3e9b08ef32b962cc5466645e | PASS | FAIL | QA HARNESS: at 320px native city label intercepted input-centre trial click; retained pointer check through associated visible native label, with focused offline label/focus regression |
| [40212863929](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40212863929) | ca4e2cfac9b1d392baa5f672cd18f4000a48d6f3 | PASS | PASS | All widths/functionality passed; visual review found redundant mobile summary outline and identified its runtime class |
| [40213777631](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40213777631) | ac0e6e8e774b89f41f82119e5f7af14e0d973d09 | PASS | PASS | Final outline fix verified; screenshots reviewed |

Every run recorded exact marker `88826907fc7ffe805a7c47f36c35a74c0049e08e`
BEFORE and AFTER. Every live context completed accepted finally cleanup with a
fresh cart GET: HTTP 200, `items_count=0`, `items=[]`. Gate B's desktop/mobile
contexts each removed 2 items; each shadow context removed 1 known simple item.
No failure was hidden, no assertion deleted, no failed implementation rerun
unchanged, no masks/tolerances/approved baselines changed.

Baseline artifact: `checkout-shadow-40209955619-1`, ID `12605826185`.
Final artifact: `checkout-shadow-40213777631-1`, ID `12606029375`.
Artifacts contain evidence JSON, screenshots, native HTML and shadow log;
generated evidence is ignored, never committed.

## Baseline findings and product implementation

Read the V1 report, architecture, CSS/JS/PHP and existing QA first. Recovered
immutable visual source through `reference_capture.py`, not from the candidate.
Reference: white 1040px sheet, 22px padding, 28px radius, 18px gap, 360px summary,
19px summary radius, 14px fields, 30px heading, #d92525 action, pronounced shadow,
230px desktop / 210px mobile map. The reference's older 1050px one-column rule
remains adapted to the explicitly accepted/requested 701/700 transition.

Product changes are CSS only:

- Remove the checkout header/back-link row duplication. Keep the existing real
  menu-return anchor as a 44px close-style target, with its accessible text and
  URL unchanged. The route stays native; no transaction modal is added.
- Align the desktop sheet at 40px, maintain its width/padding/radius/shadow,
  and give mobile the reference-like 12px outside margin and 22px inset.
- Remove the redundant nested billing border/inset; use quieter step headings,
  readable 14px floating labels and a rounded native country selector.
- At 480–700px use paired native address/additional fields where room permits;
  keep single-column fields on narrow phones and in the narrow 701px main lane.
- Refine native payment surface and summary spacing. Remove the observed
  `.checkout-order-summary-block-fill` border inside the mobile grey summary.
- Preserve existing summary/CTA/map dimensions and native action placement.

No checkout JS or application PHP change. No cloned/moved/removed inputs,
fake controls, custom submission, duplicate pickup or payment implementation.

## Final visual measurements

Measurements are CSS pixels from final `evidence.json`; sheet heights rounded.
Each row has exactly one visible native summary, all 8 required controls
reachable through their native input or associated label, `willValidate=true`,
and the native CTA trial-clickable with successful centre hit-test.

| Width | Sheet W × H | Form / summary columns | Overflow page/sheet/form/summary/map | CTA | Result |
| --- | --- | --- | --- | --- | --- |
| 1440 | 1040 × 1604 | 618 / 360 | 0 / 0 / 0 / 0 / 0 | reachable, unobscured | PASS |
| 1024 | 1000 × 1604 | 578 / 360 | 0 / 0 / 0 / 0 / 0 | reachable, unobscured | PASS |
| 701 | 677 × 1988 | 355 / 260 | 0 / 0 / 0 / 0 / 0 | reachable, unobscured | PASS |
| 700 | 676 × 1959 | 632, one column | 0 / 0 / 0 / 0 / 0 | reachable, unobscured | PASS |
| 390 | 366 × 2413 | 322, one column | 0 / 0 / 0 / 0 / 0 | reachable, unobscured | PASS |
| 320 | 296 × 2567 | 252, one column | 0 / 0 / 0 / 0 / 0 | reachable, unobscured | PASS |

Fresh baseline sheet heights: about 1710 / 1710 / 2087 / 2386 / 2495 / 2592px.
At 700px the form/sheet is about 427px shorter. Desktop sheet starts at 40px
instead of 109px; its first content lane starts at 124px instead of 240px.
These height comparisons include live native content states, not pixel baselines.
Visible suggestion panels at 1440/700/390/320 also have zero measured overflow.
Map iframe height remains 230px desktop / 210px mobile, excluding its note.

## Woo and address safety

Final before/after snapshot comparison preserves all 18 native inputs/selects
with identical IDs (generated checkbox serial normalized), types, requiredness
and visibility. Eight required inputs remain reachable at every width; empty
required inputs retain `validity.valueMissing`, including privacy consent.

Checkout Block and Store API remain authoritative. Gate B observes the exact
native cart product/line through Store API. Additional Checkout Fields registry,
required privacy, legal/terms markup and server validation code are unchanged.
No checkout endpoint was submitted to test server rejection, because submissions
are prohibited; browser validation plus unchanged PHP contracts are the evidence.

Native `pickup_location:0` and COD remain selected; no manual zone selector.
Phone preparation `+7 ` and leading `8` -> `+7 ` pass using unchanged JS.
Live exact DaData result supplies the map coordinates, compared directly to the
iframe URL; low precision warns, auto-zone=false, no customer point. An actual
live resolve delivered after an edit cannot restore the old address/marker.
Offline tests additionally cover stale suggestions ignoring AbortSignal, delayed
resolve, qc_geo 1–5/missing and malformed exact coordinates. Customer suggestion
text excludes country/provider geography labels.

Courier enforcement stays OFF. No delivery polygons/prices/thresholds invented.
Map remains display/address feedback. No acquiring enabled. Final page errors=0;
checkout submission requests=0; orders created=0; notification actions=0.

## Local regression commands/results

Run from repo root in PowerShell using the existing ignored runtime:

```powershell
$env:PLAYWRIGHT_CHANNEL='chrome'
& qa/.runtime/s1-r3q/Scripts/python.exe -B -m unittest qa.checkout.test_contracts qa.checkout.test_remote_preview qa.repair.test_s1_r3q
# 25 tests, OK
& qa/.runtime/s1-r3q/Scripts/python.exe -B qa/checkout/test_contracts.py
# 9 tests, OK; direct invocation retained
& qa/.runtime/s1-r3q/Scripts/python.exe -B qa/checkout/check_static.py
# PASS JS syntax, Python syntax, PHP lint, 10 geocode cases, legal/payment
# positive + negative consent fixtures, diff check, 38-workflow audit,
# changed-file secret scan (zero findings), protected-surface scope
& qa/.runtime/s1-r3q/Scripts/python.exe -B -m unittest qa.checkout.test_asset_versions.AssetVersions.test_actual_enqueues_versions_and_unchanged_other_arguments qa.checkout.test_asset_versions.AssetVersions.test_source_no_time_random_or_semantic_version_bump qa.checkout.test_asset_versions.AssetVersions.test_checkout_business_and_theme_catalog_code_unchanged
# 3 tests, OK
```

Marker-reader Python AST also parsed successfully. The official temporary PHP
runtime was already present at `qa/.runtime/php/php.exe`; no binaries committed.
The historical asset-cache Batch's byte-preservation assertion is not an
applicable V2 requirement: checkout CSS is intentionally changed. Relevant
enqueue/hash/business contracts above were run without weakening that test.

## Screenshot review and remaining differences

Reviewed immutable reference 1440/700/320; fresh baseline top views at all six
widths, desktop full-page and 320px bottom; final full-page views at all six
widths; final 701/700/320 CTA views, 390/320 visible map crops and 320 suggestions.
Intermediate desktop/mobile evidence was also reviewed and led to the outline
fix after assertions were already green.

| Difference / result | Classification and current reason |
| --- | --- |
| Extra back row, address frame/inset, excess 700px form length, summary inset/inner outline | FIXED — CSS can improve these without changing controls |
| Email, surname, country, city/region/postcode and native optional phone status | REQUIRED_NATIVE_WOO_DIFFERENCE — configured fields/validation remain; no claim that every conceivable future supported API change is impossible |
| Phone stays in native address step; extra details/privacy remain in API order group; CTA stays at native form end | REQUIRED_NATIVE_WOO_DIFFERENCE — preserve transaction/focus order; no React reparenting or duplicate action |
| Native summary product details, coupon control, quantity/thumbnail placeholder, pickup/COD and legal text | REQUIRED_NATIVE_WOO_DIFFERENCE — retained real state/data and legal semantics, with presentation adapted |
| Route sheet, return anchor instead of modal dismissal; 701/700 transition; narrower phone labels and native text overflow within editable fields | ACCEPTABLE_RESPONSIVE_ADAPTATION — native scrolling and accessible controls retained, no page overflow |
| Native ellipsis on the long optional suffix of door-code label at 320px | ACCEPTABLE_RESPONSIVE_ADAPTATION — field purpose remains visible; native label/control semantics unchanged |
| Real map/precision feedback instead of demo zones, dragged fake point and minimums | DEFERRED_BUSINESS_DATA — polygons/thresholds remain unapproved |
| Offscreen iframe can appear blank in full-page overview | Capture/compositing limitation, not hidden/masked: separate in-viewport map screenshots show provider rendering |

No knowingly unresolved ACTUAL_DEFECT remains in the reviewed states. Live map
tiles are not a deterministic pixel baseline. Pixel identity is not claimed.

## Exact changed-file scope

- `.github/workflows/gate-b-browser.yml`
- `qa/checkout/check_static.py`
- `qa/checkout/shadow_preview.py`
- `qa/checkout/test_contracts.py`
- `qa/checkout/test_remote_preview.py`
- `qa/repair/s1_r3q_release_read.py`
- `wordpress/wp-content/plugins/rollsbar-core/assets/css/checkout.css`
- `wordpress/docs/CHECKOUT_VISUAL_PARITY_V2_REPORT.md`

Catalog, theme, homepage, variations, upsell provisioning, maintenance, B1–B16,
masks/tolerances, migration and approved refs are untouched. Existing catalog
semantics (118 main products, 13 variable parents, 26 variations, 8 Hits and 3
hidden staging upsells) are not modified; provisional upsell prices are not
promoted to production truth.

## Commit series and final delivery

| Commit | Parent | Purpose |
| --- | --- | --- |
| 3482b8684f1a54e29e7630d4138e2e9f9cdf7bf7 | 8273df1835346be6d852fd212e1876321ea6bd77 | Remote shadow workflow, marker override, evidence and focused contracts |
| 2ee0682b28a3a1b83481b13773b96f93d1dcec9d | 3482b8684f1a54e29e7630d4138e2e9f9cdf7bf7 | CSS visual refinement and stronger native/stale QA |
| b6bb671dd7f7c94d3e9b08ef32b962cc5466645e | 2ee0682b28a3a1b83481b13773b96f93d1dcec9d | Request-observed stale-response synchronization |
| ca4e2cfac9b1d392baa5f672cd18f4000a48d6f3 | b6bb671dd7f7c94d3e9b08ef32b962cc5466645e | Native-label reachability, offline focus fixture, runner setup |
| ac0e6e8e774b89f41f82119e5f7af14e0d973d09 | ca4e2cfac9b1d392baa5f672cd18f4000a48d6f3 | Remove visually observed redundant mobile outline |
| This documentation-only delivery commit | ac0e6e8e774b89f41f82119e5f7af14e0d973d09 | Record reviewed evidence; exact SHA in final Git record and delivery reply |

Post-commit `qa/visual-results/checkout-parity-v2/final-git.txt` records every
full SHA/parent, exact changed files, final local/remote HEAD equality and clean
porcelain status. Final delivery adds only this report to the browser-tested
commit; tested asset/QA bytes remain identical.

Local evidence root: `qa/visual-results/checkout-parity-v2/` (ignored).
`baseline-proxy/evidence.json`, `final/evidence.json`, each run's log and
`final-git.txt` provide reproducible measurements, marker and cleanup proof.

Staging: persistent mutation=no; deployed files unchanged; deploy=no; isolated
cart cleanup=PASS; orders=0; notification actions=0. Production: access=no,
mutation=no. Push=feature branch only; force push=no. Approved/business-data
deferrals remain for a separate Coordinator decision. Ready for review and the
separate backup-gated staging deployment, which was not executed here.

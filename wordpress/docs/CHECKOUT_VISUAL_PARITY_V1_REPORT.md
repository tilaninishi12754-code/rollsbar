# CHECKOUT VISUAL PARITY V1 STATUS

IMPLEMENTATION PASS / READY FOR SEPARATE STAGING DEPLOY.

Candidate verification only. No claim that the new presentation is deployed.
Evidence directory: `qa/visual-results/checkout-parity/` (local, ignored artifacts).
Delivery SHA, remote feature ref and final clean-tree proof are recorded after
the single implementation commit in `final-git.txt` in that directory.

## PREFLIGHT

First Git command: `git rev-parse --show-toplevel` -> `C:/AI/Rolls Bar Project`.
Initial branch `wordpress/staging-qa-s1-r3q-2026-10-24`, HEAD
`0ad375113e7383a504bb4d366e1051cfae931efa`. Initial `git status --short`,
staged/unstaged lists and untracked list were empty.

## CURRENT CANONICAL STATE

Application base `e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea`.
Integration `22ad41e3d03ec1a9efae0bde2560a4895d6e2708`.
Approved `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
Visual source `5e7836e22110ec076603bb1fa2b12f8bb90ee756`.
Coordinator supplied acceptance run `40135295179`: 42 PASS / 4 WARN / 0 FAIL.
Those four security/REST warnings are outside this Batch and were not changed.

## REMOTE VERIFICATION

The restricted-network attempt failed with a transport error. A subsequent
authorized network read, `git ls-remote origin refs/heads/wordpress/migration-2026-10-01`,
returned exact `e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea`.
A later fresh read also confirmed integration `22ad41e3...` and no existing
feature branch. No stale remote-tracking ref was used as fresh evidence.

## CORRECTED S1-R3Q QA PROVENANCE

`git show -s --format='%H%n%P%n%s' 0ad3751...` confirmed the exact parent
`e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea` and message
`Harden staging browser acceptance harness`.
`git diff-tree --no-commit-id --name-status -r 0ad3751...` confirmed exactly:

```
M .github/workflows/address-checkout-browser-smoke.yml
M .github/workflows/gate-b-browser.yml
A qa/repair/s1_r3q_release_read.py
A qa/repair/test_s1_r3q.py
M wordpress/deploy/gate_b_browser.py
```

No application changes in that QA commit. All five files remain untouched here.

## FEATURE BRANCH

`wordpress/checkout-visual-parity-2026-10-25` created directly from exact
`0ad375113e7383a504bb4d366e1051cfae931efa`. No merge or cherry-pick.
Topology: canonical application -> accepted QA -> one implementation commit.

## REFERENCE VISUAL RECOVERY

Read immutable `5e7836e...:index.html` using `git show`. Recovered: white 1040px
surface, 22px padding, 28px radius, 18px column gap, 360px summary, 19px summary
radius, 14px field radius, 30px heading, #d92525 CTA, shadow
`0 40px 120px rgba(0,0,0,.32)`, 230px map / 210px mobile map, 700px sheet styles.
The source's older 1050px single-column rule is adapted to the explicitly
requested 701/700 transition.

`qa/checkout/reference_capture.py` renders that source locally without checking
out or editing it. Artifacts: `reference-b16-1440.png`, `reference-b16-700.png`,
`reference-b16-320.png`. Reference contains demo zones; no such code was copied.

## CURRENT WOO CHECKOUT ARCHITECTURE

Inspected architecture document, checkout PHP/CSS/JS, page shell and hydrated
staging DOM. Real Checkout Block, Store API, Additional Checkout Fields API,
native pickup and COD remain authoritative. `native.html` and
`native-1440.png` record the initial runtime. No PHP or theme file changed.

## IMPLEMENTATION STRATEGY

Checkout-only CSS uses stable Woo selectors, with an additional checkout body
scope excluding order-received. Existing `is_checkout()` enqueue is unchanged.
Narrow JS adds a heading and one display-only map per address section; no
native input is cloned, moved or removed. Responsive summary copies already
rendered by Woo are selected with CSS at the requested breakpoint, avoiding
the duplicate summary observed in the first 701px candidate.

## CHANGED APPLICATION FILES

- `wordpress/wp-content/plugins/rollsbar-core/assets/css/checkout.css`
- `wordpress/wp-content/plugins/rollsbar-core/assets/js/checkout.js`

Supporting new files: `qa/checkout/shadow_preview.py`, `test_contracts.py`,
`reference_capture.py`, `check_static.py`, and this report.

## NATIVE WOO PRESERVATION

Browser comparison preserves all 18 native inputs/selects and their required /
visible status. Only Woo's generated order-note checkbox serial is normalized
across reloads; stable field IDs remain compared. Required inputs stay visible
at every tested width. Each width has exactly one visible native summary.
Native CTA is unchanged; only its style changes.

## MAP / ADDRESS UX

Reuse of the existing public Yandex business widget for DISPLAY ONLY.
Initial / approximate state shows listing OID `229692973623`, explicitly labelled
Rolls Bar, without a customer point. Exact DaData response alone supplies the
map centre and point. Live example: Гагарина, 17 -> lon `34.094496`, lat
`44.970468`, `qc_geo=0`. Browser asserts iframe coordinates equal that response.
No geocoder switch, paid dependency, polygon or minimum calculation.

Separate `*-map.png` artifacts capture the visible iframe at its actual viewport.
Full-page overview screenshots can omit offscreen third-party map compositing;
they are not used to judge map rendering. `map-detail.png` also shows the fully
rendered exact-address map. Internal and external iframe width measured 582px
at desktop, height 230px; this is not a narrow actual map container.

## DADATA SAFETY

Live exact and low-precision flows pass. Дубки, Раздерина, 12 remains a warning
with auto-zone=false and no customer marker. Typed edits clear a point; stale
resolve responses cannot restore an edited address/point. Stale suggestion
responses are rejected; a new edit hides the old list. Country/provider fields
do not leak into DaData customer display. Server policy is untouched.

## LOCAL PICKUP

Native `pickup_location:0` visible and selected in the browser. Only one method;
switching is not applicable. No courier method or second pickup system added.

## PAYMENT / LEGAL

Native COD radio selected; payment remains at receipt. Required privacy checkbox
remains required. Local legal/payment fixture passes and rejects missing or
optional consent. Acquiring/legal configuration and server validation unchanged.
Zero checkout submission requests recorded; accepted helper also blocks them.

## DESKTOP VISUAL RESULT

1440 / 1024 / 701: main form left, native summary right. See
`candidate-1440-initial.png`, `candidate-1024-checkout.png`,
`candidate-701-checkout.png` and their `-top.png` / `-map.png` companions.
Dimensions are recorded in `evidence.json:layout`; typography/radii/CTA derive
from the reference, without restoring its demo checkout.

## MOBILE VISUAL RESULT

700 / 390 / 320: one column, upper sheet corners, single native summary before
CTA, full-width fields. See corresponding `candidate-*-checkout.png`,
`candidate-*-exact-map.png` and `candidate-*-cta.png` files. Checkout-only CSS
suppresses the redundant floating cart so it cannot obscure fields or CTA.

## SHADOW PREVIEW

`qa/checkout/shadow_preview.py` uses the accepted isolated context, product-add,
bounded exact-item polling and finally cleanup. It overrides only the two asset
responses in the browser session, with CSS loaded before JS as it is normally.
No server upload, PHP-dependent approximation, DB/config write or deployment.
`shadow.log` and `evidence.json` contain the assertions and measurements.
Final fresh cart GET: HTTP 200, `items_count=0`, `items=[]`, removed=1.

## FUNCTIONAL QA

21 offline tests pass: 7 candidate UX tests plus 14 unchanged S1-R3Q regressions.
`contracts.log` records `Ran 21 tests` / `OK`. Negative fixtures intentionally
exercise cleanup HTTP errors; those are expected offline tests, not live faults.
Browser: exact product id=10 and matching AJAX/Store API key; native populated
summary; +7 preparation on focus as in accepted Gate B; 8 -> +7; required privacy;
pickup; COD; no manual zone selector; exact / low-precision paths; zero page errors;
zero checkout submissions; verified finally cleanup.

## VISUAL QA

Reference and candidate screenshots reviewed, including 701/700 and 320 CTA.
No screenshot baseline was created from the candidate. No pixel-identity claim.
Static CSS brace / browser CSSOM parsing and scope tests pass. Map iframe crops
are authoritative for provider rendering; structural overviews remain unmasked.

## OVERFLOW METRICS

`evidence.json:metrics` records 16 candidate states across six widths.

| Width | Page | Surface | Form | Visible summary | Map | CTA |
| --- | --- | --- | --- | --- | --- | --- |
| 1440 | 0px | 0px | 0px | 0px | 0px | reachable / unobscured |
| 1024 | 0px | 0px | 0px | 0px | 0px | reachable / unobscured |
| 701 | 0px | 0px | 0px | 0px | 0px | reachable / unobscured |
| 700 | 0px | 0px | 0px | 0px | 0px | reachable / unobscured |
| 390 | 0px | 0px | 0px | 0px | 0px | reachable / unobscured |
| 320 | 0px | 0px | 0px | 0px | 0px | reachable / unobscured |

Visible suggestion lists at 1440 / 700 / 390 / 320: 0px overflow.
`evidence.json:cta` records bounds and centre hit-testing at each width; trial
clicks verify pointer access without submission. All native required fields
remain visible. No floating-cart overlay remains on checkout.

## EXISTING REGRESSION PROTECTION

No changes to homepage/theme/catalog/QA provenance or B1-B16 files, masks,
tolerances and exception registry. CSS scope proven by browser parsing; enqueue
remains checkout-only. Full homepage pixel suite is therefore not required.
Runtime helper proves 118 main / 126 representations / 8 Hits / 118 search IDs.
Unchanged source catalog has 13 variable parents / 26 variations; 6 WOK entries
with 18 sauce choices; shrimp choices чесночный / сырный / томатный.
WP/Woo versions and staging noindex remain the accepted baseline; no upgrades.

## COMMIT

Exactly one new logical implementation commit, message
`Implement native Woo checkout visual parity`, parent exact `0ad3751...`.
SHA and exact seven-file list are in post-commit `final-git.txt` and delivery reply.

## PUSH SAFETY

`check_static.py` parses the unchanged workflow audit: 38 workflows, zero
feature-branch push matches. Automatic pushes are restricted to migration;
other entry points are manual dispatch. No workflow dispatch invoked. Only
the feature branch may be pushed, without force.

## REMOTE FEATURE BRANCH

Target `wordpress/checkout-visual-parity-2026-10-25`; absent in fresh pre-push
remote read. Post-push exact SHA verification is recorded in `final-git.txt`.

## CANONICAL PRESERVATION

Migration and integration fresh reads match their exact accepted SHAs.
Approved / Visual refs untouched. Deployed marker value `e0c3d4ed...` comes from
the Coordinator's fresh accepted evidence. No local hosting credentials were
available for an independent new marker read; this limitation is explicit.
No action in this Batch writes the marker or deployed assets.

## STAGING MUTATION

No deployment or persistent business/config/catalog mutation. Only the authorized
anonymous browser-session cart was changed and verified empty in finally.
No backup creation, retention change, restore, bootstrap or import.

## PRODUCTION

No access or mutation.

## ADVERSARIAL GAP

1. Checkout Block retained: yes, hydrated native DOM and unchanged PHP.
2. Store API retained: yes, exact AJAX line observed independently.
3. Duplicated native fields: no, 18-field comparison passes.
4. Unsafely hidden required fields: no; all remain visible at all widths.
5. Unsafe React reparenting: no; no native control is moved.
6. Fake customer coordinates: no; exact coordinates compared to DaData.
7. Demo polygons: none introduced; reference only.
8. Invented minimum: none.
9. Courier enforcement: remains OFF; delivery code/config untouched.
10. qc_geo fail-closed: preserved; live low precision and 10 PHP cases pass.
11. Local Pickup: native and selected.
12. Privacy: required; positive and negative contracts pass.
13. Receipt payment: selected COD.
14. Acquiring: unchanged OFF; local payment fixture passes.
15. Real submitted orders: zero; zero checkout POSTs, route also blocks them.
16. External notifications: none invoked; no order/notification action.
17. 1440: checked, overflow 0, CTA reachable.
18. 1024: checked, overflow 0, CTA reachable.
19. 701: checked, overflow 0, single summary, CTA reachable.
20. 700: checked, overflow 0, one column, CTA reachable.
21. 390: checked, overflow 0, CTA reachable.
22. 320: checked, overflow 0, CTA reachable.
23. Relevant horizontal overflow: zero in all recorded states.
24. CTA: trial clicks and viewport/hit-test assertions pass at all six widths.
25. Suggestions: visible, selectable, above the map; viewport clamp passes.
26. Accepted cleanup: unchanged, exercised, final fresh GET empty.
27. Exact-item polling: unchanged, exercised, offline regressions pass.
28. Unrelated homepage/catalog changes: none; scope assertion passes.
29. B1-B16: untouched; absent from diff.
30. Staging persistent application state: unchanged; session cart cleaned.
31. Production: untouched.
32. Migration: fresh remote read canonical.
33. Marker: Coordinator-provided canonical evidence; no independent hosting read.
34. Final clean tree: post-commit porcelain result in `final-git.txt`.

## REMAINING VISUAL DEVIATIONS

| Difference from prototype | Classification / reason |
| --- | --- |
| Email, surname, country, city, region, postcode remain visible; longer form | REQUIRED_NATIVE_WOO_DIFFERENCE — current native validation/data preserved |
| Phone stays in native address group; payment/pickup retain native positions and labels | REQUIRED_NATIVE_WOO_DIFFERENCE — no unsafe input reparenting |
| CTA remains at native form end on desktop; summary title is native «Детали заказа» | REQUIRED_NATIVE_WOO_DIFFERENCE — native action/labels preserved |
| Additional address fields remain in their API order group; comment uses native note control | REQUIRED_NATIVE_WOO_DIFFERENCE |
| Separate native required privacy plus Woo terms text, rather than prototype's two custom checkboxes | REQUIRED_NATIVE_WOO_DIFFERENCE |
| Real map shows a DaData point or business listing, no coloured demo zones/minimums/drag-to-assign | DEFERRED_BUSINESS_DATA — approved polygons and thresholds unresolved |
| Route-based card and menu-back link, rather than fixed modal over homepage/close button | ACCEPTABLE_RESPONSIVE_ADAPTATION — full native form scroll and navigation |
| 701/700 transition, full-height mobile sheet and native summary before CTA | ACCEPTABLE_RESPONSIVE_ADAPTATION — requested widths and correct Woo composition |
| Native product image placeholder remains where the accepted checkout has no Woo thumbnail | REQUIRED_NATIVE_WOO_DIFFERENCE — catalog/product data untouched |

No unresolved actual product visual defect found in the reviewed candidate.
Provider live tiles are not a deterministic pixel baseline. Full-page offscreen
iframe compositing limitation is covered by separate native-viewport map crops.

## UNRESOLVED / DEFERRED

No courier auto-enforcement; no invented polygons/minimums. МАЗАНКА/Мазанка
3500 vs 4000 remains unresolved. Acquisition remains OFF. Four accepted
staging warnings remain outside scope. Live deployment/runtime verification
requires the separate backup-gated Batch.

The historical whole `test_s1_r1.py` was also attempted: its legal/payment/consent,
cart/shrimp and lint cases passed, then its old Batch-specific changed-file
allowlist rejected the new checkout files. That scope gate is not applicable to
this implementation Batch and was not weakened. Dedicated current scope,
legal/payment, secret and checkout gates pass instead (`static-evidence.json`).

## FINAL GIT

Post-commit `final-git.txt` records branch, SHA, parent, seven-file list, empty
porcelain status and exact remote refs. No protected branch is advanced.

## NEXT

Separate `Checkout Visual Parity — Backup-Gated Staging Deploy + Runtime
Verification` only after acceptance. That future Batch must create/verify a
fresh backup before deployment. None of that work is performed here.

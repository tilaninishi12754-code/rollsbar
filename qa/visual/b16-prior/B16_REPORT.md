# B16 final visual audit — BLOCKED

Independent audit of starting HEAD cf5e22bb5a7419af2d7da5e9aa03fecdf14b5446.
Root C:/AI/Rolls Bar Project; branch wordpress/visual-parity-2026-10-14;
initial tree CLEAN. Approved immutable SHA
a5e524392abcf89ffd5ace2a18218a6b59ed3b61 verified. No application edits.

## Findings preventing closure

The existing component gate passes, but it does not prove assembled-page parity.
`b16-assembled.mjs` uses the existing git-archive approved preview, local-only
requests, identical viewport pairs and loaded fonts. It measures unmodified
document coordinates, headings, heights, overflow and duplicate IDs. It does not
generate expected images, apply masks, align components or change tolerances.
Results: `B16_ASSEMBLED.json`. These are diagnostic measurements, not pixel parity.

1. First catalog heading and following catalog content are 21px lower than
   approved at every canonical viewport. Example 1440: approved Роллы heading
   y=423, current y=444; 320: approved y=322, current y=343. First section uses
   current 30px desktop /23px mobile internal padding versus approved zero
   internal padding with different preceding placement. Subsequent catalog
   section heights mostly match; the offset is not cumulative card-row growth.
   Component-origin rounding and isolated crops cannot detect this page offset.
   No accepted exception explicitly permits it. Requires a scoped spacing fix
   and a complete rerun before closure; no speculative correction made here.
2. Delivery remains a different visual block: current front-page.php renders
   rule cards and a pending-address panel; immutable index.html renders a map
   card, map overlay, legend and additional content. B15_REPORT.md explicitly
   says delivery is deferred and absolute whole-page parity is unproven.
   This is not a narrow accepted-exceptions registry entry. Current contacts
   consequently start hundreds of pixels earlier. Closing this by copying
   schematic demo zones or changing business delivery rules is outside B16.
   Coordinator must resolve the outstanding delivery visual scope without
   inventing rules/data, then rerun final acceptance. No new exception proposed.

|Width|First heading delta|Contacts top delta|Delivery height delta|
|---:|---:|---:|---:|
|1440|21|-388.40625|-549.40625|
|1051|21|-365.859375|-543.40625|
|1050|21|-761.25|-918.25|
|1024|21|-761.25|-918.25|
|701|21|-813.296875|-970.296875|
|700|21|-733.203125|-847.703125|
|390|21|-856.671875|-971.171875|
|320|21|-976.5625|-1091.0625|

All eight current documents have zero horizontal overflow and no duplicate IDs.
Section order is preserved. No finding is hidden by a new exception.

## Initial checks

Normal Chromium gate rerun on unchanged application: 166 passed /18 explicit
skips /0 failed, no retries (5.1 minutes). All 285 protected SHA256 hashes verified
independently. Zero new expected screenshots. Existing gate remains component
acceptance, not full assembled-page acceptance. Normal JSON copied to ignored
qa/visual-results/b16-initial-gate.json.

B11 133, B12 812, B15 22 contract assertions PASS. All WordPress PHP files lint
clean; existing QA modules and application app.js Node syntax PASS; diff check
PASS. Local adapters are not live Woo proof.

## Exception review

Read every entry of accepted-exceptions.json and the corresponding capture paths.
Existing gate re-exercises narrow B6B/B11 counter wrapping and accent copies,
B7 media containment, B9 focus/inert/backdrop and raster cap, B10 native selector
caps, B13 exact backing rectangles, B14 search corner/fallback isolation, and B15
broken approved logo box. Registry, masks, caps and baselines unchanged. No
scope expansion authorized. Passing component checks does not justify broadening
these to cover absolute catalog or delivery/contacts placement. Exception review
cannot substitute for resolving the findings above.

## Adversarial question

What could all existing tests still be missing? Absolute positions between
individually aligned crops and the intervening deferred delivery block. The
independent full-document measurement found both. Duplicate IDs were also checked
and none found. Existing representative sweep covers sequential overlays,
populated cart through search/details/footer, long cart and final removal,
focus/Escape/body lock, longest/large-price cards and fallback containment.
No independent exhaustive accessibility certification is claimed.

## Preservation and disposition

B1–B15/B6B component acceptance retained, no baselines regenerated. Application,
catalog/business data, exception registry, AGENTS and skills unchanged. No
checkout/reset/merge/rebase/push/deploy or external environment access. No staging,
production, provisioning, migration integration, MAX, Metrica or acquiring work.

118 canonical products, 126 representations, 8 Hits, 13/26 variable identities,
WOK 6/18 and shrimp 3 remain under existing deterministic contracts. Source ID
identity remains canonical. upsell-soy-sauce /upsell-ginger /upsell-wasabi remain
excluded from public catalog/search. Their 20 RUB seed is PROVISIONAL; live Woo
prices, stock and provisioning remain NOT LIVE-VERIFIED. External delivery,
notifications/MAX, acquiring, analytics and other go-live prerequisites unchanged.

Local Visual Parity is NOT COMPLETE. No PASS commit. QA evidence is left for
Coordinator review; no integration started.

Initial responsive run completed Chromium 69/69 PASS, then Firefox failed before
application inspection with `browserContext.newPage: Target crashed`. The full
suite was rerun outside the restricted execution environment, as PRE-B16 already
documented a Firefox launch restriction. This infrastructure failure is not
silently classified as an application PASS.

Final unrestricted execution: PASS, 85 completed rows: Chromium 69/69,
Firefox 8/8, WebKit 8/8. Exact 320–1440 grid and breakpoint neighbors preserved.
Application JS errors/warnings zero; protected hashes before/after 285/285.
Evidence: B16_RESPONSIVE_CROSS_BROWSER.json. Original PRE-B16 JSON restored
byte-for-byte. No browser-specific application exception introduced.
No application changes occurred between initial and final gates; normal gate
remains 166/18/0 and final screenshot total 285. New QA script syntax and final
diff check pass. HEAD remains the starting SHA. No commit created; four new
uncommitted QA/evidence files remain intentionally available for review, so final
tree is NOT CLEAN. This is a blocked audit, not a completed PASS batch.

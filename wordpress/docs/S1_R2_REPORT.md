# S1-R2 release preparation — staging only

2026-10-24, Europe/Moscow. This file records local release preparation, not live
staging acceptance. Exact release SHA, workflow results and runtime receipts are
recorded in the worker's final report after the commit exists.

## Starting evidence

- First Git command: `git rev-parse --show-toplevel`; physical root
  `C:/AI/Rolls Bar Project`, PASS.
- Clean branch `wordpress/staging-repair-s1-r1-2026-10-24`, HEAD
  `679ae474de2d51b7cee944a8235eb42a6e51eea2`, parent
  `22ad41e3d03ec1a9efae0bde2560a4895d6e2708`; no operation in progress.
- Fresh GitHub migration and integration both at the expected parent; repair
  branch absent. Approved remains `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`;
  local accepted Visual remains `5e7836e22110ec076603bb1fa2b12f8bb90ee756`.
- Complete S1-R1 diff inspected: only repair preparation, verifier and evidence.
  Unmodified S1-R1 suite passed all 41 checks before follow-on edits.
- Read-only security audit run **40082930926**, job **120840009584**, on
  `22ad41e3d03ec1a9efae0bde2560a4895d6e2708`: historical snapshot
  `20261023T215945Z` is the newest of five, integrity PASS. One new backup cannot
  evict it under retention=5. Core checksum PASS, WP 7.1.3, wp-config 640.

## Release behavior

1. Exact 40-character release checkout; existing staging required.
2. `prepare-s1-r2-backup.sh` verifies staging path/identity, noindex and pinned
   WP/Woo versions. Revalidates historical archives and manifest outside web-root.
3. Existing backup script creates a new backup. Optional named preservation
   guard refuses retention eviction before creation and again before deletion.
   Only an actual successful backup plus independent archive/checksum/manifest
   verification exports the existing S1-R1 fresh-backup acknowledgements.
4. Existing bootstrap runs with `ROLLSBAR_IMPORT_SMOKE=0`. No full importer.
5. `repair-s1-r2.sh` runs the existing entrypoint in dry-run. Canonical skips
   apply; missing/empty/pending invokes the existing exact confirmation. Unknown
   states fail. Post-dry-run must be canonical. Live Woo and legal checks follow.
6. Existing SEO provisioning, HTTP hardening, SEO audit and marker ordering
   remain unchanged. No independent/manual marker write was added.

The proven repair still writes exactly one metadata key. Its transaction now
also snapshots all product/variation posts, metadata and term relationships,
excluding only the one target options row. It compares before/after prior to
COMMIT and reports deterministic product/catalog hashes. Deliberate other-product
and variation corruption fail and roll back in local tests.

## QA infrastructure reconciliation

- Gate B validates 118 main identities, 126 representations, eight deduplicated
  Hits and the exact 118-member search index using the actual current DOM.
- The old five-card and legacy add-button assumptions are replaced by B11/B15
  native cart controls. Existing Store API, cart, checkout, RUB, phone and Local
  Pickup checks remain. The old delivery-tier DOM assumption is replaced by the
  accepted B15 deferred-delivery/receipt-payment presentation; no UI changes.
- Real shrimp selection asserts exact visible choices, request payload, native
  cart response and independent Store API option metadata.
- Desktop/mobile check sections, overflow, JS errors and intended legal,
  reviews/jobs templates. Order submission endpoints are blocked in test contexts.
- DaData workflow reuses the current add helper but retains the exact existing
  two probes, coordinates, precision, warning and country-label contract.
- These two browser workflows are manual-only so they can run after the exact
  deployed marker, instead of racing the deployment on push.
- Hidden upsells remain excluded. Their provisional local-only seeds are never
  provisioned on staging just to satisfy QA; absence is reported explicitly.

## Local validation

`python -X utf8 qa/repair/test_s1_r2.py`:

- Original legal/selector/cart/footer suite with an explicit, bounded S1-R2
  scope allowlist; original S1-R1-only scope mode remains unchanged.
- Extended shrimp suite: 191 assertions, including custom/duplicate/missing
  refusal, transaction failures, other-product and variation corruption rollback.
- Current catalog accepted; four deliberate count/membership mismatches rejected.
- Actual backup shell executed with isolated command adapters: success, missing
  recovery point, corrupted archive, retention risk, failed export, version mismatch.
- Actual repair shell sequencing: pending, canonical no-op, conflict, apply
  failure, post-state failure and runtime failure; later stages cannot run on failure.
- PHP/Python/shell syntax, all workflow YAML, repair-branch push isolation,
  secret-pattern scan and diff whitespace checks PASS.

No application/theme/CSS/catalog/price/stock/image changes, dependency or version
upgrades, production changes, notification credentials or external sends.
Live acceptance remains mandatory; green local checks are not staging PASS.

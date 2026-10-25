# ASSET CACHE BUSTING STATUS

ASSET CACHE BUSTING: PASS / READY FOR BACKUP-GATED STAGING DEPLOY.
Implementation only; no deployment or device root-cause claim.
Local evidence: `qa/visual-results/asset-cache-busting/`.
Post-commit SHA / remote / clean-tree proof: `final-git.txt` there.

## PREFLIGHT

First Git command: `git rev-parse --show-toplevel` -> `C:/AI/Rolls Bar Project`.
Initial status, staged, unstaged and untracked lists were empty.
No reset, stash, merge, rebase or branch switch performed.

## STARTING STATE

Branch `wordpress/checkout-visual-parity-2026-10-25`.
Local and fresh remote HEAD `5c5310070ef43d31b58d4e3c5973f0e1242ff52e`.
Fresh remote migration `e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea`.
The single new implementation commit has that exact feature HEAD as parent.

## EVIDENCE / PROBLEM

The local PHP fixture executes the starting commit's actual enqueue callbacks:
all four theme assets received version `0.1.0`; checkout CSS/JS and the two
conditional public analytics assets received `0.1.8`. Content changes therefore
did not necessarily change their effective asset URLs. That is a proven design
gap, independently of the owner's Android / Telegram rendering observations.

`enqueue-versions.json` records before/after versions and effective fixture URLs.
This Batch does not prove that stale cache caused the physical-device defect.

## DESIGN

Native WordPress `$ver`: first 16 lowercase hex characters of SHA-256 over each
file's actual bytes. Only local absolute Unix / Windows drive paths are accepted;
regular/readable file checks precede hashing. No network, timestamp, random
value, dependency or release-metadata bump.

Theme helper `rollsbar_theme_asset_version()` is independent of the plugin.
Plugin helper `RollsBar_Asset_Version::for_file()` is shared by checkout and
analytics, required once by each consumer; no theme/plugin coupling or bootstrap
change. Each helper memoizes by absolute path for the current PHP request,
including unavailable-file results. A changed fixture keeps the cached value
within one request and receives the new value in a fresh request.

## THEME ASSETS

| Asset | Before | Local PHP fixture after |
| --- | --- | --- |
| style.css | 0.1.0 | 105b7a57dc31f25f |
| assets/css/app.css | 0.1.0 | 04045be58bf111e2 |
| assets/css/legal.css | 0.1.0 | 4fa5ab05f1f41fd4 |
| assets/js/app.js | 0.1.0 | e72bd5fbadebda5c |

Style URI pairs with stylesheet directory; app/legal assets pair with template
directory. Existing URLs, dependencies, order, footer flags and conditional
loading remain identical in the before/after callback comparison.

## CHECKOUT ASSETS

| Asset | Before | Local PHP fixture after |
| --- | --- | --- |
| assets/css/checkout.css | 0.1.8 | 7b26a6c99aaa4c65 |
| assets/js/checkout.js | 0.1.8 | 3a8315e1c04d3c8d |
| assets/css/analytics-consent.css | 0.1.8 | 35d506cdda5cd1a4 |
| assets/js/analytics.js | 0.1.8 | 29c7a673da21bbca |

The two extra analytics files are public assets discovered during the complete
enqueue inventory. Covering them is necessary for the requested adversarial
check that every RollsBar-owned public CSS/JS has content versioning. Only their
enqueue versions change; analytics consent, enablement, config, jQuery dependency
and behavior are unchanged. The admin-only delivery-map editor and third-party
assets are outside the public asset inventory and are untouched.

These are local Windows checkout hashes, not claimed deployed values. Canonical
Git LF bytes and Windows CRLF checkout bytes legitimately have different hashes;
deployment computes the hash of its actual local file bytes.

## HASH CONTRACT

`test_asset_versions.py`: 9 tests PASS. Known bytes `abc` produce
`ba7816bf8f01cfea` in both helpers. Repeat calls and equal-content files retain
that value; different bytes produce another value. Editing fixture A in a fresh
request changes only A, leaving B's version exactly unchanged. Same-request
memoization is verified by rewriting only an owned test fixture between calls.

All eight actual enqueue versions equal their respective SHA-256 prefixes.
All other enqueue and inline-config arguments match the starting implementation.
Neither helper contains time/microtime/random/uniqid/filemtime cache breakers.
No absolute filesystem path appears in the captured browser-facing arguments.

## SAFE FALLBACK

Unavailable files return the caller's existing release version. Missing files,
directories, relative paths, nonlocal stream paths and a filesystem-scope denial
are tested without warnings or fatal errors. `is_file()` / `is_readable()` checks
and the hash read suppress filesystem warnings so failures cannot leak paths.
The hash-read failure branch returns the same fallback if a file disappears
after the checks. A memoized failure does not incorrectly cache another caller's
fallback string.

## CHANGED FILES

Application, exclusively version delivery:

- `wordpress/wp-content/themes/rollsbar-theme/functions.php`
- `wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-checkout.php`
- `wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-analytics.php`
- `wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-asset-version.php` (new)

QA:

- `qa/checkout/check_static.py`: four exact allowed PHP paths; no new wildcard.
- `qa/checkout/asset_version_fixture.php` (new)
- `qa/checkout/test_asset_versions.py` (new)
- `qa/checkout/ASSET_CACHE_BUSTING_REPORT.md` (new)

Historical S1-R1 allowlists and workflow files are untouched.

## BYTE PRESERVATION

Every theme/plugin CSS/JS file (9 files, including the admin-only script) is
unchanged against `5c531007...`. `byte-preservation.json` records unchanged Git
blob IDs, canonical SHA-256 and raw working-checkout SHA-256 for each file.

For each path, both assertions pass:

1. Raw working bytes equal `git cat-file --filters 5c531007...:<path>`.
2. `git hash-object --path=<path> <path>` equals the starting Git blob ID.

This respects the already-existing Windows CRLF checkout filter without
rewriting any file or normalizing away a change. The required app.css/app.js/
checkout.css/checkout.js are included. Theme/plugin metadata, catalog and
B1-B16 baselines/masks/tolerances remain unchanged.

## QA

- 9 focused PHP/hash/enqueue tests PASS (`hash-contract-tests.log`).
- Existing 21 checkout/S1-R3Q tests PASS (`existing-21-tests.log`). An intentional
  offline cleanup HTTP-500 fixture prints a diagnostic; unittest result is OK.
- Existing `qa/checkout/check_static.py` PASS: native API/fields, geocode policy,
  legal/payment/privacy negative cases, workflow audit, exact scope, secret scan.
- PHP lint: theme helper/enqueues, plugin helper, checkout, analytics, QA fixture.
- JS syntax: unchanged theme app.js, checkout.js and analytics.js.
- `git diff --check` PASS; changed-file secret scan has zero findings.
- 38 unchanged workflows: zero automatic feature-branch push matches.

Checkout field registration and DaData configuration tails are compared
directly with the starting commit and are identical. Theme catalog/cart helper
code after the enqueue section is also identical. There is no frontend byte
change, so the expensive visual screenshot suite is intentionally not run.
No real browser session, cart, order, server or external notification is used.

## COMMIT

Exactly one logical commit: `Version frontend assets by content hash`.
Parent `5c5310070ef43d31b58d4e3c5973f0e1242ff52e`.
Final SHA and exact eight-file list are recorded post-commit in `final-git.txt`.

## REMOTE FEATURE BRANCH

Only `wordpress/checkout-visual-parity-2026-10-25` may advance, via normal
fast-forward push. The remote SHA is read back and compared with local HEAD;
results are recorded in `final-git.txt`. No workflow dispatch.

## MIGRATION PRESERVATION

Fresh migration read remains exact `e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea`.
No protected ref is advanced.

## STAGING

No access/mutation: no deploy, backup, cache purge, DB change, import, marker write,
upgrade, order or notification. The delivered change is pre-deploy only.

## PRODUCTION

No access or mutation.

## ADVERSARIAL GAP

1. Every owned public CSS/JS: yes, 8 enqueue targets inventoried and executed.
2. app.css no longer only Version 0.1.0: yes, its own SHA-256 prefix.
3. app.js own version: yes, actual enqueue assertion.
4. legal.css own version: yes, actual conditional enqueue assertion.
5. style.css own version: yes, stylesheet URI/directory pairing tested.
6. checkout.css own version: yes, actual enqueue assertion.
7. checkout.js own version: yes, actual enqueue assertion.
8. Changed bytes change the URL version: yes, fixture A and effective URLs tested.
9. Unchanged bytes preserve version: yes, repeated/fresh request and fixture B.
10. time() breaker absent: yes, helper source guard.
11. Randomness absent: yes, helper source guard.
12. CSS/JS bytes unchanged: yes, all 9 files' raw checkout bytes and Git blobs.
13. Woo semantics unchanged: yes, field registration identical and existing QA OK.
14. DaData unchanged: yes, config tail and JS bytes identical.
15. Catalog unchanged: yes, absent from the exact diff scope.
16. B1-B16 untouched: yes, absent from diff; no masks/tolerances changed.
17. Migration unchanged: yes, fresh remote SHA verification.
18. Staging untouched: yes, no staging operations performed.
19. Production untouched: yes, no production operations performed.
20. Final tree clean: empty post-commit porcelain recorded in `final-git.txt`.

No high-impact unresolved implementation item. Physical-device root cause is
not attributed to cache yet. After deployment changed asset bytes receive new
URLs through native WordPress versioning; device/runtime verification remains
the next Batch.

## FINAL GIT

Same feature branch; one new commit, exact expected parent, clean tree.
Post-push exact SHA / migration verification: local `final-git.txt` artifact.

## NEXT

Backup-Gated Staging Deploy + warm-cache device/runtime verification.

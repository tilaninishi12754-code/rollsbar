# S1-R1 — minimal local legal / shrimp repair

Date: 2026-10-24 (Europe/Moscow). **Local acceptance PASS. Staging is not fixed or accepted by this batch.**
The single local commit SHA and final clean-tree evidence are returned in the completion report, avoiding a self-referential commit ID in this file.

## Preflight and continuity

- First Git command was exactly `git rev-parse --show-toplevel`: `C:/AI/Rolls Bar Project`.
- Starting branch: `wordpress/integration-2026-10-23`.
- Starting HEAD: `22ad41e3d03ec1a9efae0bde2560a4895d6e2708`.
- Exact ordered parents: `421d3db121e8fa3fcbb3f2fa06751858821de674`, `5e7836e22110ec076603bb1fa2b12f8bb90ee756`.
- Initial status: CLEAN, including untracked project files; no merge/rebase/cherry-pick state.
- A narrow no-tags fetch refreshed only integration/migration tracking branches. Both are exactly `22ad41e3d03ec1a9efae0bde2560a4895d6e2708`.
- Approved tracking ref remains `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
- Local Visual branch remains `5e7836e22110ec076603bb1fa2b12f8bb90ee756`; its object is also merge parent 2. No remote Visual branch was required/fetched.
- New branch absence checked before creation: `wordpress/staging-repair-s1-r1-2026-10-24`; clean start at exact integration SHA.
- S1 deploy `40030630157` failed after partial staging mutation; authoritative Coordinator evidence supplied with this task, not re-probed.
- Snapshot `20261023T215945Z` preserved by zero access: no read/download/restore/delete/rotation or retention change.
- Admin workflow `40030630098` failed waiting for the deployed marker; runtime Admin UX verifier never executed. Local workflow source confirms marker equality is checked before that verifier. No separate admin regression proved or fixed.
- No staging/production access, DB change, push, notification, email, secret change, restore, version upgrade or deployed-marker change in this batch.

## Legal evidence and decision

Evidence inspected:

1. `GO_LIVE_MATRIX.md`, current owner decision layer dated 2026-10-14: legal/payment pages and privacy required; acquiring deferred, receipt payment, delivery enforcement deferred. No requirement for an extra legal-index footer pill.
2. `deploy/provision-legal-pages.php`: nine distinct published pages, legal-index mapping, existing-page preservation, provider-neutral copy, delivery disclosure, Woo terms and WP privacy mapping.
3. `deploy/verify-staging-payment-readiness.php`, checkout/review classes, review template: receipt-only payment, acquiring disabled, separate required consent.
4. `qa/visual/B15_REPORT.md` and accepted `footer.php`: approved footer navigation/order and eleven total pills (menu, seven legal destinations, reviews/jobs/additional reviews).
5. Immutable approved `a5e5243:index.html:663–674`: delivery, requisites, offer, refund, privacy, cookies and payment security; no `legal.html` footer link.
6. Coordinator's S1 public evidence: public offer link present; legal-index page published, absent from footer. No fresh staging request made.

Decision: **`pravovaya-informaciya` is required as a published nonempty page, not as a visible footer link. No application/footer/CSS/JS change is justified.** Its page check remains, with explicit missing/draft negative cases. B15 and all protected visual assets remain byte-for-byte unchanged.

Required footer destinations:

- `/dostavka-i-oplata/`
- `/rekvizity-prodavca/`
- `/publichnaya-oferta/`
- `/oplata-i-vozvrat/`
- `/politika-konfidencialnosti/`
- `/cookies/`
- `/bezopasnost-onlajn-oplaty/`

The old verifier searched raw PHP for literal `/slug/` strings. B15 builds `home_url('/' . $slug . '/')`; therefore the original verifier incorrectly rejected a rendered offer link. The test harness reproduces the exact original failure using the accepted SHA's verifier and current actual footer.

`verify-staging-legal-pages.php` now buffers the actual runtime footer, then `legal-footer-contract.php` parses its HTML with DOM/XPath. Only actual anchors with nonempty text within footer navigation count; destinations must equal the appropriate `home_url`, independently listed in the verifier. Commented markup and incorrect destinations do not count. Static `.html` destinations fail. No HTTP request or template source extraction is used for footer proof. DOM is required and fails closed if unavailable. Existing legal checks remain; markup-only empty pages and mixed-case Russian/Latin SberBank wording are additionally rejected.

## Shrimp source, serialized contract and mechanism

Canonical identity is `_rollsbar_source_id = shrimp-tempura`. The importer stores the `options` array from `wordpress/data/catalog.json` as JSON, with Unicode/slashes unescaped. The exact approved value is:

```json
[{"label":"Соус","choices":["чесночный","сырный","томатный"]}]
```

History before `7aa7ca1` proves the only recognized historical pending value:

```json
[{"label":"Соус","choices":[],"pending":true}]
```

`functions.php::rollsbar_product_selection_data` decodes this JSON, adds computed `pending: false` for the selector, and JS validates against each group's choices. `RollsBar_Cart_Actions::options` reads the same metadata and persists selected label/value into native cart/order metadata. Tests feed the repair's serialized format through these real readers, reject a WOK sauce substitution, and exercise native cart/order adapters.

Root cause: routine live deployment explicitly preserves the promoted Woo catalog and disables smoke import. Updated source JSON alone cannot update existing Woo metadata. This is a metadata migration gap, not a reason to import the catalog again.

Implementation:

- Manual entrypoint: `deploy/repair-staging-shrimp-options.php` (WP-CLI eval-file only).
- Single-purpose implementation: `deploy/shrimp-options-repair.php`.
- No bootstrap, workflow, plugin or automatic execution registration.
- Default/unset mode is dry-run. Unknown modes refuse.
- Canonical value is read from the repository catalog and checked against the exact owner-confirmed three-choice contract; no price/catalog import runs.
- Exact identity lookup includes all statuses/post types. Missing product, duplicates, orphan/variation/trash identities, ambiguous source metadata and duplicate option keys refuse.
- Missing/empty or exact decoded historical pending metadata can be repaired only with explicit confirmation. Canonical is `ALREADY CORRECT` with no write. Any other nonempty/custom/malformed/extended pending value refuses; raw custom data is not logged.
- Prepared SQL changes only one `_rollsbar_options_json` row. Existing row updates compare the precise prior bytes, row ID, product ID and key. Missing rows are inserted only after locked absence verification.
- InnoDB required. A SERIALIZABLE transaction locks identity lookup and product/metadata/term snapshots. The exact before/after product and full unrelated metadata/terms must match before COMMIT. Unexpected delta, write count or database failure rolls back. No importer, product save or WordPress metadata mutation hook is invoked.
- Only this product's WP and native Woo metadata cache entries are invalidated after success. Woo cache API presence is checked before DB access.
- Reports contain identity, key, recognized before-state/hash, canonical after-options, write count and status; no credentials or raw custom values.

## Local proofs

Command from repository root, using the existing runtimes without installing anything:

```text
python -X utf8 qa/repair/test_s1_r1.py
```

The runner records detailed output under ignored `qa/visual-results/s1-r1/results.json`. Committed fixtures/test runner reproduce the results without WordPress, a database, HTTP, email, or staging access.

- 41 runner checks PASS, including 7 PHP lint checks and Python parsing.
- 26 legal scenarios: 2 valid renders (homepage/internal), exact original false-positive reproduction, 23 deliberate invalid variants, all rejected for the expected reason.
- Negative legal cases cover each of the seven missing links, wrong destination, commented navigation, stale footer/page `.html`, wrong Woo terms, wrong WP privacy, missing/draft legal-index page, empty offer, Russian/Latin SberBank wording, missing review consent, missing/optional checkout consent, missing delivery disclosure and incomplete requisites.
- Shrimp: 181 assertions PASS. Dry-run A missing and B pending propose precisely the canonical array with 0 writes; C canonical returns `ALREADY CORRECT`; D custom, E duplicate and F missing identity refuse. Also empty/malformed/extended pending, duplicate metadata, source conflict, wrong type/status and environment/backup/confirmation guards.
- Fault injection covers nontransactional engine, failed compare-and-set, write failure, unexpected title delta and commit failure. Full-store snapshots remain unchanged on refusal/rollback.
- Full deterministic store contains 118 products, 26 variation records, WOK option data, three hidden upsells, all metadata and client edits. Compare everything except shrimp's one approved key. Price/regular/sale, stock/status, SKU, title/slug, description/excerpt, images/gallery, categories, attributes, variation children, availability, source identity, arbitrary metadata, WOK, hidden upsells and all other products remain unchanged.
- Applied missing/empty/pending fixtures each write exactly one metadata row. Repeat application makes zero further writes. Canonical application makes zero writes from the outset.
- Exact serialized repair value passes the real theme selector and cart option readers; three expected choices, required selector, no pending/blocked state.
- Existing B11 cart contract: 133 assertions; B12: 812 assertions / 148 line paths; B15 settings/footer: 22 assertions. All PASS.
- Existing static secret patterns over WordPress and new QA sources: PASS. `git diff --check`: PASS.
- Scope guard confirms no application/catalog/workflow/backup/marker/baseline changes. Full pixel/assembled-page suite is not triggered because application files do not change.

These are deterministic local proofs, not a claim of live MySQL concurrency, live WP/Woo runtime, live cache or final staging acceptance. Real runtime compatibility and exact live delta remain S1-R2 checks. Missing runtime prerequisites refuse before writing.

## S1-R2 execution plan — prepared only, not run

1. Obtain separate Coordinator approval for the exact repair commit/release. Preserve the S1 snapshot.
2. Use the existing deploy backup gate in `deploy_staging_wordpress.py`: a **new** DB+uploads snapshot, manifest/checksums and archive integrity PASS, before any WordPress mutation. No reuse of `20261023T215945Z`.
3. Sync the exact application and repair files; retain routine `ROLLSBAR_IMPORT_SMOKE=0`, no full import. Safe future integration point is after required sync/provisioning and before the bootstrap final runtime-invariant block (`bootstrap-staging.sh`, before legal/runtime acceptance). S1-R1 does not insert this hook.
4. Run the manual repair in default dry-run on the intended WordPress path. Reconcile live identity/value/conflicts; never override a conflict automatically. Capture before product/meta snapshots.
5. Only after fresh backup PASS, provide the explicit manual environment values:
   - `ROLLSBAR_SHRIMP_REPAIR_MODE=apply`
   - `ROLLSBAR_CONFIRM_SHRIMP_OPTIONS=staging:shrimp-tempura:options-only`
   - `ROLLSBAR_FRESH_BACKUP_VERIFIED=YES`
   - `ROLLSBAR_FRESH_BACKUP_SNAPSHOT=<new verified UTC YYYYMMDDTHHMMSSZ>`
6. Invoke `wp --path=<staging WordPress path> eval-file <project>/wordpress/deploy/repair-staging-shrimp-options.php` once. This command is documentation only and was not executed. Re-run default dry-run for `ALREADY CORRECT` and verify exact live delta/real rendered selector.
7. Require all final runtime/checkout/Local Pickup/DaData/admin acceptance in the approved order. Preserve the deployed marker invariant: the existing marker step can only run after prerequisite deployment acceptance succeeds; never advance it manually to unblock Admin UX.

Guards require WordPress environment `staging`, exact home/site URLs `https://staging.rollsbar.ru`, noindex (`blog_public=0`) and explicit apply confirmation. Backup acknowledgement must name a new snapshot no older than two hours and not from the future. It is an operator/deploy PASS acknowledgement, **not an independent archive verification**; the existing backup gate owns actual archive verification. The mechanism never reads, modifies or rotates backup files. Production automatic execution: NO. Execution in S1-R1: NO.

## Adversarial audit and deferred scope

Question: **Could this repair accidentally mutate or hide more than the two proven S1 blockers?**

- Real missing footer links still fail, now for all seven approved destinations. No legal navigation removed or invented; legal-index page validation retained.
- No full importer, all-product writer, product save, unrelated-key write or automatic execution path exists. SQL is confined to one resolved identity/key; full-store tests prove protected fields/other products unchanged.
- Unknown client option values and ambiguous identities refuse. Row locking, exact prior-value comparison and transaction rollback protect the checked value and approved delta.
- Environment/confirmation/backup guards fail before DB access. Fresh backup is mandatory for the future apply path; nothing touches production or the existing S1 snapshot.
- Marker, backup scripts/retention, deploy workflow and B15 visual files remain unchanged. Admin UX is correctly deferred, not bypassed.
- No unresolved high-impact risk within the local repair scope. Live runtime/delta proof remains explicitly outside this batch.

Deferred: S1-R2 backup-gated redeploy/repair; full staging checkout/Local Pickup/DaData/admin acceptance; Inter B6B390 robustness; provisional hidden-upsell values; externally verified live price/stock truth; MAX integration (Telegram is not the current launch requirement); delivery ambiguity/automatic enforcement OFF; acquiring OFF with `Оплата при получении`; analytics/Metrica; remaining owner/external launch inputs. Authenticated staging email remains previously E2E READY, no email sent. No invented polygons, DaData unchanged, WooCommerce pinned 11.1.2, staging noindex unchanged, production untouched.

Next: return the completion report to Coordinator. No push or automatic deployment.

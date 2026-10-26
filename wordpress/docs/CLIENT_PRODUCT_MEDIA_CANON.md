# Client Product Media Canon

Version: **client-media-2026-10-21**. Customer website product media, effective 21 October 2026.

**For product media assignments covered by CLIENT MEDIA CANON v2026-10-21, client-supplied media manifest overrides legacy catalog/Yandex image sources. Do not change this rule without new explicit customer/user media input.**

## Sources and Project No Loss

Original private packages are immutable customer provenance, not temporary files:

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| 19-10-2026_09-24-58.zip | 7550703 | 9ce332520d715225a527bde90b439aa9a306579415ed3d18ab18212e1889b531 |
| 21-10-2026_10-48-20.zip | 8280976 | 336150f653fc2247e92612fe3388a996449222b3bc17e2b351c97d804d5d00ef |

Both contain `Таблица Роллс бар.xlsx`. The **21.10 table alone controls photo assignment** (61 rows, 47 product names, 36 photo names). The 19.10 table is historical evidence (50 mapped rows). Latest adds 11 assignments and removes none. Table SHA-256 values:

- Historical: `763a87755fcf0b11571f19db5190b5d872069e31811261f106cc563dfd301e57`
- Current: `3cd4c86a8bdec068162742df466d3e0447d9dad7ae7a978951aeb04febdf11f8`

Original ZIPs, the two original XLSX byte streams and a review-only non-media difference report are preserved outside this public repository, in the persistent project `source-evidence/client-media-2026-10-21` folder. Coordinator also holds the originals in persistent project/library storage. Never publish private ZIP/XLSX originals or unrelated workbook metadata in Git. The 34 detected non-media field differences are recorded privately and **not applied**.

## Committed deployable canon

`wordpress/data/product-media/client-2026-10-21/manifest.json` and `images/` contain everything runtime needs. Downloads, chat attachments, private originals, Yandex and any particular staging DB are not runtime dependencies.

- 36 unique canonical image binaries, all 1254 × 1254; no missing or unused photo files.
- 61 source assignment rows preserved, including category, customer name, size, table row, photo identity and resolution status.
- 57 resolved rows target **45 explicit catalog source IDs**. Runtime never matches fuzzy product titles.
- Four rows / two names are `deferred_new_product_identity`: **Охотничья** (rows 83–84, 30/50 см) and **Салями** (85–86, 30/50 см). No corresponding canonical source ID exists. Their two images and rows remain canonical evidence; their attachments are imported, but no Woo product is invented or assigned. A separate catalog decision is required.
- Exact category/name/variant matching resolves the normal rows. Two explicit rice aliases are supported by exact category and composition: `Запеченный рис спайси` → `baked-rice-shrimp`, `Запеченный рис унаги` → `baked-rice-salmon`. This applies media only; names/composition/prices remain unchanged.
- 32 actual WebP files remain WebP. Four original `.WEBP` members are actually PNG: **Запеченный рис**, **Запеченные маменори**, **Огонек**, **Итальянский**. Derived copies use `.png` with identical bytes. No recompression.
- Manifest records archive/member provenance, original photo names, source/derived hashes, detected MIME, dimensions, per-asset source IDs and source table row indexes.

## Sync and rendering

```sh
wp rollsbar media validate
wp rollsbar media sync --dry-run --confirm-staging
wp rollsbar media sync --confirm-staging
```

`RollsBar_Client_Media` validates all assets, rows, source identities and existing attachments before media/product writes. It rejects missing assets, conflicting hashes/keys, wrong resolved IDs, ambiguous SKU/source identities and conflicting parent images. A lock serializes cooperating syncs. Failures do not trigger automatic retries or destructive rollback: inspect state first. An abandoned lock requires inspection before removal.

Each unique canonical binary has one attachment, including the two deferred assets. Shared photos reuse it across products. Pizza size rows target the existing variable parent, never per-size attachment copies. Attachment identity/provenance metadata:

- `_rollsbar_client_media_key`
- `_rollsbar_client_media_sha256`
- `_rollsbar_client_media_canon`
- `_rollsbar_client_media_source`

Products also store `_rollsbar_client_media_attachment_id`, key and canon version. A same-named upload is not identity evidence. Reuse checks actual original file SHA-256 and MIME as well as metadata. Existing wrong hashes fail safely. Repeat sync must report `created=0`, `assigned=0`, `reused=36`, `unchanged=45`. An accidental featured-image switch is reconciled on the next sync.

The shared theme resolver prefers the canonical client attachment for covered source IDs, even if a stale featured ID or legacy `_rollsbar_source_image` remains. Other products keep their existing featured/source/fallback behavior. Old Yandex metadata is retained as provenance. No mass deletion.

## Future deploys and rebuilds

1. Staging bootstrap copies the entire repo media canon into the installed plugin's `data/product-media/` directory. Package builds include it too.
2. `wp rollsbar catalog import` validates the canon, retains featured images, and reconciles canonical media **after products exist**. Limited five-product smoke imports skip provisioning while the required identities are incomplete.
3. Routine staging bootstrap reconciles media when the full catalog exists, including recovery from a fresh full-catalog database. Original ZIP/XLSX files are unnecessary at runtime.
4. Media-only release uses the existing `deploy-reg-ru-staging-wordpress.yml` workflow, operation `client-media`, restricted to `wordpress/checkout-visual-parity-2026-10-25`, exact staging host/environment and shared deployment concurrency. It performs full app-file hash checks, the protected backup gate, four media-related PHP file updates plus canon data, two syncs, catalog/business-data checks and real Chromium desktop/mobile acceptance. It never runs checkout work, business repair, or the broad bootstrap against live staging.
5. Application marker advances only after all tracked app files match the release, backend verification passes and browser acceptance succeeds. Workflow artifacts contain the backup receipt, 36 HTTP hash proofs, 45 product/attachment/DOM mappings per viewport and screenshots. A protected media release receipt also records staging phase and backup.

The staging backup gate verifies DB/uploads/manifest checksums and archives outside web root, retains protected snapshot `20261023T215945Z`, and bounds retention to six snapshots. Backup precedes staging site/media/database changes.

## Verification

```sh
php qa/visual/client-media-contract.php
python wordpress/tools/test_client_media_sources.py
python wordpress/deploy/test_client_media_release.py
```

The real importer/sync run in a deterministic Woo CRUD fixture: empty-state rebuild, known deferral, dry-run determinism, shared image deduplication, second-sync no-op, catalog re-import persistence, stale featured/Yandex precedence and rejection before writes for corrupt manifests/assets/identities. Source tests cover wrong archive checksums, missing/conflicting files and ambiguous/unknown products. Optional private-source reproduction:

```sh
python wordpress/tools/build_client_media_canon.py --source-dir PRIVATE_SOURCE_DIR --check
```

On staging, `verify-client-media.php` reads exact assignments and hashes without mutation. `client_media_browser.py` checks canonical full image HTTP bytes/MIME, all 45 displayed product image URLs and decoded images on desktop/mobile, all four new 21.10 assets and screenshots. Structural contract remains 118 canonical products, 13 variable parents, 26 variations, three hidden provisional upsells, 121 published product posts.

## Production status

**Not promoted. Production access=no, mutation=no, deploy=no.** Sync rejects production. A future explicit customer-authorized production promotion must supply its own reviewed safeguards. Checkout Final Direct Port is outside this Batch.

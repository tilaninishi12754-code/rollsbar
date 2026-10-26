# Client Product Media Canon — staging acceptance, 26 October 2026

**PASS — 57 APPLIED / 4 DEFERRED / 61 PRESERVED.**

Application release: `8383511f31d2520a4e348de6df2605c94abe68e2`.
[Verified staging workflow, run 40282972199](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40282972199), operation `client-media`, attempt 1: **success**. Production access=no, mutation=no, deploy=no. Checkout Final Direct Port was not started.

## Source and authority

Version `client-media-2026-10-21`. Repo source: `wordpress/data/product-media/client-2026-10-21/manifest.json` and 36 public website images. Raw ZIP/XLSX originals are preserved privately outside Git.

| Original archive | Bytes | SHA-256 |
| --- | ---: | --- |
| 19-10-2026_09-24-58.zip | 7550703 | 9ce332520d715225a527bde90b439aa9a306579415ed3d18ab18212e1889b531 |
| 21-10-2026_10-48-20.zip | 8280976 | 336150f653fc2247e92612fe3388a996449222b3bc17e2b351c97d804d5d00ef |

Both original checksums verified before mutation and again during canon build/check. Current 21.10 table: 61 photo rows / 47 names / 36 photos. Historical 19.10 table: 50 rows. Exactly 11 added, zero removed, missing=0, unused=0. Images: 1254 × 1254, 32 true WebP plus four byte-preserved PNG files renamed `.png` (Запеченный рис, Запеченные маменори, Огонек, Итальянский).

57 rows resolve to 45 explicit source IDs. Four rows (83–86) for **Охотничья / Салями**, sizes 30/50 см, remain `deferred_new_product_identity`. Their images are preserved and imported, unassigned. No products or source IDs invented. 34 detected non-media field differences remain private review-only evidence.

## Offline verification

- Real importer/media-sync PHP CRUD fixture: PASS, 23 rejection cases before product/media writes.
- Private-source builder tests: PASS, 6 cases, including wrong archive checksum, conflicting/missing images, unknown/ambiguous identities and nonfatal known deferral.
- Release/lifecycle tests: PASS, 3 cases; protected backup before writes, exact host/environment, only four media-related PHP paths deployable, canon included in bootstrap/package.
- Source reproduction (`--check`), all source/derived image hashes, MIME, dimensions and manifest cardinalities: PASS.
- Dry run deterministic; repeated sync creates no duplicates; shared photos use one attachment; catalog import preserves canonical assignments; accidental stale featured/Yandex image cannot win.
- Two independent empty Woo/media fixture rebuilds from repo catalog + canon: PASS, no original ZIP/XLSX runtime dependency.
- Live catalog import was not run: its non-media writes were outside this media-only staging operation. The actual importer persistence/rebuild behavior was verified in the deterministic fixture.

## Backup and live state

Fresh staging snapshot **20261026T065917Z** (26 October, **09:59:17 Moscow**), complete and verified **before site/media/database mutation**. Database/uploads/manifest SHA-256, gzip and tar validation: PASS. Stored outside web root. Protected snapshot **20261023T215945Z**: verified before and after, preserved. Retained snapshots: **6**.

| Sync | Created attachments | Reused | Assigned products | Already correct |
| --- | ---: | ---: | ---: | ---: |
| Initial dry run | 36 planned | 0 | 45 planned | 0 |
| First actual sync | 36 | 0 | 45 | 0 |
| Second actual sync | 0 | 36 | 0 | 45 |
| Final read-only sync plan | 0 | 36 | 0 | 45 |

All 36 unique assets are available. 34 assets serve the 45 resolved products; two assets await new product identity decisions. Shared images: six baked rolls, six baked mamenori, two baked rice products. Existing pizza size rows share parent attachment identity.

Before/after live Woo catalog contract: **118 canonical / 13 variable parents / 26 variations / 3 exact hidden provisional upsells / 121 published products**. Missing/duplicate/unexpected products=0, variation mismatches=0, blank variation attributes=0. Non-media business-data digest unchanged:
`f6739d6e2f493ddf8a258eb2a51c6bda0ed7ef20a59e16935f260b2ba8d46d8f`.
Checkout PHP/CSS/JS SHA-256 unchanged. Every tracked theme/plugin file matches application release. Verified application marker was advanced only after browser acceptance.

## Browser evidence reviewed

Real Chromium **156.0.8078.4**, desktop **1440 × 1000**, mobile **390 × 900**. All 36 original canonical HTTP responses: **200**, SHA-256 matches repo, correct MIME. All **45** mapped product cards per viewport: displayed URL matches exact canonical attachment, visible, decoded, positive natural dimensions, HTTP **200**, no legacy Yandex/ROLLS BAR fallback. Shared detail data also points to canon. Broken mapped images=**0**. Catalog DOM remains 118 main cards + 8 Hits representations.

All four new 21.10 images visibly confirmed on both viewports: **Запеченный рис**, **Запеченные маменори**, **Огонек**, **Итальянский**. Staging additionally opened and visually inspected in the user's in-app browser. All ten downloaded screenshots were opened and visually reviewed by Worker. Evidence JSON, logs and screenshots are preserved in persistent project storage; the GitHub artifact is `client-media-40282972199-1` (30-day retention).

### Reviewed screenshot checksums

| Screenshot | SHA-256 |
| --- | --- |
| desktop-homepage.png | df46e34287c6a2b180a55eaa463d0016e23ffe068495e7826060b0f1174fa048 |
| desktop-italyanskiy.png | 205bf5dc75a1cf6a2608ea95feabfef4e78813ae50063f654415f9aef0546ff1 |
| desktop-ogonek.png | e9c4634ed5bded00b1f099e9c58a0818c836cc1f807131f639c685faf91a1533 |
| desktop-baked-mamenori.png | d1057819324779cde0af93381911dac50baca244eff173bca4eda47b8f1f0082 |
| desktop-rice.png | 4a3a8da51e778fd8c8fa5fa99946391b579791ad49583020dcbaad72c48513b6 |
| mobile-homepage.png | 46154ed1c8f1d4f2e43bc48470f14ec54d66ee4aaf9d1f1a9963e001d7ab71de |
| mobile-italyanskiy.png | f2e352258519055f8965d90cd0af2029ad5d86851bb40e27a2d1d8df5085c916 |
| mobile-ogonek.png | f97843e0de347ebe49afed94a5a54c0e177ff8017619c3ddaf0a9fc412266ee1 |
| mobile-baked-mamenori.png | aae057c54b914a99f16404de8a0958c544d6792aecb93a374c9a9a8e78e80c3a |
| mobile-rice.png | b5d3e086e973c236bce1519eef3e2a85708c42d54b64a2b81276237024f4e0c5 |

## Durable behavior and production boundary

`wp rollsbar media sync --confirm-staging` validates repo assets, explicit source IDs/SKUs and actual attachment hashes. It serializes syncs, reuses attachments and restores accidental image switches. Client canon wins over legacy imagery for resolved IDs. Catalog import provisions media after identities exist; bootstrap and deploy packages include all repo media. Production sync is forbidden. Promotion requires a future explicit decision.

## Exact files changed in this Batch

The application commit changes 53 files; this acceptance-only documentation commit adds the 54th. No checkout or catalog business-data source changed.

```text
.github/workflows/build-wordpress-staging-package.yml
.github/workflows/deploy-reg-ru-staging-wordpress.yml
.github/workflows/wordpress-migration-static-gate.yml
qa/visual/client-media-contract.php
wordpress/data/product-media/client-2026-10-21/images/4-syra-chedder.webp
wordpress/data/product-media/client-2026-10-21/images/bonito.webp
wordpress/data/product-media/client-2026-10-21/images/byanka.webp
wordpress/data/product-media/client-2026-10-21/images/cezar.webp
wordpress/data/product-media/client-2026-10-21/images/chizzi.webp
wordpress/data/product-media/client-2026-10-21/images/chuka-roll.webp
wordpress/data/product-media/client-2026-10-21/images/cypochka.webp
wordpress/data/product-media/client-2026-10-21/images/derevenskaya.webp
wordpress/data/product-media/client-2026-10-21/images/filadelfiya-s-krevetkoy.webp
wordpress/data/product-media/client-2026-10-21/images/filadelfiya-s-ugrem.webp
wordpress/data/product-media/client-2026-10-21/images/filadelfiya.webp
wordpress/data/product-media/client-2026-10-21/images/gribnaya.webp
wordpress/data/product-media/client-2026-10-21/images/in-yan.webp
wordpress/data/product-media/client-2026-10-21/images/italyanskiy.png
wordpress/data/product-media/client-2026-10-21/images/kaliforniya-klassicheskaya.webp
wordpress/data/product-media/client-2026-10-21/images/kaliforniya-s-kopchennym-lososem.webp
wordpress/data/product-media/client-2026-10-21/images/kaliforniya-s-krabom.webp
wordpress/data/product-media/client-2026-10-21/images/kaliforniya-s-krevetkoy.webp
wordpress/data/product-media/client-2026-10-21/images/kani.webp
wordpress/data/product-media/client-2026-10-21/images/karbonara.webp
wordpress/data/product-media/client-2026-10-21/images/krasnyy-drakon.webp
wordpress/data/product-media/client-2026-10-21/images/mamenori-s-krabom.webp
wordpress/data/product-media/client-2026-10-21/images/mamenori-s-krevetkoy.webp
wordpress/data/product-media/client-2026-10-21/images/margarita.webp
wordpress/data/product-media/client-2026-10-21/images/myasnaya.webp
wordpress/data/product-media/client-2026-10-21/images/ogonek.png
wordpress/data/product-media/client-2026-10-21/images/ohotnichya.webp
wordpress/data/product-media/client-2026-10-21/images/pepperoni.webp
wordpress/data/product-media/client-2026-10-21/images/pikant.webp
wordpress/data/product-media/client-2026-10-21/images/ranch.webp
wordpress/data/product-media/client-2026-10-21/images/salyami.webp
wordpress/data/product-media/client-2026-10-21/images/surimi.webp
wordpress/data/product-media/client-2026-10-21/images/tempura-roll-s-lososem.webp
wordpress/data/product-media/client-2026-10-21/images/zapechennye-mamenori.png
wordpress/data/product-media/client-2026-10-21/images/zapechennye-roll.webp
wordpress/data/product-media/client-2026-10-21/images/zapechennyy-ris.png
wordpress/data/product-media/client-2026-10-21/manifest.json
wordpress/deploy/apply_client_media_staging.py
wordpress/deploy/bootstrap-staging.sh
wordpress/deploy/client_media_browser.py
wordpress/deploy/test_client_media_release.py
wordpress/deploy/verify-client-media.php
wordpress/docs/CLIENT_MEDIA_ACCEPTANCE_2026-10-26.md
wordpress/docs/CLIENT_PRODUCT_MEDIA_CANON.md
wordpress/tools/build_client_media_canon.py
wordpress/tools/test_client_media_sources.py
wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-catalog-importer.php
wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-client-media.php
wordpress/wp-content/plugins/rollsbar-core/rollsbar-core.php
wordpress/wp-content/themes/rollsbar-theme/functions.php
```

# Rolls Bar — Pre-WordPress Baseline Audit

Date: 2026-10-01
Status: PRE-MIGRATION AUDIT / FAST BROWSER PASS / FULL WEBKIT PASS PENDING
Approved baseline: `approved/site-2026-10-01`
Approved commit: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`

## Why this audit exists

The approved static site is the UX/design baseline, not proof that every technical behavior is production-ready.

This audit happens **before WordPress migration** so that:
- existing demo defects are not mistaken for WordPress regressions;
- approved behavior becomes an explicit regression contract;
- pending client inputs remain visible;
- migration can prove parity instead of relying on memory.

The audit is repeated at two later gates:
1. WordPress staging parity / integration audit.
2. Pre-production release audit.

## Baseline invariants

- Project No Loss register: 81 requirements.
- Catalog: 118 sellable cards / 131 source rows.
- Approved visual baseline stays frozen.
- Search remains available.
- One top utility strip: Акции / Работа / Доставка / Отзывы.
- Mobile sticky cart must hide while cart/checkout UI is open.
- Client may edit content in WordPress; client may not accidentally edit layout/grid/checkout logic.

## Findings

### P0 / migration blockers before production, but not before coding

1. **Delivery zones are still demo-only.**
   - current polygons are schematic;
   - real polygons, minimum order values, delivery fee/free-delivery thresholds are pending;
   - address → coordinates → polygon → minimum → shortfall cannot be production-final until inputs exist.

2. **Static checkout is not a production order system.**
   - the approved demo does not provide WooCommerce order persistence/admin order lifecycle;
   - production proof must happen on WordPress staging.

3. **Notifications are not production-proven.**
   - email/Telegram notifications need staging credentials and an end-to-end order test.

### P1 / defects or architecture debt already identified in approved/static layer

1. **Missing-image product modal regression.**
   - symptom: placeholder `ROLLS BAR` covered the entire modal and hid purchase controls;
   - root cause: absolute fallback inside media container without a positioning context;
   - static `main` hotfix exists; frozen approved branch is intentionally unchanged as evidence;
   - regression test required: missing media must never block add-to-cart.

2. **Late utility-strip render / flash.**
   - current approved demo uses layered runtime injection `demo.html → client-fixes.html → index.html`;
   - utility cards appear after JS/hydration instead of being in initial server HTML;
   - WordPress solution: render them directly in `front-page.php`, no runtime injection.

3. **Footer/logo fragility.**
   - static demo contains data-URI image layers and has shown a broken logo state in browser;
   - WordPress solution: Media Library + native Custom Logo, not embedded giant data URIs.

4. **External image dependency.**
   - catalog inventory: 63 cards currently have external HTTP image URLs; 55 have no direct `img` value and rely on local sprite/fallback behavior;
   - migration should import controlled product media into WordPress Media Library where rights/source allow;
   - deliberate placeholder must exist for missing media and must never block purchase controls.

5. **Static architecture is too layered for production.**
   - multiple iframe/runtime patch layers create cache/order/timing risk;
   - WordPress production should have one server-rendered theme + rollsbar-core behavior, not reproduce the demo layering.

### P3 / low-impact static findings

1. **Missing favicon in current static audit environment.**
   - browser audit logs contain `/favicon.ico → 404`;
   - does not block purchase/user flows;
   - WordPress solution: native Site Icon / Media Library.

### P2 / SEO and discoverability gaps in static baseline

Current source inspection:
- home and vacancies have meta descriptions;
- most legal/review/support pages have no meta description;
- no canonical links detected;
- no JSON-LD blocks detected;
- no `Restaurant/LocalBusiness` schema detected;
- WooCommerce Product schema cannot exist until products are migrated into WooCommerce.

These are migration tasks, not reasons to mutate the approved visual baseline.

## Pre-migration checks completed

- 81-requirement No Loss baseline exists.
- catalog invariant: 118 cards / 131 rows.
- no duplicate HTML IDs found in inspected current pages.
- no obvious missing local page targets among inspected live pages after accounting for catalog JS chunks.
- static missing-image root cause identified.
- approved baseline remains immutable.
- WordPress migration branch isolated from approved baseline.
- QA scaffold created before staging.
- repository secret-pattern search returned no matches for common API key/private key/password/client-secret/token patterns.
- fast real-browser pre-WordPress audit branch: `audit/pre-wordpress-2026-10-01`.
- fast Chrome run `36895390413`: **SUCCESS — 17 PASS / 1 expected desktop skip**.
- passed in real browser execution: 118/131 invariant, 4 utility cards, missing-image product modal, simple add-to-cart, checkout, +7 phone, no manual zone selector, address fields/map marker, mobile sticky-cart regression, search, cookie dismissal, core pages 2xx and initial-render page errors.
- WordPress migration static gate run `36896570281`: **SUCCESS** — PHP syntax, JS syntax, 118/131 catalog JSON invariant, approved-source pointer and secret-pattern scan.
- full Chromium + WebKit audit is still a separate pending evidence layer; do not call the complete cross-browser gate PASS until that run finishes.

## Audit layers for this project

### Gate A — PRE-WORDPRESS (now)
- requirement coverage
- catalog/data integrity
- known-bug inventory
- interaction inventory
- SEO/current metadata inventory
- mobile/desktop approved visuals
- pending-client-input register
- code/adversarial review

### Gate B — WORDPRESS STAGING
- import reconciliation
- product/cart/checkout/order persistence
- admin editability
- email/Telegram
- PHP/JS error log
- Playwright E2E
- visual regression
- accessibility
- performance
- SEO/schema/canonical/sitemap validation

### Gate C — PRE-PRODUCTION
- backup + rollback
- production-like test order
- payment/shipping/delivery behavior
- robots/indexability
- Search Console / sitemap handoff
- mobile/desktop acceptance
- Project No Loss 81/81 readback
- no P0/P1 regressions

## Current status

**PASS TO CONTINUE MIGRATION WITH KNOWN PENDING INPUTS.**

Evidence level at this checkpoint:
- source/static audit: PASS for migration continuation;
- fast real-browser desktop + mobile Chrome gate: PASS;
- WordPress candidate static gate: PASS;
- full WebKit/Safari-equivalent gate: PENDING;
- production integrations: PENDING STAGING.

This does not mean “production-ready”.
It means the approved baseline and current static hotfix layer are sufficiently inventoried to continue WordPress migration without silently treating known demo defects as intended production behavior.

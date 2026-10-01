# Rolls Bar — Independent Codex / Second-Agent Audit Brief

Date: 2026-10-01

## Purpose

Use Codex or another independent code-review agent as an **additional adversarial layer**.
It does not replace browser E2E, visual regression, data reconciliation, or manual acceptance.

## Read-only baseline

Repository: `tilaninishi12754-code/rollsbar`

Audit both:
1. `approved/site-2026-10-01` — approved visual/behavior baseline.
2. `wordpress/migration-2026-10-01` — migration candidate.

Do not modify either branch during the first audit pass.

## Required checks

1. Find functionality present in approved baseline but absent from WordPress migration.
2. Find functionality implemented differently in a way that can change client-visible behavior.
3. Check all 118 product cards / 131 source rows for migration accounting.
4. Check simple vs variable products and variant prices.
5. Inspect missing-image behavior.
6. Inspect search, mobile cart, cart, checkout, delivery/pickup.
7. Inspect custom admin editability:
   - product name
   - image
   - price
   - weight/volume
   - optional KBJU
   - phone/address
   - promo cards
   - vacancies
8. Inspect security:
   - escaping/sanitization
   - nonce/capability checks
   - secrets
   - external HTTP dependencies
   - direct file access guards
9. Inspect WordPress/WooCommerce conventions.
10. Inspect performance risks:
   - N+1 queries
   - unbounded loops
   - unnecessary external assets
   - render-blocking/custom runtime patching
11. Inspect SEO duplication:
   - title/meta
   - canonical
   - Product schema
   - Restaurant/LocalBusiness schema
   - sitemap/noindex rules for cart/checkout.
12. Find code paths where missing/empty content breaks purchase controls.
13. Look for mobile-only regressions.
14. Look for stale demo values accidentally presented as production truth.
15. Produce an adversarial “what could still go wrong after migration?” section.

## Output format

For every finding:
- ID
- severity: P0 / P1 / P2 / P3
- branch/file/line
- observed evidence
- expected behavior
- why it matters
- recommended fix
- whether it blocks migration, staging acceptance, or production

Then provide:
- coverage table
- no-loss gaps
- security gaps
- performance gaps
- SEO gaps
- confidence + unverified areas

Do not mark an item fixed without readback from the changed branch.

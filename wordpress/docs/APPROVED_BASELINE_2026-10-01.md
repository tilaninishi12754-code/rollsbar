# Rolls Bar — approved baseline / WordPress migration checkpoint

Date: 2026-10-01  
Status: APPROVED_SITE / WORDPRESS_MIGRATION_STARTED

## Approved source

- Git commit: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`
- Frozen branch: `approved/site-2026-10-01`
- Migration branch: `wordpress/migration-2026-10-01`
- Project No Loss baseline: 81 requirements
- Approved catalog: 118 sellable cards / 131 source rows
- GitHub Pages demo remains the visual/UX acceptance baseline until WordPress passes regression.

## Migration rule

The approved demo is not rewritten during WordPress work. WordPress is built in parallel and must prove parity before any production switch.

Required cycle:

`INGEST → REGISTER → IMPLEMENT → VERIFY → READBACK → CHECKPOINT`

No feature may silently disappear merely because WordPress/WooCommerce implements it differently.

## Known pending inputs that DO NOT block migration

1. Real delivery polygons.
2. Minimum order / delivery price / free-delivery threshold per zone.
3. Which address details are mandatory vs optional.
4. Final sauce list for Shrimp Tempura.
5. Final vacancy questionnaire wording.
6. Confirmation/correction of disputed tyahan rows / 942 pcs item.

Until these inputs arrive:
- no fake production delivery thresholds;
- no invented sauce choices;
- no invented vacancy wording;
- pending fields remain configurable.

## Production architecture

- WordPress: CMS/pages/admin.
- WooCommerce: products/cart/checkout/orders.
- `rollsbar-theme`: presentation only.
- `rollsbar-core`: delivery, checkout, notifications, integrations, project-specific behavior.
- Secrets never enter Git.
- Staging is mandatory before production.

## No-loss release gate

Before WordPress can replace the approved demo:
- all 81 requirement IDs accounted for;
- catalog reconciliation PASS;
- cart/checkout/order-admin PASS;
- mobile + desktop PASS;
- vacancies/reviews/legal pages PASS;
- search PASS;
- email/Telegram notifications PASS when credentials are available;
- delivery logic PASS once real zone data arrives;
- approved design parity readback completed.

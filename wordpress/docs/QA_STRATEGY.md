# Rolls Bar — QA / Regression Strategy

Date: 2026-10-01
Status: ACTIVE DURING WORDPRESS MIGRATION

## Goal

Do not discover regressions accidentally after launch.

Every WordPress migration step must preserve the approved Rolls Bar behavior and pass a layered QA gate before production.

## Source of truth

- Approved static branch: `approved/site-2026-10-01`
- Approved baseline commit: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`
- WordPress branch: `wordpress/migration-2026-10-01`
- Catalog invariant: 118 cards / 131 source rows
- Project No Loss: all 81 requirements remain accounted for

## Layer 1 — Data integrity

Must prove before and after every catalog migration:

- 118 sellable cards remain accounted for
- 131 source rows remain accounted for
- no silent product deletion
- no duplicate stable SKU
- simple vs variable product type preserved
- price preserved
- product title preserved
- category preserved
- image source either works or a deliberate placeholder is shown
- missing image never blocks add-to-cart
- pending Shrimp Tempura sauce options are not invented
- disputed tyahan data is not silently corrected

## Layer 2 — WordPress / WooCommerce code quality

Run on staging/development:

- WordPress Coding Standards / PHP_CodeSniffer
- Plugin Check against `rollsbar-core`
- Theme Check against `rollsbar-theme`
- Query Monitor during exploratory testing
- PHP error log must be clean for tested flows
- no secrets in Git
- staging before production

Plugin Check is advisory, not an absolute proof. Review each finding.

## Layer 3 — Automated browser E2E (Playwright)

Minimum desktop + iPhone/WebKit scenarios:

1. Home page renders.
2. Search opens and returns products.
3. Product with image opens and remains addable.
4. Product without image shows placeholder and remains addable.
5. Simple product can be added to cart.
6. Variable product requires/accepts a variant.
7. Cart quantity + / - works.
8. Mobile sticky cart does not cover cart/checkout controls.
9. Checkout opens.
10. Phone starts with +7.
11. Delivery / pickup switch works.
12. Address fields render.
13. Required/optional field rules match the latest client decision.
14. Delivery map renders.
15. When real zone data exists: address -> coordinates -> zone -> minimum -> shortfall.
16. Outside real zones -> pickup only.
17. Vacancy page renders and editable vacancies appear.
18. Reviews/legal/contact pages return 200.
19. No uncaught page errors.
20. No broken product images without fallback.

## Layer 4 — Visual regression

Use Playwright `toHaveScreenshot()` on stable interface regions:

- desktop header + promo cards
- desktop product grid
- mobile header + promo strip
- mobile product cards
- cart
- checkout
- vacancies

Generate baselines only from an explicitly approved staging build.
Never auto-accept screenshot changes without review.

## Layer 5 — Accessibility

Run `@axe-core/playwright` on:

- home
- product
- cart
- checkout
- vacancies

Automated accessibility checks are only a first pass. Manual keyboard/mobile checks remain required.

## Layer 6 — Performance

Run Lighthouse/Lighthouse CI on staging:

- Home
- Product
- Cart
- Checkout (where technically measurable)

Track regressions rather than chasing an arbitrary perfect score.

## Layer 7 — Manual acceptance

Test on:

- current desktop Chrome
- current desktop Safari/WebKit equivalent
- iPhone viewport / WebKit
- Android viewport / Chromium

Verify:

- visual parity with approved design
- no overlaps
- long product names
- missing photos
- slow image loading
- empty optional fields
- validation messages
- map interaction
- payment and order messaging
- admin editing without layout damage

## Known regression found 2026-10-01

### Missing-image product detail overlay

Symptom:
A product with no photo opened a large `ROLLS BAR` placeholder over the entire product modal, hiding title/price/add-to-cart.

Root cause:
`.product-fallback { position:absolute; inset:0 }` was rendered inside a modal media container that was not positioned. The fallback therefore positioned itself against the modal panel.

Static hotfix:
Make the media container `position:relative` and make the fallback non-interactive.

WordPress rule:
Use WooCommerce placeholder/media fallback. Missing media must never affect purchase controls.

## Release gate

Production switch is blocked unless:

- data integrity PASS
- browser E2E PASS
- visual regression reviewed
- PHP errors reviewed
- Plugin Check / Theme Check reviewed
- mobile checkout PASS
- admin editability PASS
- backup/rollback ready
- Project No Loss readback PASS

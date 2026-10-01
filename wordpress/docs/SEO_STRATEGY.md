# Rolls Bar — SEO / Discoverability Strategy

Date: 2026-10-01
Status: MIGRATION DESIGN DECISION

## Decision

Do **not** build a parallel home-grown SEO framework inside `rollsbar-core`.

Use:
- WordPress/WooCommerce as the canonical content/product layer;
- one SEO plugin for editable titles, descriptions, canonicals, robots, XML sitemaps and social metadata;
- WooCommerce core product data/schema as the default product source of truth;
- one controlled LocalBusiness/Restaurant schema owner;
- Search Console + Rich Results Test after staging.

Do not run two SEO plugins or two competing Product-schema generators.

## Best-fit plugin for Rolls Bar

Default candidate: **SEOPress**.

Reason:
- simple client-facing title/meta UI;
- free tier covers titles/meta and XML sitemaps;
- PRO adds WooCommerce SEO, Local SEO and schema if we later need those features;
- avoids putting SEO fields into custom theme code;
- can be replaced without redesigning the theme.

This is a project best-fit choice, not a universal statement that SEOPress is objectively the best WordPress SEO plugin.

## Structured data ownership

### Products
WooCommerce already generates core Product structured data.

Rule:
- keep WooCommerce as canonical product data;
- do not add a second Product JSON-LD implementation in `rollsbar-core`;
- only enrich Product schema through the chosen SEO/plugin layer when there is a verified need;
- validate variable products, price/availability and visible content consistency.

### Local business
For the business entity use the most specific applicable schema type: **Restaurant** (subtype of LocalBusiness).

Populate only verified values:
- legal/public name
- URL
- address
- phone
- geo
- opening hours
- price range if confirmed
- menu URL where appropriate
- logo/image

Do not invent opening hours, price range or coordinates.

### Pages
Editable per page/product:
- SEO title
- meta description
- canonical when needed
- robots
- Open Graph/social image

### Indexation policy
Normally index:
- home
- useful category/product pages
- delivery/payment
- vacancies if intended public
- reviews if useful/original
- legal pages as appropriate

Normally noindex transactional/utility surfaces where appropriate:
- cart
- checkout
- account/internal search result surfaces

Final policy must be verified on staging against WooCommerce/plugin-generated robots.

## Migration checklist

1. Preserve human-readable slugs.
2. Define canonical domain before production.
3. Generate XML sitemap.
4. Verify products/categories included intentionally.
5. Verify cart/checkout noindex behavior.
6. Add Restaurant/LocalBusiness only once.
7. Validate product pages in Google Rich Results Test.
8. Add Search Console after production domain is ready.
9. Submit sitemap.
10. Monitor crawl/indexing and structured-data errors after launch.
11. Add redirects for any URL changed during migration.
12. Keep SEO metadata editable for the client without exposing layout code.

## Review triggers

Re-check this decision when:
- major WooCommerce SEO/schema behavior changes;
- chosen SEO plugin changes;
- Google structured-data requirements change;
- product feed / Merchant Center is introduced;
- multi-location business model appears.

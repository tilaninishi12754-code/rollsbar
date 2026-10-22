# Batch 15 — Website Footer / Contacts only

Status: **PASS — full B15 local deterministic acceptance**. Local deterministic acceptance only.

## Preflight

- First Git command: `git rev-parse --show-toplevel` → `C:/AI/Rolls Bar Project`.
- Branch: `wordpress/visual-parity-2026-10-14`.
- Starting HEAD: `8487db10b1f250dbed280f10b821c8335da198c9`; initial tree CLEAN.
- Approved ref: `refs/remotes/origin/approved/site-2026-10-01`.
- Approved SHA: `a5e524392abcf89ffd5ace2a18218a6b59ed3b61`.
- Initial normal gate: **150 passed / 18 explicit skips** before application edits.
- All **258** starting PNG hashes verified against their manifest before edits.
- npm unavailable; used the unchanged package script `node qa/visual/run.mjs test`
  through the existing bundled Node executable. No package installation/change.

## Approved footer/contact contract

Evidence below is immutable approved Git source, without checkout:

- `index.html:646–653`: contacts follow the delivery section and end main content.
  Three cards: Rolls Bar/address; two telephone links; VK and Telegram text links.
  Address is plain text, not a map/location link. No hours or social icons.
- `index.html:84–99,138–147` and `client-fixes.html:24,66–70,142–158,177–181`:
  contacts use the approved shell, 62px top padding, 34px heading/22px lower gap;
  three equal columns with 18px gaps above 1050px, one column through 1050px.
  Cards have 25px padding, 1px #ececec border, 30px radius, white surface, no shadow.
  At/below 700px: 44px top padding, 29px heading/15px lower gap, 14px shell sides.
- `index.html:655–675`: footer follows contacts, logo/home-top link, delivery copy,
  seller identity/phone and navigation. No copyright line, business hours or new CTA.
- `index.html:96–99,349`, `client-fixes.html:31,142–158`, `demo.html:99–103`:
  72px top gap, #171717 background, no border/radius/shadow; 34px upper/100px lower
  padding, 30px flex gap. Logo box 160×52px. Paragraphs 12px/18px, #9d9d9d;
  seller #b9b9bb. Navigation wraps with 8px gaps, #282828 pills, 12px radius,
  10px/12px padding, 12px bold text. Through 700px the flex layout stacks,
  logo is 101×34px, footer lower padding is 145px; existing body bottom padding 86px.
- `client-fixes.html:242–244`: append the additional “Отзывы клиентов” link;
  both this and the original “Отзывы” remain. Eleven navigation pills in total.
- `index.html:649–650`: primary `tel:+79786882288`, secondary `tel:+79786990399`;
  VK `https://vk.ru/rollsbar82`, Telegram `https://telegram.me/rollsbar82`.
  Social links use `_blank` + `noreferrer` (including implicit noopener protection).
  Footer menu is `#sets`, brand is `#top`; legal/reviews/jobs links use `_top`.
- Native hover/focus behavior is retained, with no invented hover backgrounds.

The current delivery section above contacts remains deferred and unchanged. B15
compares contact/footer relative geometry, including the actual 72px intervening
gap; it does not claim whole-page absolute-position/final parity.

## Data source and editability

- `RollsBar_Settings::all/get` → `rollsbar_setting` → actual footer template uses
  the existing `rollsbar_settings` option keys: `phone_display`, `phone_href`,
  `city`, `address`, `vk_url`, `telegram_url`. No duplicate defaults added.
- Seller phone formats that same editable display phone with the approved
  parentheses. Address uses edited city/address. Delivery copy uses edited city,
  retaining the approved grammatical form for the default city.
- Approved secondary phone has no existing canonical settings field; its exact
  approved value is retained. No admin field or settings/database mutation.
- Logo uses existing WordPress `custom_logo`, otherwise the existing local
  `assets/images/header-logo.png`; no new brand asset or parallel logo setting.
- Seller identity is the approved literal legal text, corroborated by current
  `requisites.html:18–22` and `wordpress/deploy/verify-staging-legal-pages.php:62`.
  There is no structured seller-identity option in the current settings source.
- Legal destinations use existing WordPress routes from
  `wordpress/deploy/provision-legal-pages.php:18–28`; reviews/jobs reuse the
  existing header destinations `/otzyvy/` and `/rabota-v-rolls-bar/`.
- **Approved-vs-current business-data conflicts: none found in project sources.**
  No live client/staging/production DB was queried or changed.

## Implementation

Application files:

- `wordpress/wp-content/themes/rollsbar-theme/footer.php`: homepage contacts before
  `</main>`, shared site-wide footer after main. Existing cart controls/drawer tail
  preserved. Non-homepage brand/menu links go to homepage anchors.
- `wordpress/wp-content/themes/rollsbar-theme/assets/css/app.css`: scoped contacts
  and website-footer presentation only. Long values wrap locally; no page-wide
  overflow suppression or catalog/card/layout refactor.
- `wordpress/wp-content/themes/rollsbar-theme/assets/js/app.js`: two existing
  Contacts actions now reach `#contacts`. Existing lifecycle/state systems reused.

QA files: `gate.spec.mjs`, `b15-footer-helpers.mjs`, `b15-contact-contract.php`,
`preview.php` (real settings with in-memory option/theme-mod overrides), `run.mjs`
(B15 targeting only), `accepted-exceptions.json`, baseline manifest, this report,
and ten B15 PNGs. Package files and core plugin/settings source unchanged.

## Functional / static QA

- Targeted B15 browser suite: **8/8 PASS** before final full run.
- All contact text, both tel destinations, social protocols/targets/rel, all footer
  labels/order and WordPress destinations; native hover presentation vs approved.
- Native Tab traversal and visible focus outlines across contacts/footer; Enter
  activates brand/top and menu anchor. Header Contacts action reaches new section.
- Real page bottom reached at all eight widths. Last footer link is in viewport;
  every footer link remains above visible fixed cart/order controls, including
  the existing 701px fallback cart. Capture-only styles are removed first.
- Drawer open/Escape close leaves no body scroll lock or inert elements.
- Long realistic address/phone and unbroken 120-character values / long link label
  remain contained with zero page/content overflow.
- Real settings + real template: **22 PHP assertions PASS**; changed phone/city/
  address/social values, no stale defaults, escaping, empty socials, custom logo,
  homepage-only contacts, non-homepage anchor destinations. In-memory only, no DB.
- B11 PHP: **133 assertions PASS**. B12 PHP: **812 assertions PASS**, 148 line paths.
- Existing populated-drawer overflow helper: all eight widths PASS with 15 lines,
  internal vertical scrolling intact, selector/action/header/mobile overflow zero.
- PHP lint (footer and QA PHP), application/helper/test/runner Node syntax,
  `git diff --check`: PASS.
- **Application JS errors/warnings: 0** in B15. External-resource network failures
  are filtered by the established local harness, not treated as application JS.

## Visual Gate and overflow

- New expected screenshots generated only with current rendering disabled, from
  immutable approved `demo.html > client-fixes.html > index.html`.
- **258/258 old PNG/hash values preserved exactly**, checked independently against
  the starting-HEAD manifest. All 268 final manifest hashes valid.
- New screenshots: **10** — eight complete footers, contacts at 1440/320.
- Final screenshot total: **268**. B15 adds eight normal-mode tests, no new skips.
- Final full normal gate: **158 passed / 18 explicit skips** (176 tests). No normal-mode snapshot updates.

All widths use height 900, DPR 1. Geometry includes both complete components and
all links/cards; a separate populated drawer run verifies existing control areas.

| Width | Page | Footer | Footer/contact content & links | Header/search | Mobile cart/order | Drawer/content | Card action | Selector |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1440 | 0px | 0px | 0px | 0px | 0px | 0px | 0px | 0px |
| 1051 | 0px | 0px | 0px | 0px | 0px | 0px | 0px | 0px |
| 1050 | 0px | 0px | 0px | 0px | 0px | 0px | 0px | 0px |
| 1024 | 0px | 0px | 0px | 0px | 0px | 0px | 0px | 0px |
| 701 | 0px | 0px | 0px | 0px | 0px | 0px | 0px | 0px |
| 700 | 0px | 0px | 0px | 0px | 0px | 0px | 0px | 0px |
| 390 | 0px | 0px | 0px | 0px | 0px | 0px | 0px | 0px |
| 320 | 0px | 0px | 0px | 0px | 0px | 0px | 0px | 0px |

Narrow documented capture exceptions, no global tolerance change:

1. Approved `index.html:658` embeds a footer WebP that fails to decode. Browser
   oracle explicitly verifies `complete && naturalWidth===0`; current logo must
   decode successfully. Retain the existing editable/valid brand source with the existing valid source. Only the exact logo rectangle is masked
   #171717: **160×52 = 8,320px** desktop / **101×34 = 3,434px** mobile. Geometry
   and all text/links remain compared; no footer-wide mask or pixel allowance.
2. Unrelated floating `.client-back-top`, `.back-to-menu-top`, `.mobile-actions`
   and existing B13 `.rollsbar-mobile-cart` are hidden only for component captures.
   Styles are removed before keyboard/bottom/cart/overflow checks; B13 rendering
   itself is unchanged. No new back-to-top/phone-control work in B15.
3. Component screenshot origins are rounded to whole CSS pixels in both sources
   to isolate fractional placement from the preceding deferred page content.
   Actual geometry compares the unmodified components. No pixel tolerance added.

## Preservation / deferred work

- B1–B14 protected baseline values retained. B6B product-card footer/action-row
  parity remains **OPEN**; its source, exceptions and acceptance are not modified.
- Canonical public catalog **118**, DOM card representations **126**, Hits **8**,
  variable parents **13** / variations **26**, WOK choices **18**, confirmed shrimp
  choices **3** preserved. Three hidden upsells remain outside main catalog/search.
- Upsell 20 RUB seed remains **PROVISIONAL**, outside B15. Existing production
  prerequisites remain owner confirmation of upsell pricing and environment-specific
  native Woo provisioning/verification. Local adapters are not deployed-Woo proof.
- B16 **not started**. No delivery/checkout/payment/acquiring/notifications/analytics/
  admin UX/product cleanup work. No staging/production access or DB writes.
- No checkout/reset/merge/rebase/push/deploy. AGENTS.md and skills untouched.
- One local B15 commit only after final acceptance; SHA/final clean-tree evidence
  are returned in the completion response (avoids a self-referential commit SHA).

Next: return report to Coordinator. Do not start B16 or B6B automatically.

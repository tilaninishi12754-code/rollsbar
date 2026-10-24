#!/usr/bin/env python3
"""Browser Gate B for the real RollsBar REG.RU staging site.

Covers desktop and mobile customer journeys without placing a real order:
home -> add product -> cart -> checkout, checkout field behavior, delivery table,
manual-zone absence, trusted HTTPS, ruble pricing, and the historical mobile
cart-overlay bug.
"""
from __future__ import annotations

import re
import json
from pathlib import Path
from urllib.parse import parse_qs
from catalog_browser_contract import verify_catalog
import sys
from dataclasses import dataclass
from typing import Iterable

from playwright.sync_api import Browser, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

BASE = "https://staging.rollsbar.ru"


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ").strip())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS  {message}")


def response_ok(response, label: str) -> None:
    require(response is not None, f"{label}: navigation returned a response")
    require(200 <= response.status < 400, f"{label}: HTTP {response.status}")
    require(response.url.startswith("https://"), f"{label}: HTTPS URL")


def first_visible(page: Page, selectors: Iterable[str]):
    for selector in selectors:
        loc = page.locator(selector)
        for i in range(loc.count()):
            candidate = loc.nth(i)
            if candidate.is_visible():
                return candidate
    return None


def store_cart_state(page: Page) -> dict:
    return page.evaluate(
        """async () => {
          const r = await fetch('/wp-json/wc/store/v1/cart', {credentials:'same-origin'});
          const j = await r.json();
          return {
            status: r.status,
            names: (j.items || []).map(i => i.name),
            itemsCount: j.items_count || 0,
            currencyCode: j.totals ? j.totals.currency_code : '',
            currencySymbol: j.totals ? j.totals.currency_symbol : ''
          };
        }"""
    )


def assert_catalog(page: Page) -> None:
    rows = page.locator('.rollsbar-product-card').evaluate_all("els => els.map(e => ({id:e.dataset.rollsbarSourceId, hit:!!e.closest('#hits')}))")
    canonical = [p['id'] for p in json.loads((Path(__file__).resolve().parents[1] / 'data/catalog.json').read_text(encoding='utf-8'))['products']]
    verify_catalog([r['id'] for r in rows if not r['hit']], [r['id'] for r in rows if r['hit']], [r['id'] for r in rows], canonical)
    search = json.loads(page.locator('#rollsbarProductSearchData').text_content())
    require(len(search) == 118 and {r['id'] for r in search} == set(canonical), 'search exposes exactly 118 public identities; hidden upsells excluded')
    print('PASS  live catalog: 118 main / 126 representations / 8 Hits / 118 unique identities')


def assert_layout(page: Page) -> None:
    for selector in ('header', '.rollsbar-category-nav', '.rollsbar-utilities', '.rollsbar-catalog-section', '#delivery', '#contacts', 'footer.rollsbar-footer'):
        require(page.locator(selector).first.is_visible(), 'homepage section rendered: ' + selector)
    overflow = page.evaluate('Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth')
    require(overflow <= 1, f'no horizontal overflow ({overflow}px)')


def add_first_simple_product(page: Page) -> str:
    assert_catalog(page)
    button = page.locator('.rollsbar-product-card [data-rollsbar-cart-delta="1"]').first
    button.wait_for(state='visible')
    card = button.locator("xpath=ancestor::article[contains(@class,'rollsbar-product-card')]")
    name = norm(card.locator('h3').inner_text())
    with page.expect_response(lambda r: 'wc-ajax=rollsbar_cart' in r.url and r.request.method == 'POST') as response:
        button.click()
    require(response.value.ok and response.value.json().get('success'), 'real native Woo cart add succeeds')
    state = store_cart_state(page)
    require(state.get('status') == 200 and name in state.get('names', []), 'Store API contains simple product added through current UI')
    return name


def assert_delivery_table(page: Page) -> None:
    # Accepted B15 renders a schematic map and conditions, not the legacy tier list.
    text = norm(page.locator('#delivery').inner_text())
    for fragment in ('Доставка и оплата', 'Самовывоз', 'после утверждения точных границ', 'при получении'):
        require(fragment in text, 'current delivery disclosure: ' + fragment)


def assert_shrimp(page: Page) -> None:
    page.locator('[data-rollsbar-source-id="shrimp-tempura"] [data-rollsbar-selection-open]').first.click()
    modal = page.locator('#rollsbarProductDetails')
    control = modal.locator('select')
    require(control.count() == 1, 'shrimp has exactly one option group')
    require(control.locator('option').all_text_contents() == ['чесночный', 'сырный', 'томатный'], 'shrimp UI exposes exactly the three approved choices')
    control.select_option('сырный')
    with page.expect_response(lambda r: 'wc-ajax=rollsbar_cart' in r.url and r.request.method == 'POST') as response:
        modal.locator('.rollsbar-product-options__add').click()
    r = response.value
    payload = json.loads(parse_qs(r.request.post_data)['request'][0])
    require(payload.get('source_id') == 'shrimp-tempura' and payload.get('options') == ['сырный'], 'real add request preserves selected shrimp sauce')
    result = r.json()
    require(r.ok and result.get('success'), 'shrimp add-to-cart succeeds')
    lines = [line for line in result['data']['lines'] if line['source_id'] == 'shrimp-tempura']
    require(len(lines) == 1 and lines[0]['options'] == [{'label':'Соус','value':'сырный'}], 'native Woo cart response preserves shrimp metadata')
    modal.wait_for(state='hidden')
    items = page.evaluate("async () => (await (await fetch('/wp-json/wc/store/v1/cart', {credentials:'same-origin'})).json()).items")
    require(any(any(d.get('key') == 'Соус' and d.get('value') == 'сырный' for d in i.get('item_data', [])) for i in items), 'Store API independently exposes selected shrimp option metadata')


def clean_test_cart(page: Page) -> None:
    result = page.evaluate("""async () => {
      const r = await fetch('/wp-json/wc/store/v1/cart', {credentials:'same-origin'});
      const nonce = r.headers.get('Nonce');
      if (!nonce) throw Error('Missing cart nonce for test-session cleanup');
      const deleted = await fetch('/wp-json/wc/store/v1/cart/items', {method:'DELETE',credentials:'same-origin',headers:{Nonce:nonce}});
      return {status:deleted.status, cart:await deleted.json()};
    }""")
    require(result['status'] == 200 and result['cart']['items_count'] == 0, 'only isolated browser test cart cleaned')


def assert_public_routes(page: Page) -> None:
    routes = {'/otzyvy/':'.rb-reviews-page', '/rabota-v-rolls-bar/':'.rb-career-hero'}
    for slug in ('dostavka-i-oplata','rekvizity-prodavca','publichnaya-oferta','oplata-i-vozvrat','politika-konfidencialnosti','cookies','bezopasnost-onlajn-oplaty','pravovaya-informaciya'):
        routes['/' + slug + '/'] = '.rollsbar-legal-page'
    for route, selector in routes.items():
        response_ok(page.goto(BASE + route, wait_until='domcontentloaded'), route)
        require(page.locator(selector).is_visible(), route + ': intended page template, no generic fallback')


def assert_cart(page: Page, product_name: str) -> None:
    response = page.goto(BASE + "/cart/", wait_until="domcontentloaded")
    response_ok(response, "cart")

    state = store_cart_state(page)
    require(state.get("status") == 200, "Store API cart remains reachable after cart navigation")
    require(product_name in state.get("names", []), f"cart session persists added product: {product_name}")
    require(state.get("currencyCode") == "RUB", "WooCommerce cart currency is RUB")
    require(state.get("currencySymbol") in ("₽", "руб.", "руб"), "WooCommerce cart exposes a ruble symbol")

    row = page.locator(".wc-block-cart-items__row").filter(has_text=product_name).first
    try:
        row.wait_for(state="visible", timeout=10000)
    except PlaywrightTimeoutError:
        # Keep the final body assertion for diagnostics, but fail on actual
        # user-visible hydration rather than on an arbitrary fixed delay.
        body = norm(page.locator("body").inner_text())
        raise AssertionError(f"hydrated cart row not visible for {product_name}; body={body[:900]}")

    require(product_name in norm(row.inner_text()), f"cart visibly renders added product: {product_name}")
    cart_text = norm(page.locator(".wc-block-cart").inner_text())
    require("₽" in cart_text, "cart visibly renders ruble prices")
    require("$" not in cart_text, "cart does not render dollar prices")

    proceed = first_visible(
        page,
        (
            ".wc-block-cart__submit-button",
            "a.checkout-button",
            "a[href*='/checkout']",
            "a[href*='checkout']",
        ),
    )
    require(proceed is not None, "cart has a visible proceed-to-checkout control")


def input_meta(page: Page):
    return page.locator("input, select, textarea").evaluate_all(
        """els => els.map(el => ({
          tag: el.tagName.toLowerCase(),
          type: (el.getAttribute('type') || '').toLowerCase(),
          name: (el.getAttribute('name') || '').toLowerCase(),
          id: (el.id || '').toLowerCase(),
          aria: (el.getAttribute('aria-label') || '').toLowerCase(),
          placeholder: (el.getAttribute('placeholder') || '').toLowerCase()
        }))"""
    )


def assert_checkout(page: Page) -> None:
    response = page.goto(BASE + "/checkout/", wait_until="domcontentloaded")
    response_ok(response, "checkout")
    page.wait_for_timeout(2200)
    body = norm(page.locator("body").inner_text())

    for label in ("Подъезд", "Код двери / домофона", "Этаж", "Квартира / офис"):
        require(label in body, f"checkout shows additional field label: {label}")

    phone = first_visible(
        page,
        (
            "input[type='tel']",
            "input[autocomplete='tel']",
            "input[name*='phone' i]",
            "input[id*='phone' i]",
        ),
    )
    require(phone is not None, "checkout has a visible phone input")
    phone.focus()
    page.wait_for_timeout(250)
    require(phone.input_value().strip().startswith("+7"), "empty checkout phone is prefilled with +7")
    phone.fill("89781234567")
    phone.blur()
    page.wait_for_timeout(300)
    require(phone.input_value().strip().startswith("+7"), "phone starting with 8 normalizes to +7 on blur")

    bad_zone_controls = []
    for item in input_meta(page):
        hay = " ".join(str(item.get(k, "")) for k in ("name", "id", "aria", "placeholder"))
        if "delivery_zone" in hay or "delivery-zone" in hay or "зона доставки" in hay or "выберите зону" in hay:
            bad_zone_controls.append(item)
    require(not bad_zone_controls, "checkout has no manual delivery-zone input/select")

    pickup_present = "Самовывоз" in body or "Local pickup" in body or "Pickup" in body
    require(pickup_present, "native Local Pickup is visible in checkout")


def assert_no_mobile_overlay(page: Page) -> None:
    proceed = first_visible(
        page,
        (
            ".wc-block-cart__submit-button",
            "a.checkout-button",
            "a[href*='/checkout']",
            "a[href*='checkout']",
        ),
    )
    require(proceed is not None, "mobile cart has visible checkout control")
    pbox = proceed.bounding_box()
    require(pbox is not None, "mobile checkout control has a rendered bounding box")

    overlays = page.locator("text=Перейти в корзину")
    for i in range(overlays.count()):
        el = overlays.nth(i)
        if not el.is_visible():
            continue
        info = el.evaluate(
            """el => {
              const s = getComputedStyle(el);
              const r = el.getBoundingClientRect();
              return {position:s.position, left:r.left, top:r.top, right:r.right, bottom:r.bottom};
            }"""
        )
        if info["position"] not in ("fixed", "sticky"):
            continue
        overlaps = not (
            info["right"] <= pbox["x"]
            or info["left"] >= pbox["x"] + pbox["width"]
            or info["bottom"] <= pbox["y"]
            or info["top"] >= pbox["y"] + pbox["height"]
        )
        require(not overlaps, "mobile 'Перейти в корзину' overlay does not cover checkout button")
    print("PASS  historical mobile sticky-cart overlap regression absent")


@dataclass
class RunResult:
    page_errors: list[str]


def run_desktop(browser: Browser) -> RunResult:
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="ru-RU")
    ctx.route('**/*', lambda route: route.abort() if route.request.method == 'POST' and ('/wc/store/v1/checkout' in route.request.url or 'wc-ajax=checkout' in route.request.url) else route.continue_())
    page = ctx.new_page()
    page_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    response = page.goto(BASE + "/", wait_until="domcontentloaded")
    response_ok(response, "desktop home")
    page.wait_for_timeout(1000)
    assert_delivery_table(page)
    assert_layout(page)
    product_name = add_first_simple_product(page)
    assert_shrimp(page)
    assert_cart(page, product_name)
    assert_checkout(page)
    clean_test_cart(page)
    assert_public_routes(page)
    require(not page_errors, f"desktop has no uncaught page JS errors (got {page_errors})")
    ctx.close()
    return RunResult(page_errors)


def run_mobile(browser: Browser) -> RunResult:
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
        device_scale_factor=3,
        locale="ru-RU",
    )
    ctx.route('**/*', lambda route: route.abort() if route.request.method == 'POST' and ('/wc/store/v1/checkout' in route.request.url or 'wc-ajax=checkout' in route.request.url) else route.continue_())
    page = ctx.new_page()
    page_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    response = page.goto(BASE + "/", wait_until="domcontentloaded")
    response_ok(response, "mobile home")
    page.wait_for_timeout(1000)
    assert_layout(page)
    assert_delivery_table(page)
    product_name = add_first_simple_product(page)
    assert_shrimp(page)
    assert_cart(page, product_name)
    assert_no_mobile_overlay(page)
    assert_checkout(page)
    clean_test_cart(page)
    assert_public_routes(page)
    require(not page_errors, f"mobile has no uncaught page JS errors (got {page_errors})")
    ctx.close()
    return RunResult(page_errors)


def main() -> int:
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                run_desktop(browser)
                run_mobile(browser)
            finally:
                browser.close()
        print("BROWSER GATE B PASS")
        return 0
    except Exception as exc:
        print(f"BROWSER GATE B FAIL: {exc.__class__.__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

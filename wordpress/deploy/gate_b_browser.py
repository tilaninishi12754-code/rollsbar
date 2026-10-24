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
import time
from contextlib import contextmanager
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


def store_cart_state(page: Page, timeout_ms: int = 5000) -> dict:
    return page.evaluate(
        """async timeout => {
          const r = await fetch('/wp-json/wc/store/v1/cart', {credentials:'same-origin', signal:AbortSignal.timeout(timeout)});
          const j = await r.json();
          return {
            status: r.status,
            items: (j.items || []).map(i => ({id:i.id, key:i.key, name:i.name})),
            names: (j.items || []).map(i => i.name),
            itemsCount: j.items_count || 0,
            currencyCode: j.totals ? j.totals.currency_code : '',
            currencySymbol: j.totals ? j.totals.currency_symbol : ''
          };
        }""", timeout_ms
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


def is_cart_add_response(response, source_id: str, product_id: int) -> bool:
    if 'wc-ajax=rollsbar_cart' not in response.url or response.request.method != 'POST':
        return False
    try:
        request = json.loads(parse_qs(response.request.post_data or '')['request'][0])
    except (KeyError, ValueError, IndexError):
        return False
    return (request.get('operation') == 'add' and request.get('source_id') == source_id
            and request.get('product_id') == product_id)


def add_first_simple_product(page: Page) -> str:
    assert_catalog(page)
    button = page.locator('.rollsbar-product-card [data-rollsbar-cart-delta="1"]').first
    button.wait_for(state='visible')
    card = button.locator("xpath=ancestor::article[contains(@class,'rollsbar-product-card')]")
    name = norm(card.locator('h3').inner_text())
    source_id = card.get_attribute('data-rollsbar-source-id')
    product_id = json.loads(page.locator('#rollsbarProductDetailsData').text_content())[source_id]['woo_id']
    with page.expect_response(lambda r: is_cart_add_response(r, source_id, product_id)) as response:
        button.click()
    r = response.value
    result = r.json()
    request = json.loads(parse_qs(r.request.post_data)['request'][0])
    lines = [line for line in result.get('data', {}).get('lines', []) if line.get('source_id') == source_id]
    diagnostic = {'ajax_status': r.status, 'ajax_success': result.get('success'), 'operation': request.get('operation'),
                  'source_id': source_id, 'product_id': request.get('product_id'), 'name': name,
                  'lines': [{k: line.get(k) for k in ('key', 'source_id', 'name', 'quantity')} for line in lines],
                  'url': page.url, 'origin': page.evaluate('location.origin'),
                  'cookie_names': sorted({c['name'] for c in page.context.cookies(BASE)})}
    print('INFO add=' + json.dumps(diagnostic, ensure_ascii=False))
    require(r.ok and result.get('success'), 'real native Woo cart add succeeds')
    require(request.get('source_id') == source_id and len(lines) == 1, 'AJAX cart line matches intended canonical source')
    wait_for_store_item(page, request['product_id'], lines[0]['key'])
    return name


def wait_for_store_item(page: Page, product_id: int, key: str, *, timeout=5.0, interval=0.25,
                        clock=time.monotonic) -> dict:
    """Observe the exact AJAX line in the same browser session, never any item."""
    started = clock()
    deadline = started + timeout
    attempt = 0
    while True:
        attempt += 1
        state = store_cart_state(page, timeout_ms=max(1, int((deadline - clock()) * 1000)))
        print('INFO store_observation=' + json.dumps({**state, 'attempt': attempt,
              'elapsed_ms': round((clock() - started) * 1000)}, ensure_ascii=False))
        require(state.get('status') == 200, 'Store API observation HTTP 200')
        if any(i.get('id') == product_id and i.get('key') == key for i in state.get('items', [])):
            require(clock() <= deadline, 'exact cart item observed within bounded deadline')
            print('PASS  Store API contains exact simple product and AJAX cart line added through current UI')
            return state
        remaining = deadline - clock()
        if remaining <= 0:
            raise AssertionError(f'Exact Store API item absent after {attempt} attempts: product_id={product_id}; key={key}; state={state}')
        page.wait_for_timeout(min(interval, remaining) * 1000)


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
    require(not page.is_closed() and page.url.startswith(BASE + '/'), 'cleanup stays in isolated staging browser page')
    result = page.evaluate("""async () => {
      const read = async () => {
        const r = await fetch('/wp-json/wc/store/v1/cart', {credentials:'same-origin'});
        if (r.status !== 200) throw Error('Cleanup cart GET HTTP ' + r.status);
        const cart = await r.json();
        if (!Array.isArray(cart.items)) throw Error('Invalid cleanup cart shape');
        return {cart, nonce:r.headers.get('Nonce')};
      };
      let current = await read();
      const keys = current.cart.items.map(i => i.key);
      for (const key of keys) {
        if (!key || !current.nonce) throw Error('Missing item key/nonce for isolated cleanup');
        const removed = await fetch('/wp-json/wc/store/v1/cart/remove-item', {
          method:'POST', credentials:'same-origin',
          headers:{Nonce:current.nonce, 'Content-Type':'application/json'}, body:JSON.stringify({key})
        });
        if (removed.status !== 200) throw Error('Cleanup remove-item HTTP ' + removed.status);
        current = await read();
      }
      const final = await read();
      return {status:200, removed:keys.length, cart:final.cart};
    }""")
    cart = result['cart']
    require(result['status'] == 200 and cart['items_count'] == 0 and cart['items'] == [],
            f"only isolated browser test cart cleaned; fresh GET HTTP 200, items_count=0, items=[]; removed={result['removed']}")


@contextmanager
def isolated_browser_page(browser: Browser, **options):
    """Own a new anonymous context; report cleanup failures without masking assertions."""
    ctx = browser.new_context(**options)
    try:
        ctx.route('**/*', lambda route: route.abort() if route.request.method == 'POST' and ('/wc/store/v1/checkout' in route.request.url or 'wc-ajax=checkout' in route.request.url) else route.continue_())
        page = ctx.new_page()
        pending = set()
        page.on('request', lambda request: pending.add(request) if 'wc-ajax=rollsbar_cart' in request.url else None)
        page.on('requestfinished', lambda request: pending.discard(request))
        page.on('requestfailed', lambda request: pending.discard(request))
        try:
            yield page
        finally:
            primary = sys.exc_info()[1]
            try:
                deadline = time.monotonic() + 10
                while pending and not page.is_closed() and time.monotonic() < deadline:
                    page.wait_for_timeout(100)
                require(not pending, 'isolated cart AJAX requests settled before cleanup')
                clean_test_cart(page)
            except Exception as cleanup:
                print(f'FAIL  isolated cart cleanup: {type(cleanup).__name__}: {cleanup}', file=sys.stderr)
                if primary is None:
                    raise
                primary.add_note(f'Cleanup also failed: {cleanup}')
    finally:
        ctx.close()


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
    pickup_controls = page.locator('input[type="radio"]').evaluate_all("""els => els.map(el => ({
      name:el.name, value:el.value, checked:el.checked,
      label:(el.closest('label') || document.querySelector('label[for="'+CSS.escape(el.id)+'"]'))?.textContent?.trim() || ''
    }))""")
    print('INFO checkout_radio_options=' + json.dumps(pickup_controls, ensure_ascii=False))


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
    proceed.scroll_into_view_if_needed()
    proceed.click(trial=True)
    print('PASS  mobile checkout control receives pointer events without submitting')
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
    with isolated_browser_page(browser, viewport={"width": 1440, "height": 1000}, locale="ru-RU") as page:
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
        assert_public_routes(page)
        require(not page_errors, f"desktop has no uncaught page JS errors (got {page_errors})")
        return RunResult(page_errors)


def run_mobile(browser: Browser) -> RunResult:
    with isolated_browser_page(browser, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=3, locale="ru-RU") as page:
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
        assert_public_routes(page)
        require(not page_errors, f"mobile has no uncaught page JS errors (got {page_errors})")
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

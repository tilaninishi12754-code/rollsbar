#!/usr/bin/env python3
"""Browser Gate B for the real RollsBar REG.RU staging site.

Covers desktop and mobile customer journeys without placing a real order:
home -> add product -> cart -> checkout, checkout field behavior, delivery table,
manual-zone absence, trusted HTTPS, ruble pricing, and the historical mobile
cart-overlay bug.
"""
from __future__ import annotations

import re
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


def add_first_simple_product(page: Page) -> str:
    cards = page.locator(".rollsbar-product-card")
    require(cards.count() == 5, f"homepage has exactly 5 smoke product cards (got {cards.count()})")

    add_buttons = page.locator("a.add_to_cart_button.ajax_add_to_cart")
    require(add_buttons.count() > 0, "at least one smoke product is directly addable")
    button = add_buttons.first
    card = button.locator("xpath=ancestor::article[contains(@class,'rollsbar-product-card')]")
    product_name = norm(card.locator("h3").inner_text())
    require(bool(product_name), "selected smoke product has a visible name")

    href = button.get_attribute("href") or ""
    product_id = button.get_attribute("data-product_id") or ""
    print(f"INFO  add button href={href} product_id={product_id}")

    observed: list[tuple[int, str]] = []

    def capture(response) -> None:
        url = response.url
        if "wc-ajax=add_to_cart" in url or "add-to-cart=" in url:
            observed.append((response.status, url))

    page.on("response", capture)

    before_badge = ""
    badge = page.locator(".rollsbar-cart-count").first
    if badge.count():
        before_badge = norm(badge.inner_text())

    button.click()
    page.wait_for_timeout(2500)

    after_badge = ""
    if badge.count():
        after_badge = norm(badge.inner_text())
    cookie_names = sorted(
        {
            c.get("name", "")
            for c in page.context.cookies()
            if "woocommerce" in c.get("name", "") or "wp_woocommerce" in c.get("name", "")
        }
    )
    button_classes = button.get_attribute("class") or ""
    print(f"INFO  add responses={observed}")
    print(f"INFO  cart badge before={before_badge!r} after={after_badge!r}")
    print(f"INFO  add button classes after click={button_classes}")
    print(f"INFO  Woo cookie names={cookie_names}")
    print(f"INFO  browser URL after click={page.url}")

    if any("wc-ajax=add_to_cart" in url and 200 <= status < 300 for status, url in observed):
        require(
            "added" in button_classes or (after_badge and after_badge != before_badge),
            "Woo AJAX add-to-cart emitted a browser success signal",
        )
    else:
        require(
            "add-to-cart=" in page.url
            or any("add-to-cart=" in url and 200 <= status < 400 for status, url in observed),
            "add-to-cart produced either AJAX or fallback navigation",
        )

    state = store_cart_state(page)
    require(state.get("status") == 200, "Store API cart is reachable after add-to-cart")
    require(product_name in state.get("names", []), f"Store API contains added product: {product_name}")
    print(f"INFO  added product: {product_name}")
    return product_name


def assert_delivery_table(page: Page) -> None:
    rules = page.locator(".rollsbar-delivery-rule")
    require(rules.count() == 7, f"delivery table has 7 tiers (got {rules.count()})")
    text = norm(page.locator("#delivery").inner_text())
    for fragment in ("Бесплатная доставка от суммы по району", "М. Жукова", "Мазанка", "1 200 ₽", "4 000 ₽"):
        require(fragment in text, f"delivery table contains: {fragment}")
    require("Ручного выбора зоны клиентом не будет" in text, "delivery copy preserves no-manual-zone rule")


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
    page = ctx.new_page()
    page_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    response = page.goto(BASE + "/", wait_until="domcontentloaded")
    response_ok(response, "desktop home")
    page.wait_for_timeout(1000)
    assert_delivery_table(page)
    product_name = add_first_simple_product(page)
    assert_cart(page, product_name)
    assert_checkout(page)
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
    page = ctx.new_page()
    page_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    response = page.goto(BASE + "/", wait_until="domcontentloaded")
    response_ok(response, "mobile home")
    page.wait_for_timeout(1000)
    require(page.locator(".rollsbar-product-card").count() == 5, "mobile home renders 5 smoke products")
    product_name = add_first_simple_product(page)
    assert_cart(page, product_name)
    assert_no_mobile_overlay(page)
    assert_checkout(page)
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

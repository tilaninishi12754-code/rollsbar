#!/usr/bin/env python3
"""Final live Browser Gate B for the promoted 118-card staging catalog.

Reuses the already-proven Gate B assertions while replacing only the smoke
catalog cardinality assumption (5 cards) with the promoted catalog invariant
(118 cards).
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Browser, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_b_browser as gate  # noqa: E402

EXPECTED_CARDS = 118


def add_first_simple_product_full(page) -> str:
    cards = page.locator(".rollsbar-product-card")
    gate.require(
        cards.count() == EXPECTED_CARDS,
        f"homepage renders full approved catalog ({EXPECTED_CARDS} cards; got {cards.count()})",
    )

    add_buttons = page.locator("a.add_to_cart_button.ajax_add_to_cart")
    gate.require(add_buttons.count() > 0, "at least one full-catalog product is directly addable")
    button = add_buttons.first
    card = button.locator("xpath=ancestor::article[contains(@class,'rollsbar-product-card')]")
    product_name = gate.norm(card.locator("h3").inner_text())
    gate.require(bool(product_name), "selected full-catalog product has a visible name")

    badge = page.locator(".rollsbar-cart-count").first
    before_badge = gate.norm(badge.inner_text()) if badge.count() else ""
    button.click()
    page.wait_for_timeout(2500)
    after_badge = gate.norm(badge.inner_text()) if badge.count() else ""

    state = gate.store_cart_state(page)
    gate.require(state.get("status") == 200, "Store API cart is reachable after full-catalog add-to-cart")
    gate.require(product_name in state.get("names", []), f"Store API contains added product: {product_name}")
    gate.require(
        (after_badge and after_badge != before_badge) or state.get("itemsCount", 0) > 0,
        "full-catalog add-to-cart changes observable cart state",
    )
    print(f"INFO  added full-catalog product: {product_name}")
    return product_name


def run_mobile_full(browser: Browser) -> None:
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

    response = page.goto(gate.BASE + "/", wait_until="domcontentloaded")
    gate.response_ok(response, "mobile full-catalog home")
    page.wait_for_timeout(1200)
    gate.require(
        page.locator(".rollsbar-product-card").count() == EXPECTED_CARDS,
        f"mobile home renders full approved catalog ({EXPECTED_CARDS} cards)",
    )
    product_name = add_first_simple_product_full(page)
    gate.assert_cart(page, product_name)
    gate.assert_no_mobile_overlay(page)
    gate.assert_checkout(page)
    gate.require(not page_errors, f"mobile full-catalog has no uncaught page JS errors (got {page_errors})")
    ctx.close()


def main() -> int:
    try:
        # Patch only the smoke cardinality helper used by the proven desktop run.
        gate.add_first_simple_product = add_first_simple_product_full
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                gate.run_desktop(browser)
                run_mobile_full(browser)
            finally:
                browser.close()
        print("FULL CATALOG BROWSER GATE B PASS")
        return 0
    except Exception as exc:
        print(f"FULL CATALOG BROWSER GATE B FAIL: {exc.__class__.__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

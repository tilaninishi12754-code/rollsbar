#!/usr/bin/env python3
"""Read-only browser diagnostic for Woo cart persistence/rendering."""
from __future__ import annotations
import json
import re
import sys
from playwright.sync_api import sync_playwright

BASE = "https://staging.rollsbar.ru"

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ").strip())

def store_cart(page):
    return page.evaluate("""async () => {
      const r = await fetch('/wp-json/wc/store/v1/cart', {credentials:'same-origin'});
      const j = await r.json();
      return {status:r.status, items:(j.items||[]).map(i=>({name:i.name,key:i.key,quantity:i.quantity})), items_count:j.items_count, totals:j.totals};
    }""")

def main() -> int:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width":1440,"height":1000}, locale="ru-RU")
        page = ctx.new_page()
        errors=[]; page.on('pageerror', lambda e: errors.append(str(e)))
        resp=page.goto(BASE+'/', wait_until='domcontentloaded')
        print(f'home_status={resp.status if resp else "none"}')
        page.wait_for_timeout(1000)
        btn=page.locator('a.add_to_cart_button.ajax_add_to_cart').first
        name=norm(btn.locator("xpath=ancestor::article[contains(@class,'rollsbar-product-card')]").locator('h3').inner_text())
        pid=btn.get_attribute('data-product_id') or ''
        print(f'product={name} id={pid}')
        network=[]
        page.on('response', lambda r: network.append((r.status,r.url)) if ('wc-ajax=add_to_cart' in r.url or '/wp-json/wc/store/v1/cart' in r.url) else None)
        btn.click(); page.wait_for_timeout(2500)
        print('network_after_add='+json.dumps(network, ensure_ascii=False))
        before=store_cart(page)
        print('store_cart_before_nav='+json.dumps(before, ensure_ascii=False)[:3000])
        cookies=[{k:c.get(k) for k in ('name','domain','path','secure','sameSite')} for c in ctx.cookies() if 'woocommerce' in c.get('name','') or 'wp_woocommerce' in c.get('name','')]
        print('woo_cookies='+json.dumps(cookies, ensure_ascii=False))
        cart_resp=page.goto(BASE+'/cart/', wait_until='domcontentloaded')
        print(f'cart_status={cart_resp.status if cart_resp else "none"} final_url={page.url}')
        page.wait_for_timeout(1600)
        after=store_cart(page)
        print('store_cart_after_nav='+json.dumps(after, ensure_ascii=False)[:3000])
        body=norm(page.locator('body').inner_text())
        print('cart_body='+body[:1800])
        print('cart_blocks='+json.dumps({
          'block_cart': page.locator('.wc-block-cart').count(),
          'classic_cart': page.locator('.woocommerce-cart-form').count(),
          'empty_cart': page.locator('.wc-block-cart__empty-cart__title, .cart-empty').count(),
          'product_rows': page.locator('.wc-block-cart-items__row, .woocommerce-cart-form__cart-item').count(),
        }, ensure_ascii=False))
        print('page_errors='+json.dumps(errors, ensure_ascii=False))
        browser.close()
        if before.get('items_count',0) < 1:
            print('DIAG FAIL: Store API is empty immediately after add'); return 2
        if after.get('items_count',0) < 1:
            print('DIAG FAIL: Store API loses cart across navigation'); return 3
        if name not in body:
            print('DIAG: session persists but cart page does not render product name'); return 4
        print('CART SESSION DIAG PASS'); return 0

if __name__=='__main__': sys.exit(main())

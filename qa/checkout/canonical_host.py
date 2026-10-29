"""Trailing-dot entry must normalize before cart creation; no order submission."""
import os,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'wordpress/deploy'),str(ROOT/'qa/checkout')]
from gate_b_browser import BASE,require,store_cart_state
from delivery_test_context import delivery_page,settle_native
from playwright.sync_api import sync_playwright
out=ROOT/'qa/visual-results/canonical-host';out.mkdir(parents=True,exist_ok=True)
report={'release_sha':os.environ.get('ROLLSBAR_DEPLOY_SHA'),'status':'RUNNING','orders_created':0,'checks':[]}
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch()
  for width in [1440,390]:
   with delivery_page(b,viewport={'width':width,'height':900},locale='ru-RU') as p:
    response=p.goto('https://staging.rollsbar.ru./?alias-regression=1',wait_until='domcontentloaded')
    require(p.url==BASE+'/?alias-regression=1','dotted host redirects before storefront/cart initialization')
    require(response.request.redirected_from is not None,'actual HTTP redirect, not client navigation')
    sources=p.locator('.rollsbar-product-card').filter(has=p.locator('[data-rollsbar-cart-delta="1"]')).evaluate_all('cards=>cards.slice(0,4).map(c=>c.dataset.rollsbarSourceId)')
    require(len(sources)==4,'four distinct simple products available')
    for source in sources:
     with p.expect_response(lambda r:'wc-ajax=rollsbar_cart' in r.url and r.request.method=='POST') as added:
      p.locator(f'[data-rollsbar-source-id="{source}"] [data-rollsbar-cart-delta="1"]').first.click()
     require(added.value.json().get('success'),'native cart add succeeds')
     p.wait_for_function('!document.querySelector(".rollsbar-product-card[aria-busy=true]")')
    require(store_cart_state(p)['itemsCount']==4,'native session contains four products')
    p.locator('.rollsbar-cart-link:visible').first.click()
    p.wait_for_function('document.querySelector(".rollsbar-cart-drawer__panel")?.getAttribute("aria-busy")==="false"')
    require(p.locator('.rollsbar-cart-item').count()==4,'drawer contains the same four products')
    settle_native(p);p.locator('.rollsbar-drawer-checkout').click()
    p.wait_for_url(BASE+'/checkout/',wait_until='domcontentloaded')
    p.locator('input[id$="-phone"]:visible').wait_for()
    require(store_cart_state(p)['itemsCount']==4,'checkout keeps exact populated native session')
    require(not p.locator('.wc-block-cart__empty-cart__title').count(),'not redirected to empty cart')
    settle_native(p)
    p.goto('https://staging.rollsbar.ru./checkout/?alias-regression=2',wait_until='domcontentloaded')
    require(p.url==BASE+'/checkout/?alias-regression=2','direct dotted checkout preserves path/query')
    p.locator('input[id$="-phone"]:visible').wait_for()
    require(store_cart_state(p)['itemsCount']==4,'normalization preserves existing canonical cart')
    report['checks'].append({'width':width,'status':'PASS','distinct_products':sources})
  b.close()
 report['status']='PASS'
finally:(out/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

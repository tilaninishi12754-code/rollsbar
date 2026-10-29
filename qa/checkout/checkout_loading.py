"""Real cold/warm checkout timings, normal cache, isolated cart, never submit.

Unlike functional submit gates this probe installs no routes: Playwright routing
disables HTTP cache and would invalidate a real cold/warm comparison.
"""
import json,sys,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'wordpress/deploy'),str(ROOT/'qa/checkout')]
from gate_b_browser import BASE,add_first_simple_product,first_visible,clean_test_cart,require
from request_guard import is_order_submission
from playwright.sync_api import sync_playwright
out=Path(os.environ.get('ROLLSBAR_LOADING_OUT',str(ROOT/'qa/visual-results/checkout-loading')))
out.mkdir(parents=True,exist_ok=True)
report={'release_sha':os.environ.get('ROLLSBAR_DEPLOY_SHA'),'orders_created':0,'checks':[],'status':'RUNNING'}
def idle(p):
 p.wait_for_function('()=>!window.wp?.data?.select("wc/store/cart")?.isCustomerDataUpdating?.()&&!window.wp?.data?.select("wc/store/checkout")?.isCalculating?.()')
 p.wait_for_timeout(600)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch()
  for width in [1440,390]:
   with b.new_context(viewport={'width':width,'height':900},locale='ru-RU') as ctx:
    p=ctx.new_page();orders=[];errors=[]
    p.on('request',lambda r:orders.append(r.url) if is_order_submission(r) else None)
    p.on('pageerror',lambda e:errors.append(str(e)))
    try:
     p.goto(BASE+'/',wait_until='domcontentloaded');add_first_simple_product(p)
     first_visible(p,['.rollsbar-cart-link','[data-rollsbar-orderbar]:not([hidden])','[data-rollsbar-mobile-cart]:not([hidden])']).click()
     p.wait_for_function('document.querySelector(".rollsbar-cart-drawer__panel")?.getAttribute("aria-busy")==="false"')
     idle(p)
     t=time.monotonic();p.locator('.rollsbar-drawer-checkout').click()
     p.wait_for_url(BASE+'/checkout/',wait_until='domcontentloaded')
     p.locator('input[id$="-phone"]:visible').wait_for()
     cold=time.monotonic()-t
     idle(p)
     initial=p.evaluate('''()=>({nav:performance.getEntriesByType('navigation')[0].toJSON(),scripts:[...document.scripts].map(s=>s.src).filter(Boolean),speculative:[...document.querySelectorAll('link[rel=prefetch],link[rel=prerender]')].map(l=>l.href),resources:performance.getEntriesByType('resource').map(r=>({name:r.name,initiator:r.initiatorType,duration:r.duration,size:r.transferSize}))})''')
     if '--optimized' in sys.argv:
      require(not initial['speculative'],'checkout speculative downloads absent')
      require(not any('/checkout.min.js?' in u for u in initial['scripts']),'classic submission script absent')
     p.screenshot(path=str(out/f'checkout-{width}.png'),animations='disabled')
     t=time.monotonic();p.reload(wait_until='domcontentloaded');p.locator('input[id$="-phone"]:visible').wait_for()
     warm=time.monotonic()-t;idle(p)
     require(not orders and not errors,'no order submission or JavaScript errors')
     row={'width':width,'cold_form_seconds':cold,'warm_form_seconds':warm,'initial':initial}
     report['checks'].append(row)
     print(json.dumps({k:v for k,v in row.items() if k!='initial'}),flush=True)
    finally:
     idle(p);clean_test_cart(p)
  b.close()
 report['status']='PASS'
finally:(out/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

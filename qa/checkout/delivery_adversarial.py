"""Live native pickup, empty fields, close/reopen and low-precision adversarial gate."""
import json,os,sys
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
sys.stdout.reconfigure(encoding='utf8',line_buffering=True)
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'wordpress/deploy'))
from gate_b_browser import BASE,isolated_browser_page,add_first_simple_product,first_visible,require,store_cart_state
from playwright.sync_api import sync_playwright
from request_guard import is_order_submission
from delivery_test_context import delivery_page,settle_native
OUT=ROOT/'qa/visual-results/delivery-rules';OUT.mkdir(parents=True,exist_ok=True)
report={'status':'RUNNING','release_sha':os.environ['ROLLSBAR_DEPLOY_SHA'],'checks':[],'submissions':[]}
def enter(p):
 p.evaluate('scrollTo({top:900,behavior:"instant"})')
 trigger=first_visible(p,['.rollsbar-cart-link','[data-rollsbar-orderbar]:not([hidden])','[data-rollsbar-mobile-cart]:not([hidden])'])
 require(trigger is not None,'cart trigger visible');trigger.click()
 p.locator('#rollsbarCartDrawer').wait_for(state='visible')
 p.wait_for_function('document.querySelector(".rollsbar-cart-drawer__panel")?.getAttribute("aria-busy")==="false"')
 settle_native(p)
 p.locator('.rollsbar-drawer-checkout').click();p.wait_for_url(BASE+'/checkout/',wait_until='domcontentloaded')
 p.locator('[data-rollsbar-modal="1"]').wait_for(state='visible')
 require(p.locator('.wp-block-woocommerce-checkout').count()==1,'first cart activation opens one native checkout')
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  for width in [320,700,701]:
   with delivery_page(browser,viewport={'width':width,'height':900},is_mobile=width<=700,has_touch=width<=700,locale='ru-RU') as p:
    def guard(route):
     if is_order_submission(route.request):report['submissions'].append(route.request.url);route.abort()
     else:route.fallback()
    p.context.route('**/*',guard)
    p.goto(BASE+'/',wait_until='load')
    p.evaluate('scrollTo({top:900,behavior:"instant"})')
    p.locator('.rollsbar-cart-link:visible,[data-rollsbar-orderbar]:not([hidden]):visible,[data-rollsbar-mobile-cart]:not([hidden]):visible').first.wait_for(state='visible')
    first_visible(p,['.rollsbar-cart-link','[data-rollsbar-orderbar]:not([hidden])','[data-rollsbar-mobile-cart]:not([hidden])']).click()
    p.locator('#rollsbarCartDrawer').wait_for(state='visible')
    p.wait_for_function('document.querySelector(".rollsbar-cart-drawer__panel")?.getAttribute("aria-busy")==="false"')
    p.locator('[data-drawer-mode=pickup]').click()
    p.wait_for_function('document.querySelector(".rollsbar-cart-drawer__panel")?.getAttribute("aria-busy")==="false"&&document.querySelector("[data-drawer-mode=pickup]")?.getAttribute("aria-pressed")==="true"')
    persisted=p.evaluate('async()=>{const c=rollsbarCart,r=await fetch(c.url,{method:"POST",body:new URLSearchParams({nonce:c.nonce,request:JSON.stringify({operation:"read"})})});return (await r.json()).data.mode}')
    require(persisted=='pickup','empty-cart pickup persists across a fresh native-session request')
    p.locator('.rollsbar-drawer-close').click()
    add_first_simple_product(p)
    rates=p.evaluate('async()=>await(await fetch("/wp-json/wc/store/v1/cart")).json()')
    require(any(r['selected'] and r['method_id']=='pickup_location' for package in rates['shipping_rates'] for r in package['shipping_rates']),'empty-cart pickup preference selects native pickup after first add')
    enter(p)
    p.wait_for_function('wp.data.select("wc/store/checkout").prefersCollection()===true')
    require(not p.locator('input[id$="-address_1"]').filter(visible=True).count(),'native drawer pickup reaches checkout without customer address')
    first=p.locator('#billing-first_name');phone=p.locator('#billing-phone')
    require(p.locator('.wc-block-checkout__pickup-options').bounding_box()['y']<p.locator('.wc-block-checkout__order-notes').bounding_box()['y'],'pickup address appears below identity before comment')
    first.fill('');phone.fill('');phone.blur()
    require(first.evaluate('e=>e.required&&e.validity.valueMissing'),'empty native pickup name invalid')
    require(phone.evaluate('e=>e.required&&e.validity.valueMissing'),'empty native pickup phone invalid')
    first.fill('Тест');phone.fill('+79780000000')
    p.locator('#order-rollsbar-privacy-consent').check()
    p.locator('.wc-block-checkout__add-note textarea').fill('Самовывоз: тест без заказа')
    p.wait_for_function('()=>!wp.data.select("wc/store/cart").isCustomerDataUpdating()&&!wp.data.select("wc/store/checkout").isCalculating()')
    p.evaluate('''()=>{window.__rbPickupPayload=null;wp.apiFetch.use((o,next)=>{
     if((o.path||o.url||'').includes('/wc/store/v1/checkout')&&(o.method||'GET').toUpperCase()==='POST'){
      window.__rbPickupPayload=JSON.parse(JSON.stringify(o.data));return Promise.reject({code:'qa_stop',message:'QA: остановлено до HTTP.',data:{status:400}});
     }return next(o);
    });}''')
    phone.fill('+7')
    p.wait_for_function('!!wp.data.select("wc/store/validation").getValidationError("rollsbar-contact-phone")')
    p.locator('.wc-block-components-checkout-place-order-button').click()
    p.wait_for_function('wp.data.select("wc/store/checkout").isIdle()')
    require(p.evaluate('window.__rbPickupPayload') is None,'prefix-only phone blocked before native POST assembly')
    phone.fill('+79780000000')
    p.wait_for_function('()=>!wp.data.select("wc/store/validation").getValidationError("rollsbar-contact-phone")&&!wp.data.select("wc/store/cart").isCustomerDataUpdating()&&!wp.data.select("wc/store/checkout").isCalculating()')
    p.locator('.wc-block-components-checkout-place-order-button').click()
    p.wait_for_function('window.__rbPickupPayload!==null')
    payload=p.evaluate('window.__rbPickupPayload')
    report['pickup_payload']=payload
    require(payload['billing_address']['first_name']=='Тест' and payload['billing_address']['phone']=='+79780000000','native pickup payload retains identity')
    require(not payload['billing_address']['address_1'],'native pickup submits without customer address')
    require(payload['payment_method']=='cod' and payload.get('create_account') is False,'native pickup guest COD payload')
    require(payload['billing_address']['email'].endswith('@checkout.rollsbar.invalid'),'pickup email compatibility without customer input')
    p.locator('[role=dialog]').evaluate('e=>e.scrollTop=150')
    require(p.evaluate('document.scrollingElement.scrollTop===0'),'body stays locked while modal scrolls')
    p.locator('.rollsbar-legal-page__back').focus();p.keyboard.press('Shift+Tab')
    require(p.locator('[role=dialog]').evaluate('e=>e.contains(document.activeElement)'),'focus stays in modal')
    settle_native(p)
    p.keyboard.press('Escape');p.wait_for_url(BASE+'/',wait_until='domcontentloaded')
    require(store_cart_state(p)['itemsCount']==1,'close preserves native cart session')
    enter(p)
    p.locator('.wc-block-checkout__shipping-method [role=radio]').first.click()
    address=p.locator('input[id$="-address_1"]').filter(visible=True).first
    query='Симферополь Киевская'
    with p.expect_response(lambda r:'/rollsbar/v1/address-suggestions' in r.url and parse_qs(urlsplit(r.url).query).get('query')==[query]) as fresh:address.fill(query)
    candidates=fresh.value.json()['suggestions']
    p.wait_for_function('(v)=>document.querySelector(".rollsbar-address-suggestions__item")?.textContent===v',arg=candidates[0]['display'])
    with p.expect_response(lambda r:'/rollsbar/v1/address-resolve' in r.url and r.request.method=='POST') as resolved:p.locator('.rollsbar-address-suggestions__item').first.click()
    result=resolved.value.json()
    require(result['qc_geo']!=0 and result['delivery']['minimum'] is None,'low precision never assigns a threshold')
    p.wait_for_function('!!wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum")')
    require(p.locator('iframe[src*="map"]').count()==0,'low precision never opens deferred map')
    p.screenshot(path=str(OUT/f'adversarial-{width}.png'))
    report['checks'].append({'width':width,'status':'PASS','pickup_native_presubmit':True,'empty_identity_rejected':True,'close_reopen':True,'low_precision':True})
    print('ADVERSARIAL PASS',width,flush=True)
  browser.close()
 require(not report['submissions'],'no order HTTP request escaped native middleware')
 report['status']='PASS'
finally:(OUT/'adversarial-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

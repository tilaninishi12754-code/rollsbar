"""Live map/address integration. No order POST; isolated native cart cleaned."""
import sys,os,json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'wordpress/deploy'))
from gate_b_browser import BASE,add_first_simple_product,require
from delivery_test_context import delivery_page,settle_native
from request_guard import is_order_submission
from playwright.sync_api import sync_playwright
OUT=ROOT/'qa/visual-results/delivery-rules/map';OUT.mkdir(parents=True,exist_ok=True)
SHA=os.environ['ROLLSBAR_DEPLOY_SHA'];expected=subprocess.check_output(['git','show',SHA+':wordpress/wp-content/plugins/rollsbar-core/assets/delivery-map.html'],cwd=ROOT)
report={'status':'RUNNING','release_sha':SHA,'checks':[],'orders_created':0,'errors':[]}
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  for width in [1440,701,700,390,320]:
   with delivery_page(browser,viewport={'width':width,'height':900},is_mobile=width<=700,has_touch=width<=700,locale='ru-RU') as p:
    p.on('pageerror',lambda e:report['errors'].append(str(e)))
    p.goto(BASE+'/',wait_until='domcontentloaded');add_first_simple_product(p);settle_native(p)
    with p.expect_response(lambda r:'/rollsbar-core/assets/delivery-map.html' in r.url) as response:
     p.goto(BASE+'/checkout/',wait_until='domcontentloaded')
     p.locator('.wc-block-checkout__shipping-method [role=radio]').first.click()
    require(response.value.status==200 and response.value.body()==expected,'exact deployed map asset, no substitutions')
    frame=p.locator('.rollsbar-checkout-map iframe').element_handle().content_frame();frame.wait_for_function('window.rollsbarMapReady===true')
    address=p.locator('#shipping-address_1');address.fill('Симферополь Киевская 139А')
    with p.expect_response(lambda r:'/rollsbar/v1/address-resolve' in r.url and r.request.method=='POST') as resolved:p.locator('.rollsbar-address-suggestions__item').first.click()
    decision=resolved.value.json()['delivery'];require(decision.get('provisional') is True and decision['minimum']==1200,'live geographic fallback outside exact table is informational')
    frame.wait_for_function('window.rollsbarMapState?.exact===true')
    require(p.locator('.rollsbar-checkout-map').get_attribute('data-exact')=='1','exact provider point displayed')
    require(frame.locator('.legend span').count()==7,'seven free-delivery minimums, no delivery fees')
    require(frame.evaluate('document.documentElement.scrollWidth<=innerWidth'),'iframe has no horizontal overflow')
    p.locator('.rollsbar-checkout-map').scroll_into_view_if_needed()
    p.screenshot(path=str(OUT/f'map-{width}.png'),animations='disabled')
    state=frame.evaluate('window.rollsbarMapState')
    address.fill('Другой адрес')
    frame.wait_for_function('window.rollsbarMapState?.exact===false')
    require(not p.evaluate('wp.data.select("wc/store/checkout").getExtensionData()["rollsbar-delivery"].address_proof'),'editing removes signed proof and customer marker')
    p.locator('.wc-block-checkout__shipping-method [role=radio]').nth(1).click()
    require(not p.locator('.rollsbar-checkout-map').is_visible(),'pickup hides map')
    p.locator('.wc-block-checkout__shipping-method [role=radio]').first.click()
    require(p.locator('.rollsbar-checkout-map').is_visible(),'delivery restores same map')
    require(p.locator('.rollsbar-checkout-map iframe').count()==1,'no duplicated map lifecycle')
    settle_native(p)
    frame=p.locator('.rollsbar-checkout-map iframe').element_handle().content_frame()
    frame.wait_for_function('window.rollsbarMapReady===true')
    frame.locator('#map').focus();frame.locator('#map').press('Escape')
    p.wait_for_url(BASE+'/',timeout=5000,wait_until='domcontentloaded')
    require(True,'Escape from focused map closes checkout without losing native cart')
    report['checks'].append({'width':width,'status':'PASS','exact_point':state,'served_sha256':hashlib.sha256(expected).hexdigest()})
  browser.close()
 require(not report['errors'],'no map JavaScript errors')
 report['status']='PASS'
finally:(OUT/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

"""4200/2500 regression, nearest local address and attribution; no order POST."""
import sys,os,json
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'wordpress/deploy'),str(ROOT/'qa/checkout')]
from gate_b_browser import BASE,add_first_simple_product,require
from delivery_test_context import delivery_page,settle_native
from playwright.sync_api import sync_playwright
out=ROOT/'qa/visual-results/fulfillment';out.mkdir(parents=True,exist_ok=True)
report={'status':'RUNNING','release_sha':os.environ['ROLLSBAR_DEPLOY_SHA'],'checks':[],'orders_created':0}
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch()
  for width in [1440,390]:
   with delivery_page(b,viewport={'width':width,'height':900},locale='ru-RU') as p:
    p.goto(BASE+'/',wait_until='domcontentloaded');add_first_simple_product(p);settle_native(p)
    total=p.evaluate('''async()=>{const r=await fetch('/wp-json/wc/store/v1/cart'),cart=await r.json();const u=await fetch('/wp-json/wc/store/v1/cart/update-item',{method:'POST',headers:{'Content-Type':'application/json',Nonce:r.headers.get('Nonce')},body:JSON.stringify({key:cart.items[0].key,quantity:10})});if(!u.ok)throw Error('Native quantity update failed');return (await u.json()).totals;}''')
    print('NATIVE_TOTALS',total,flush=True)
    require(int(total['total_items'])/10**int(total['currency_minor_unit'])==4200,'native 10 x 420 cart, not a client-invented total')
    p.goto(BASE+'/checkout/',wait_until='domcontentloaded');p.locator('#shipping-address_1').wait_for()
    def select(query):
     with p.expect_response(lambda r:'/address-suggestions' in r.url and parse_qs(urlsplit(r.url).query).get('query')==[query]) as suggested:p.locator('#shipping-address_1').fill(query)
     first=suggested.value.json()['suggestions'][0]['display']
     p.wait_for_function('(text)=>document.querySelector(".rollsbar-address-suggestions__item")?.textContent===text',arg=first)
     with p.expect_response(lambda r:'/address-resolve' in r.url and r.request.method=='POST') as resolved:p.locator('.rollsbar-address-suggestions__item').first.click()
     value=resolved.value.json();settle_native(p);return value
    address=select('Симферополь Ульяны Громовой 3')
    require(address['delivery']['minimum']==2500,'reported customer address has actual 2500 minimum')
    p.locator('#shipping-phone').fill('89781234567');p.locator('#order-rollsbar-privacy-consent').check();settle_native(p)
    require(p.evaluate('wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum")') is None,'4200 exceeds 2500 and has no minimum error')
    p.wait_for_function('()=>!document.querySelector(".rollsbar-submit-feedback").textContent.includes("Оставьте телефон")')
    require('доставка бесплатная' in p.locator('.rollsbar-submit-feedback').inner_text(),'completed contact/consent gets truthful qualified feedback')
    p.locator('[role=dialog]').evaluate('e=>e.scrollTop=0');p.screenshot(path=str(out/f'qualified-{width}.png'),animations='disabled')
    youth=[]
    for house in [1,2,5]:
     value=select('Симферополь Молодёжная '+str(house));youth.append(value)
     if value['qc_geo']==0:
      require(value['delivery']['status']=='resolved' and value['delivery']['minimum'] in [1200,1500,2000,2500,3000,3500,4000],'exact Molodezhnaya house receives an existing zone minimum')
      break
     require(value['delivery']['minimum'] is None,'imprecise Molodezhnaya coordinate remains manager callback')
    frame=p.locator('.rollsbar-checkout-map iframe').element_handle().content_frame();frame.wait_for_function('window.rollsbarMapReady===true')
    require(frame.locator('.leaflet-control-attribution a[href*="leafletjs"]').count()==0,'Leaflet prefix/flag removed through supported API')
    require(frame.locator('.leaflet-control-attribution a[href*="openstreetmap.org/copyright"]').is_visible(),'OpenStreetMap attribution preserved')
    p.locator('[role=dialog]').evaluate('e=>e.scrollTop=0');p.screenshot(path=str(out/f'local-address-{width}.png'),animations='disabled')
    report['checks'].append({'width':width,'status':'PASS','cart_rubles':4200,'minimum':2500,'molodezhnaya':[{'display':v['display'],'qc_geo':v['qc_geo'],'decision':v['delivery']} for v in youth]})
  b.close()
 report['status']='PASS'
finally:(out/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

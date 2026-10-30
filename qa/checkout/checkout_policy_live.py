"""Local suggestions / persisted minimum / note draft / ordinary browser cache. No order POST."""
import json,sys,os
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'wordpress/deploy'),str(ROOT/'qa/checkout')]
from gate_b_browser import BASE,add_first_simple_product,require,first_visible
from delivery_test_context import delivery_page,settle_native
from request_guard import effective_rest_method
from playwright.sync_api import sync_playwright
out=ROOT/'qa/visual-results/checkout-policy';out.mkdir(parents=True,exist_ok=True)
report={'status':'RUNNING','release_sha':os.environ.get('ROLLSBAR_DEPLOY_SHA'),'orders_created':0,'checks':[]}
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch()
  for width in [1440,390]:
   with delivery_page(b,viewport={'width':width,'height':900},locale='ru-RU') as p:
    home=p.goto(BASE+'/',wait_until='domcontentloaded')
    require('no-store' in home.headers.get('cache-control',''),'ordinary storefront document cannot retain old asset references')
    add_first_simple_product(p);settle_native(p)
    checkout=p.goto(BASE+'/checkout/',wait_until='domcontentloaded')
    directives={part.strip().lower() for part in checkout.headers.get('cache-control','').split(',')}
    require({'private','no-cache','must-revalidate','max-age=0'}<=directives,'native checkout HTML requires private revalidation on every visit')
    p.locator('#shipping-address_1').wait_for()
    address=p.locator('#shipping-address_1');queries=[]
    for query in ['Симферополь','улица Гагарина','Мазанка','Приятное Свидание']:
     with p.expect_response(lambda r:'/address-suggestions' in r.url and parse_qs(urlsplit(r.url).query).get('query')==[query]) as suggested:address.fill(query)
     result=suggested.value.json()['suggestions']
     require(bool(result) and not any('Москва' in s['display'] for s in result),'local suggestions for '+query)
     if query in ['Симферополь','улица Гагарина']:require('Симферополь' in result[0]['display'],'Simferopol ranked first for '+query)
     else:require(query in result[0]['display'],'approved nearby village remains available: '+query)
     queries.append({'query':query,'first':result[0]['display']})
    with p.expect_response(lambda r:'/address-suggestions' in r.url and parse_qs(urlsplit(r.url).query).get('query')==['Гагарина 1']) as suggested:address.fill('Гагарина 1')
    candidate=suggested.value.json()['suggestions'][0]['display']
    p.wait_for_function('(v)=>document.querySelector(".rollsbar-address-suggestions__item")?.textContent===v',arg=candidate)
    p.locator('.rollsbar-address-suggestions__item').first.click()
    p.wait_for_function('!!wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum")')
    settle_native(p);p.reload(wait_until='domcontentloaded')
    p.wait_for_function('!!wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum")')
    require(p.locator('#shipping-address_1').input_value()==candidate,'verified address survives ordinary reload')
    p.locator('.rollsbar-delivery-terms').filter(visible=True).first.wait_for(state='visible')
    require(all('От' in text for text in p.locator('.rollsbar-delivery-terms').all_text_contents()) and p.locator('.rollsbar-delivery-terms').count()>0,'saved-address minimum survives reload without false free delivery')
    for typed,expected in [('8','+7'),('7','+7'),('89781234567','+79781234567')]:
     p.locator('#shipping-phone').fill(typed);require(p.locator('#shipping-phone').input_value()==expected,'immediate prefix '+typed)
    note='Привезти 30.10 к 14:00 — незавершённый тест, без заказа'
    with p.expect_response(lambda r:'/wc/store/v1/checkout' in r.url and effective_rest_method(r.request)=='PUT' and json.loads(r.request.post_data or '{}').get('order_notes')==note):
     p.locator('.wc-block-checkout__add-note textarea').fill(note)
    settle_native(p);p.reload(wait_until='domcontentloaded')
    p.locator('.wc-block-checkout__add-note textarea').wait_for()
    require(p.locator('.wc-block-checkout__add-note textarea').input_value()==note,'unfinished note survives reload; only successful order may clear it')
    require('no-store' in p.request.get(BASE+'/').headers.get('cache-control',''),'same-browser revisit fetches dynamic HTML')
    p.locator('[role=dialog]').evaluate('e=>e.scrollTop=0');p.screenshot(path=str(out/f'policy-{width}.png'),animations='disabled')
    report['checks'].append({'width':width,'status':'PASS','queries':queries,'saved_address':candidate,'draft_retained':True})
  b.close()
 report['status']='PASS'
finally:(out/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

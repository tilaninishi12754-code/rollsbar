"""Actual staging DaData/identity/UI coverage. No checkout POST or order creation."""
import json,sys,os,base64,time
from urllib.parse import urlsplit,parse_qs
from pathlib import Path
sys.stdout.reconfigure(encoding='utf8',line_buffering=True)
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'wordpress/deploy'))
from gate_b_browser import BASE,isolated_browser_page,add_first_simple_product,require
from playwright.sync_api import sync_playwright
from request_guard import is_order_submission
from delivery_test_context import delivery_page
OUT=ROOT/'qa/visual-results/delivery-rules';OUT.mkdir(parents=True,exist_ok=True)
CASES=[
 (1200,'Симферополь Гагарина 17'),(1200,'Симферополь Лермонтова 16'),
 (1500,'Симферополь Бела Куна 5'),(1500,'Симферополь 51-й Армии 55'),
 (2000,'Крым Мирное Таврическая 120'),(2000,'Крым Мирное Стадионная 19'),
 (2000,'Крым Грэсовский Яблочкова 12'),
 (2500,'Крым Молодёжное Крымская 13'),(2500,'Крым Аграрное Спортивная 9'),
 (3000,'Крым Денисовка Энергетиков 2'),(3000,'Крым Фонтаны Верхние Фонтаны 32'),
 (3500,'Крым Урожайное 8 Марта 31'),(3500,'Крым Урожайное 8 Марта 32'),
 (4000,'Крым Донское Комсомольская 146А'),(4000,'Крым Мазанка Ясная 14'),
 (None,'Симферополь Кечкеметская 79'),(None,'Симферополь Беспалова 53'),
 (None,'Симферополь Киевская 139А'),(None,'Москва Тверская 1'),(None,'Симферополь Киевская')]
report={'status':'RUNNING','release_sha':os.environ['ROLLSBAR_DEPLOY_SHA'],'cases':[],'orders_created':0}
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  with delivery_page(browser,viewport={'width':1440,'height':900},locale='ru-RU') as p:
   def guard(route):
    if is_order_submission(route.request):raise RuntimeError('Unexpected checkout POST')
    route.fallback()
   p.context.route('**/*',guard)
   p.goto(BASE+'/',wait_until='domcontentloaded');add_first_simple_product(p)
   p.goto(BASE+'/checkout/',wait_until='domcontentloaded')
   p.locator('.wc-block-checkout__shipping-method [role=radio]').first.click()
   address=p.locator('input[id$="-address_1"]').filter(visible=True).first
   p.evaluate('()=>{window.__rbProbeEvents=[];document.addEventListener("input",e=>{if(e.target.id?.endsWith("address_1"))window.__rbProbeEvents.push({id:e.target.id,value:e.target.value,data:{...e.target.dataset},time:performance.now()})},true)}')
   for minimum,query in CASES:
    p.wait_for_function('()=>!wp.data.select("wc/store/cart").isCustomerDataUpdating()')
    try:
     with p.expect_response(lambda r:'/rollsbar/v1/address-suggestions' in r.url and parse_qs(urlsplit(r.url).query).get('query')==[query]) as suggested:
      address.fill(query)
    except Exception:
     report['failure_context']={'query':query,'field':address.evaluate('e=>({value:e.value,data:{...e.dataset},html:e.outerHTML})'),'events':p.evaluate('window.__rbProbeEvents'),'customer':p.evaluate('wp.data.select("wc/store/cart").getCustomerData()'),'panel':p.locator('.rollsbar-address-suggestions').inner_text()}
     raise
    require(suggested.value.status==200,'fresh suggestions '+query)
    payload=suggested.value.json()
    require(bool(payload.get('suggestions')),'provider candidates exist '+query)
    p.locator('.rollsbar-address-suggestions__item').first.wait_for(state='visible')
    p.wait_for_function('(display)=>document.querySelector(".rollsbar-address-suggestions__item")?.textContent===display',arg=payload['suggestions'][0]['display'])
    with p.expect_response(lambda r:'/rollsbar/v1/address-resolve' in r.url and r.request.method=='POST') as resolved:
     p.locator('.rollsbar-address-suggestions__item').first.click()
    response=resolved.value
    require(response.status==200,'provider resolve succeeds '+query)
    result=response.json();rule=result['delivery']
    provider=base64.b64decode(result['address_proof'].split('.')[0]);provider=json.loads(provider)['data']
    row={'query':query,'expected':minimum,'display':result['display'],'qc_geo':result['qc_geo'],'decision':rule,'identity':provider}
    report['cases'].append(row)
    if minimum is None:require(rule['status']!='resolved' and rule['minimum'] is None,'no invented minimum '+query)
    else:require(rule['status']=='resolved' and rule['minimum']==minimum,'actual provider minimum '+query+' = '+str(minimum))
    p.wait_for_function('(value)=>[...document.querySelectorAll("input[id$=address_1]")].some(e=>e.value===value)',arg=result['display'])
    p.wait_for_function('()=>!!wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum")')
    message=p.evaluate('wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum").message')
    if minimum is not None:require(str(minimum) in message.replace(' ','').replace('\u00a0',''),'native browser blocks below '+str(minimum))
    row['browser_message']=message
    print('PASS',query,rule,flush=True)
    if minimum==4000 or minimum is None:
     p.locator('[role=dialog]').evaluate('e=>e.scrollTop=0');p.screenshot(path=str(OUT/('address-'+str(len(report['cases']))+'.png')))
   for tier in [1200,1500,2000,2500,3000,3500,4000]:
    unique={r['display'] for r in report['cases'] if r['expected']==tier}
    require(len(unique)>=2,'two distinct live exact addresses at tier '+str(tier))
  browser.close()
 report['status']='PASS'
finally:
 (OUT/'address-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

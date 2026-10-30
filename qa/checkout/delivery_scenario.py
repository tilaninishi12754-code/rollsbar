"""Delivery/pickup UX gate with real Woo Blocks. Never submit an order."""
import json,sys,os,subprocess,re,time,hashlib
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
sys.stdout.reconfigure(encoding='utf8',line_buffering=True)
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'wordpress/deploy'))
from gate_b_browser import BASE,isolated_browser_page,add_first_simple_product,require,store_cart_state
from playwright.sync_api import sync_playwright
from request_guard import is_order_submission
from release_gate import AssetIdentity,release_assets
from delivery_native_fixture import DeliveryFixture
from delivery_test_context import delivery_page,settle_native
OUT=ROOT/'qa/visual-results/delivery-rules';OUT.mkdir(parents=True,exist_ok=True)
CAPTURE=ROOT/'qa/visual-results/checkout-direct'
LIVE='--live' in sys.argv
report={'status':'RUNNING','mode':'live' if LIVE else 'offline-native','release_sha':os.environ.get('ROLLSBAR_DEPLOY_SHA'),'checks':[],'submissions':[],'errors':[]}
locale=json.loads((CAPTURE/'locale.json').read_text(encoding='utf8')) if not LIVE else None
def hydrate(data):
 if isinstance(data,list):return [hydrate(x) for x in data]
 if not isinstance(data,dict):return data
 if 'countryData' in data:
  for k,v in locale.items():
   data['countryData']['RU']['locale'].setdefault(k,{}).update(v);data['defaultFields'].setdefault(k,{}).update(v)
  data['defaultFields']['email']['hidden']=True
  data['defaultFields']['rollsbar/privacy-consent']['required']=True
  for k in ['entrance','door-code','floor','apartment-office']:
   f=data['defaultFields']['rollsbar/'+k];f['optionalLabel']=f['label']
  data['defaultFields']['rollsbar/door-code'].update(label='Домофон',optionalLabel='Домофон')
  data['shippingMethodsExist']=True
  data['checkoutAllowsSignup']=False
 if 'billing_address' in data:data['billing_address'].update(country='RU',email='guest-shadow@checkout.rollsbar.invalid')
 if 'shipping_address' in data:data['shipping_address']['country']='RU'
 if data.get('method_id')=='pickup_location':data['name']='Самовывоз'
 if data.get('key')=='pickup_location':data['value']='Симферополь, Кечкеметская улица, 1'
 return {k:hydrate(v) for k,v in data.items()}

def visible(p,selector):
 return p.locator(selector).filter(visible=True).first

def mode(p,pickup):
 p.locator('.wc-block-checkout__shipping-method').wait_for(state='visible')
 target=p.locator('.wc-block-checkout__shipping-method [role="radio"]').nth(1 if pickup else 0)
 if not target.count():raise RuntimeError('Native fulfillment controls: '+p.locator('.wc-block-checkout__shipping-method').inner_html())
 target.click()
 p.wait_for_function('(pickup)=>wp.data.select("wc/store/checkout").prefersCollection()===pickup',arg=pickup)
 p.wait_for_function('()=>!wp.data.select("wc/store/cart").isCustomerDataUpdating()')
 settle_native(p)

fixture=None
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  if not LIVE:fixture=DeliveryFixture(ROOT,CAPTURE,hydrate)
  for width in [1440,701,700,390,320]:
   with delivery_page(browser,viewport={'width':width,'height':900},is_mobile=width<=700,has_touch=width<=700) as p:
    if fixture:p.context.route(BASE+'/**',fixture.route)
    identity=AssetIdentity(release_assets(os.environ['ROLLSBAR_DEPLOY_SHA']),BASE) if LIVE else None
    if identity:p.on('response',identity.observe)
    p.on('pageerror',lambda error:report['errors'].append(str(error)))
    def guard(route):
     if is_order_submission(route.request):report['submissions'].append(route.request.url);route.abort()
     else:route.fallback()
    p.context.route('**/*',guard)
    p.goto(BASE+'/',wait_until='domcontentloaded');add_first_simple_product(p)
    p.wait_for_function('()=>document.querySelector(".rollsbar-cart-link")')
    settle_native(p)
    p.goto(BASE+'/checkout/',wait_until='domcontentloaded')
    p.locator('[data-rollsbar-modal="1"]').wait_for(state='visible')
    p.locator('.wc-block-checkout__shipping-method').wait_for(state='visible')
    mode(p,False)
    p.wait_for_timeout(250)
    require(p.locator('.wp-block-woocommerce-checkout').count()==1,'one native Checkout lifecycle')
    server_cart=p.evaluate('async()=>await(await fetch("/wp-json/wc/store/v1/cart",{credentials:"same-origin"})).json()')
    shown=p.locator('.wc-block-checkout__sidebar .wc-block-components-totals-footer-item .wc-block-components-totals-item__value').inner_text()
    shown_amount=float(re.sub(r'[^0-9,.]','',shown).replace(',','.'))
    require(abs(shown_amount-int(server_cart['totals']['total_price'])/10**server_cart['totals']['currency_minor_unit'])<.001,'checkout visible total equals independent Store API total')
    require(all(item['name'] in p.locator('.wc-block-checkout__sidebar').inner_text() for item in server_cart['items']),'checkout summary contains authoritative cart products')
    require(p.locator('.rollsbar-checkout-map iframe').count()==1 and p.locator('.rollsbar-checkout-map').is_visible(),'one advisory map below delivery address')
    map_frame=p.locator('.rollsbar-checkout-map iframe').element_handle().content_frame()
    map_frame.wait_for_function('window.rollsbarMapReady===true')
    require(p.locator('.rollsbar-checkout-map').bounding_box()['y']>p.locator('#shipping-address_1').bounding_box()['y'],'map is placed after native address input')
    require(not p.locator('input[type="email"]').filter(visible=True).count(),'email absent')
    require(not p.locator('[id$="-city"]').filter(visible=True).count(),'locality absent')
    require(p.locator('.wc-block-checkout__add-note textarea').is_visible(),'native note always open')
    require(all('Уточнит менеджер' in text for text in p.locator('.rollsbar-delivery-terms').all_text_contents()) and p.locator('.rollsbar-delivery-terms').count()>0,'unknown delivery is not promised free in either native summary')
    require(not p.locator('.wc-block-checkout__add-note input[type="checkbox"]').is_visible(),'note checkbox absent')
    require(not p.locator('.wc-block-checkout__shipping-option').is_visible(),'single delivery rate has no duplicate selector')
    address=visible(p,'input[id$="-address_1"]');require(address.count()==1,'one customer address')
    require('Город, улица и дом' in address.locator('..').inner_text(),'single address label')
    for field in ['entrance','door-code','floor','apartment-office']:
     control=p.locator('#order-rollsbar-'+field)
     require(control.is_visible() and control.get_attribute('required') is None,'delivery optional '+field)
     require('необязательно' not in control.locator('..').inner_text(),'clean label '+field)
    first=visible(p,'input[id$="-first_name"]');phone=visible(p,'input[id$="-phone"]')
    require(not first.evaluate('e=>e.required') and phone.evaluate('e=>e.required'),'phone alone required; name optional')
    p.evaluate('''()=>{window.__rbPhoneOnlyPayload=null;wp.apiFetch.use((o,next)=>{if((o.path||o.url||'').includes('/wc/store/v1/checkout')&&(o.method||'GET').toUpperCase()==='POST'){window.__rbPhoneOnlyPayload=JSON.parse(JSON.stringify(o.data));return Promise.reject({code:'qa_stop',message:'QA stopped before HTTP',data:{status:400}});}return next(o);});}''')
    for entered,expected in [('8','+7'),('7','+7'),('89781234567','+79781234567'),('79781234567','+79781234567'),('+79781234567','+79781234567')]:
     phone.fill(entered);require(phone.input_value()==expected,'immediate phone prefix '+entered)
    first.fill('');phone.fill('');phone.blur()
    p.locator('.wc-block-components-checkout-place-order-button').click()
    p.wait_for_function('wp.data.select("wc/store/checkout").isIdle()')
    require(p.evaluate('window.__rbPhoneOnlyPayload') is None,'empty phone rejects request before native POST assembly')
    phone.fill('+79780000000')
    p.wait_for_function('()=>!wp.data.select("wc/store/cart").isCustomerDataUpdating()&&!wp.data.select("wc/store/checkout").isCalculating()')
    p.locator('.wc-block-components-checkout-place-order-button').click()
    p.wait_for_function('()=>document.activeElement?.id==="order-rollsbar-privacy-consent"&&wp.data.select("wc/store/checkout").isIdle()')
    require(p.evaluate('window.__rbPhoneOnlyPayload') is None,'unchecked consent blocks native request')
    require('согласие' in p.locator('.rollsbar-submit-feedback').inner_text(),'consent explanation beside native button')
    consent=p.locator('#order-rollsbar-privacy-consent')
    marker=p.locator('.rollsbar-consent-missing')
    require(marker.count()==1 and marker.evaluate('e=>getComputedStyle(e).backgroundColor==="rgb(255, 242, 242)"'),'consent block has distinct red background and outline')
    require(marker.evaluate('e=>{let r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight}'),'unchecked consent block scrolled into viewport')
    consent_out=OUT/'consent-feedback';consent_out.mkdir(exist_ok=True)
    p.screenshot(path=str(consent_out/f'consent-{width}.png'))
    consent.check()
    p.wait_for_function('!document.querySelector(".rollsbar-consent-missing")')
    require(True,'consent marker clears after explicit check')
    p.locator('.wc-block-components-checkout-place-order-button').click()
    p.wait_for_function('window.__rbPhoneOnlyPayload!==null')
    minimal=p.evaluate('window.__rbPhoneOnlyPayload')
    require(not minimal['billing_address']['first_name'] and not minimal['shipping_address']['address_1'] and minimal['billing_address']['phone']=='+79780000000','native phone-only payload with absent name and address')
    require(minimal['additional_fields'].get('rollsbar/privacy-consent') is True,'native callback retains explicit customer consent')
    p.wait_for_function('wp.data.select("wc/store/checkout").isIdle()')
    first.fill('Тест');phone.fill('+7')
    p.wait_for_function('!!wp.data.select("wc/store/validation").getValidationError("rollsbar-contact-phone")')
    require(True,'country prefix alone cannot satisfy required phone')
    phone.fill('+79780000000')
    p.wait_for_function('!wp.data.select("wc/store/validation").getValidationError("rollsbar-contact-phone")')
    require(p.evaluate('wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum")') is None,'unresolved address does not block callback')
    address.fill('Симферополь Гагарина 17')
    p.locator('.rollsbar-address-suggestions__item').first.click()
    p.wait_for_function("()=>document.querySelector('input[data-rollsbar-address-resolved]')")
    p.wait_for_function('(id)=>document.getElementById(id)?.parentNode.textContent.replace(/\s/g,"").includes("1200")',arg=address.get_attribute('id'))
    require(p.evaluate('!!wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum")'),'known below-minimum address is blocked')
    require(all('От' in text for text in p.locator('.rollsbar-delivery-terms').all_text_contents()),'below-minimum summaries do not promise free delivery')
    feedback=p.locator('.rollsbar-submit-feedback')
    require('Добавьте товаров' in feedback.inner_text(),'missing amount explained beside native button')
    p.evaluate('window.__rbPhoneOnlyPayload=null')
    p.locator('.wc-block-components-checkout-place-order-button').click()
    p.wait_for_function('wp.data.select("wc/store/checkout").isIdle()')
    require(p.evaluate('window.__rbPhoneOnlyPayload') is None,'below-minimum cart never assembles checkout POST')
    p.wait_for_function('wp.data.select("wc/store/checkout").isIdle()')
    if LIVE:require('Наличными или картой при получении' in p.locator('.wc-block-checkout__payment-method').inner_text(),'native receipt payment copy includes cash and card')
    require(p.evaluate('wp.data.select("wc/store/checkout").getExtensionData()["rollsbar-delivery"].address_proof')!='','native checkout carries signed address proof')
    if width==1440:
     query='Симферополь Лермонтова 16'
     with p.expect_response(lambda r:'/rollsbar/v1/address-suggestions' in r.url and parse_qs(urlsplit(r.url).query).get('query')==[query]) as fresh:
      address.fill(query)
     candidates=fresh.value.json()['suggestions']
     p.wait_for_function('(value)=>wp.data.select("wc/store/cart").getCustomerData().shippingAddress.address_1===value',arg=query)
     p.wait_for_function('(value)=>document.querySelector(".rollsbar-address-suggestions__item")?.textContent===value',arg=candidates[0]['display'])
     require(not p.evaluate('wp.data.select("wc/store/checkout").getExtensionData()["rollsbar-delivery"].address_proof'),'editing consumes latest value and clears old proof')
     p.locator('.rollsbar-address-suggestions__item').first.click()
     p.wait_for_function("()=>document.querySelector('input[data-rollsbar-address-resolved]')")
    modal=p.locator('[data-rollsbar-modal="1"]')
    geometry=modal.evaluate('e=>{let r=e.getBoundingClientRect(),s=getComputedStyle(e);return {x:r.x,y:r.y,width:r.width,height:r.height,radius:s.borderRadius,position:s.position,scrollHeight:e.scrollHeight,clientHeight:e.clientHeight}}')
    print('GEOMETRY',geometry,flush=True)
    require(abs(geometry['width']-min(1040,width-24))<2,'approved panel width')
    require(geometry['height']<=900*.92+2 and p.locator('.rollsbar-legal-page').evaluate('e=>getComputedStyle(e).position')=='fixed','fixed bounded modal')
    require(p.evaluate('document.documentElement.scrollWidth<=innerWidth'),'no horizontal overflow')
    modal.evaluate('e=>e.scrollTop=0');p.screenshot(path=str(OUT/f'delivery-{width}.png'))
    mode(p,True)
    require(not p.locator('.rollsbar-checkout-map').is_visible(),'pickup hides customer address map')
    require(not p.locator('input[id$="-address_1"]').filter(visible=True).count(),'pickup customer address absent')
    require(not p.locator('#order-rollsbar-entrance').is_visible(),'pickup details absent')
    require('Симферополь, Кечкеметская улица, 1' in p.locator('.wc-block-checkout__pickup-options').inner_text(),'exact pickup address')
    require(p.locator('.wc-block-checkout__pickup-options').bounding_box()['y']<p.locator('.wc-block-checkout__order-notes').bounding_box()['y'],'pickup address precedes comment')
    require(p.evaluate('wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum")') is None,'pickup no delivery requirement')
    contact=p.evaluate('wp.data.select("wc/store/cart").getCustomerData().billingAddress.phone') or ''
    ready=len(''.join(c for c in contact if c.isdigit()))>=10 and p.locator('#order-rollsbar-privacy-consent').is_checked()
    expected='Самовывоз по адресу: Симферополь, Кечкеметская улица, 1.' if ready else 'Оставьте телефон и отметьте согласие'
    require(expected in p.locator('.rollsbar-submit-feedback').inner_text(),'pickup feedback follows actual saved phone/consent state')
    require(not p.locator('#rollsbarAddressSuggestions').is_visible(),'pickup has no stale address list obscuring fulfillment controls')
    require(p.locator('input[value="cod"]').is_checked(),'native COD')
    modal.evaluate('e=>e.scrollTop=0');p.screenshot(path=str(OUT/f'pickup-{width}.png'))
    mode(p,False)
    require(visible(p,'input[id$="-address_1"]').count()==1,'delivery restored')
    if width==1440:
     p.evaluate('async()=>{const s=wp.data.select("wc/store/cart");await wp.data.dispatch("wc/store/cart").changeCartItemQuantity(s.getCartData().items[0].key,3)}')
     try:p.wait_for_function('()=>!wp.data.select("wc/store/validation").getValidationError("rollsbar-delivery-minimum")')
     except Exception:
      report['minimum_failure']={'validation':p.evaluate('wp.data.select("wc/store/validation").getValidationErrors()'),'customer':p.evaluate('wp.data.select("wc/store/cart").getCustomerData()'),'totals':p.evaluate('wp.data.select("wc/store/cart").getCartTotals()'),'proof':p.evaluate('wp.data.select("wc/store/checkout").getExtensionData()'),'body':p.locator('body').inner_text()}
      raise
     settle_native(p)
     p.wait_for_function('()=>{const terms=[...document.querySelectorAll(".rollsbar-delivery-terms")];return terms.length>0&&terms.every(e=>e.textContent==="Бесплатно")}')
     terms=p.locator('.rollsbar-delivery-terms').all_text_contents()
     if not all(text=='Бесплатно' for text in terms):
      report['qualified_failure']={'terms':terms,'totals':p.evaluate('wp.data.select("wc/store/cart").getCartTotals()'),'address':p.evaluate('wp.data.select("wc/store/cart").getCustomerData().shippingAddress.address_1')}
      print('QUALIFIED_FAILURE',report['qualified_failure'],flush=True)
     require(all(text=='Бесплатно' for text in terms),'qualified basket gets free delivery')
     for field,value in [('entrance','2'),('door-code','10'),('floor','3'),('apartment-office','4')]:p.locator('#order-rollsbar-'+field).fill(value)
     p.locator('.wc-block-checkout__add-note textarea').fill('Тест без отправки заказа')
     p.locator('#order-rollsbar-privacy-consent').check()
     p.wait_for_function('()=>!wp.data.select("wc/store/cart").isCustomerDataUpdating()&&!wp.data.select("wc/store/checkout").isCalculating()')
     p.evaluate('''()=>{window.__rbDeliveryPresubmit=null;wp.apiFetch.use((options,next)=>{
      if((options.path||options.url||'').includes('/wc/store/v1/checkout')&&(options.method||'GET').toUpperCase()==='POST'){
       window.__rbDeliveryPresubmit=JSON.parse(JSON.stringify(options.data));return Promise.reject({code:'rollsbar_qa_presubmit_stop',message:'QA: остановлено до HTTP, заказ не создавался.',data:{status:400}});
      }return next(options);
     });}''')
     p.locator('.wc-block-components-checkout-place-order-button').click()
     try:p.wait_for_function('window.__rbDeliveryPresubmit!==null')
     except Exception:
      report['presubmit_failure']={'validation':p.evaluate('wp.data.select("wc/store/validation").getValidationErrors()'),'customer':p.evaluate('wp.data.select("wc/store/cart").getCustomerData()'),'body':p.locator('body').inner_text()}
      p.screenshot(path=str(OUT/'presubmit-failed.png'))
      raise
     payload=p.evaluate('window.__rbDeliveryPresubmit')
     require(payload['extensions']['rollsbar-delivery']['address_proof']!='','actual native submit includes signed address proof')
     import base64
     confirmed=json.loads(base64.b64decode(payload['extensions']['rollsbar-delivery']['address_proof'].split('.')[0])) if LIVE else {'display':payload['shipping_address']['address_1']}
     require(payload['shipping_address']['address_1']==confirmed['display'],'native submission address equals signed provider confirmation')
     require(payload['payment_method']=='cod' and payload.get('create_account') is False,'actual native guest COD payload')
     require(payload['billing_address']['email'].endswith('@checkout.rollsbar.invalid'),'native email compatibility retained')
     require(payload['billing_address']['first_name']=='Тест' and re.sub(r'\D','',payload['billing_address']['phone'])=='79780000000','native identity and full phone retained without duplicated prefix')
     require(payload['customer_note']=='Тест без отправки заказа','native comment storage')
     require(payload['additional_fields']['rollsbar/privacy-consent'] is True,'native privacy consent')
     for field,value in [('entrance','2'),('door-code','10'),('floor','3'),('apartment-office','4')]:require(payload['additional_fields']['rollsbar/'+field]==value,'native optional field '+field)
     report['native_presubmit']={'status':'PASS','http_sent':False,'fields':list(payload),'proof_present':True}
    if not LIVE and width==1440:
     settle_native(p)
     keyboard_frame=p.locator('.rollsbar-checkout-map iframe').element_handle().content_frame()
     keyboard_frame.wait_for_function('window.rollsbarMapReady===true')
     keyboard_frame.locator('#map').focus();keyboard_frame.locator('#map').press('Escape')
     p.wait_for_url(BASE+'/',wait_until='domcontentloaded')
     require(True,'Escape in focused iframe returns from native checkout')
    if identity:identity.verify([])
    report['checks'].append({'width':width,'geometry':geometry,'status':'PASS'})
    print('PASS',width,flush=True)
  browser.close()
 if fixture:require(not fixture.unhandled,'all offline requests accounted for')
 require(not report['errors'] and not report['submissions'],'no JS errors or order submissions')
 report['status']='AUTOMATED_PASS_AWAITING_SCREENSHOT_REVIEW'
except Exception as e:
 report['failure']=repr(e)
 raise
finally:
 if fixture:fixture.close()
 (OUT/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

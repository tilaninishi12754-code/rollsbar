"""Final Direct Port native Blocks preview/live gates. Never submit checkout."""
import json,os,re,subprocess,sys,uuid,time
from pathlib import Path
from urllib.parse import unquote,quote
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from PIL import Image,ImageChops
import hashlib
from release_gate import AssetIdentity,release_assets
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'wordpress/deploy'))
from shadow_preview import choose as native_choose
from gate_b_browser import BASE,isolated_browser_page,add_first_simple_product,store_cart_state,require,first_visible
from request_guard import is_order_submission,effective_rest_method
from playwright.sync_api import sync_playwright
OUT=ROOT/'qa/visual-results/checkout-direct';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=subprocess.check_output(['git','show','5e7836e22110ec076603bb1fa2b12f8bb90ee756:index.html'],cwd=ROOT)
ASSETS=ROOT/'wordpress/wp-content/plugins/rollsbar-core/assets'
LIVE='--live' in sys.argv
OFFLINE='--local-native' in sys.argv
if LIVE and OFFLINE:raise ValueError('Choose live or local native fixture')
fixture=None
identity=AssetIdentity(release_assets(os.environ['ROLLSBAR_DEPLOY_SHA']),BASE) if LIVE else None
WIDTHS=[1440,701,700,390,320]
report={'run_id':str(uuid.uuid4()),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ASSETS/'css/checkout.css',ASSETS/'js/checkout.js',ASSETS.parent/'includes/class-rollsbar-checkout.php']},'release_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'mode':'live' if LIVE else 'offline-native' if OFFLINE else 'native-shadow','status':'RUNNING','checks':[],'submissions':[],'errors':[]}
(OUT/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  if self.path=='/reference.html':
   self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.end_headers();self.wfile.write(SOURCE)
  else:super().do_GET()
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)));Thread(target=server.serve_forever,daemon=True).start()
def hydrate(data):
 if isinstance(data,list):return [hydrate(v) for v in data]
 if not isinstance(data,dict):return data
 if 'countryData' in data:
  locale=json.loads((OUT/'locale.json').read_text(encoding='utf8'))
  for key,value in locale.items():
   data['countryData']['RU']['locale'].setdefault(key,{}).update(value)
   data['defaultFields'].setdefault(key,{}).update(value)
  data['defaultFields']['email']['hidden']=True
  data['defaultFields']['city']['optionalLabel']='Населённый пункт (необязательно)'
  for k in ['checkoutAllowsSignup','checkoutShowLoginReminder']:data[k]=False
  for f in ['rollsbar/entrance','rollsbar/door-code','rollsbar/floor','rollsbar/apartment-office']:
   if f in data.get('defaultFields',{}):data['defaultFields'][f]['required']=False
 if 'billing_address' in data:data['billing_address'].update({'country':'RU','email':'guest-shadow@checkout.rollsbar.invalid'})
 if 'shipping_address' in data:data['shipping_address']['country']='RU'
 if data.get('method_id')=='pickup_location':data['name']='Самовывоз (Симферополь, Кечкеметская улица, 1)'
 if data.get('key')=='pickup_location':data['value']='Симферополь, Кечкеметская улица, 1'
 if data.get('id')=='rollsbar/door-code':data.update({'label':'Домофон','optionalLabel':'Домофон (необязательно)'})
 return {k:hydrate(v) for k,v in data.items()}

def document(route):
 response=route.fetch();html=re.sub(r'<script type="speculationrules">.*?</script>','',response.text(),flags=re.S)
 pattern=r"var wcSettings = JSON.parse\( decodeURIComponent\( '([^']+)' \) \);"
 match=re.search(pattern,html);require(bool(match),'native Woo settings hydration found')
 data=hydrate(json.loads(unquote(match[1])));html=html[:match.start(1)]+quote(json.dumps(data,ensure_ascii=False),safe='')+html[match.end(1):]
 html=html.replace('window.rollsBarCheckoutConfig={','window.rollsBarCheckoutConfig={"internalEmail":"guest-shadow@checkout.rollsbar.invalid",')
 # Mandatory contact block remains; email is hidden by native field configuration.
 route.fulfill(response=response,body=html)

def from_cart(page):
 page.evaluate("scrollTo({top:900,behavior:'instant'})")
 trigger=first_visible(page,['.rollsbar-cart-link','[data-rollsbar-orderbar]:not([hidden])','[data-rollsbar-mobile-cart]:not([hidden])'])
 require(trigger is not None,'visible storefront cart trigger')
 trigger.click()
 page.locator('#rollsbarCartDrawer').wait_for(state='visible')
 page.wait_for_function("document.querySelector('.rollsbar-cart-drawer__panel')?.getAttribute('aria-busy')==='false' && document.querySelector('.rollsbar-drawer-checkout')?.getAttribute('aria-disabled')==='false'")
 print('checkout href',page.locator('.rollsbar-drawer-checkout').get_attribute('href'),flush=True)
 page.locator('.rollsbar-drawer-checkout').click()
 page.wait_for_url(BASE+'/checkout/',wait_until='commit')
 page.locator('[data-rollsbar-modal="1"]').wait_for(state='visible')
 try:page.locator('#billing-first_name').wait_for(state='visible')
 except Exception:
  (OUT/'failed-checkout.html').write_text(page.content(),encoding='utf8')
  page.screenshot(path=str(OUT/'failed-checkout.png'))
  report['failed_checkout']={'body':page.locator('body').inner_text(),'cart':store_cart_state(page)}
  raise
 require(page.locator('.wp-block-woocommerce-checkout').count()==1,'first cart activation opens one native modal')
 require(page.evaluate('wcSettings.checkoutData.order_id===0'),'isolated fresh checkout has no order to update')

def choose(page,query,exact):
 try:return native_choose(page,query,exact)
 except Exception:
  # Preserve evidence before isolated cleanup/navigation destroys the field.
  report['address_failure']={'query':query,'field':page.locator('#billing-address_1').evaluate('e=>({value:e.value,html:e.outerHTML,focused:document.activeElement===e,status:e.parentElement.innerText})'),'input_events':page.evaluate('window.__rbAddressInputEvents||[]')}
  page.screenshot(path=str(OUT/'address-failed.png'))
  raise

def geom(p,selector):
 return p.locator(selector).evaluate('e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {x:r.x,y:r.y,width:r.width,height:r.height,radius:s.borderRadius,padding:s.padding,shadow:s.boxShadow,overflow:s.overflowY,scrollHeight:e.scrollHeight,clientHeight:e.clientHeight}}')

def map_ready(page,reveal=False):
 if reveal:page.locator('.rollsbar-checkout-map iframe').scroll_into_view_if_needed()
 frame=page.locator('.rollsbar-checkout-map iframe').element_handle().content_frame()
 require(frame is not None,'native map frame attached')
 # Yandex inserts each tile image only after download. "All current images
 # complete" can therefore pass with a single tile and leave most map blank.
 # Measure the union of loaded tile rectangles over the whole visible map.
 coverage="""()=>{
  const w=innerWidth,h=innerHeight;
  const rects=[...document.images].filter(i=>i.src.includes('renderer-tiles.maps.yandex.ru/tiles')&&i.complete&&i.naturalWidth>0).map(i=>i.getBoundingClientRect()).map(r=>({l:Math.max(0,r.left),r:Math.min(w,r.right),t:Math.max(0,r.top),b:Math.min(h,r.bottom)})).filter(r=>r.r>r.l&&r.b>r.t);
  const xs=[...new Set([0,w,...rects.flatMap(r=>[r.l,r.r])])].sort((a,b)=>a-b);let area=0;
  for(let n=1;n<xs.length;n++){
   const l=xs[n-1],r=xs[n],ys=rects.filter(t=>t.l<=l&&t.r>=r).map(t=>[t.t,t.b]).sort((a,b)=>a[0]-b[0]);let end=0,covered=0;
   for(const [top,bottom] of ys){covered+=Math.max(0,bottom-Math.max(top,end));end=Math.max(end,bottom);}
   area+=(r-l)*covered;
  }
  return area/(w*h)>=0.995;
 }"""
 try:frame.wait_for_function(coverage)
 except Exception:
  report['map_failure']={'url':frame.url,'state':frame.evaluate("({ready:document.readyState,images:[...document.images].map(i=>({url:i.src,complete:i.complete,width:i.naturalWidth}))})")}
  page.locator('.rollsbar-checkout-map').screenshot(path=str(OUT/'map-failed.png'))
  raise
 frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
 require(True,'real Yandex map tiles loaded before screenshot')
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  report['browser_version']=browser.version
  ref=browser.new_page(viewport={'width':1440,'height':1000})
  ref.goto(f'http://127.0.0.1:{server.server_port}/reference.html',wait_until='load')
  if ref.locator('#cookieAccept').is_visible():ref.locator('#cookieAccept').click()
  ref.evaluate("document.querySelector('#checkoutModal').classList.add('open');document.body.style.overflow='hidden'")
  with isolated_browser_page(browser,viewport={'width':1440,'height':1000},locale='ru-RU',service_workers='block') as p:
   # Batch-specific guard understands WP 7.1.3's POST + method override. The
   # historical baseline helper stays byte-for-byte unchanged and independently
   # tested. Real native POST and all legacy checkout POST remain blocked.
   p.context.route('**/*',lambda r:r.abort() if is_order_submission(r.request) else r.continue_())
   if LIVE:p.on('response',identity.observe)
   p.on('request',lambda r:print('store request',r.url,flush=True) if '/wc/store/' in r.url else None)
   def ajax_trace(response):
    if 'wc-ajax=rollsbar_cart' in response.url:
     # Diagnostic only; the asserted add/read helpers consume their own bodies.
     # A response from the previous document may already be discarded here.
     print('native AJAX response',round(time.monotonic(),2),response.status,flush=True)
   p.on('response',ajax_trace)
   # Diagnostic journal only: no response substitution, retry or timeout change.
   report['address_transport']=[]
   def address_event(kind,request,status=None):
    if '/rollsbar/v1/address-' in request.url:
     report['address_transport'].append({'event':kind,'url':request.url,'method':request.method,'status':status,'elapsed':round(time.monotonic(),3)})
   p.on('request',lambda r:address_event('request',r))
   p.on('response',lambda r:address_event('response',r.request,r.status))
   p.on('requestfailed',lambda r:address_event('failed',r,r.failure))
   p.add_init_script("window.__rbAddressInputEvents=[];document.addEventListener('input',e=>{if(e.target.id==='billing-address_1')window.__rbAddressInputEvents.push({value:e.target.value,programmatic:e.target.dataset.rollsbarAddressProgrammatic||'',time:performance.now()})},true)")
   p.on('pageerror',lambda e:report['errors'].append(str(e)))
   def checkout_guard(route):
    if is_order_submission(route.request):
     report['submissions'].append(route.request.url);route.abort()
    else:
     if effective_rest_method(route.request) in ['PUT','PATCH']:
      report.setdefault('native_session_updates',[]).append({'url':route.request.url,'transport_method':route.request.method,'rest_method':effective_rest_method(route.request)})
     route.fallback()
   p.route('**/wc/store/v1/checkout*',checkout_guard)
   if OFFLINE:
    from native_fixture import NativeFixture
    fixture=NativeFixture(ROOT,OUT,hydrate)
    p.context.route('https://staging.rollsbar.ru/**',fixture.route)
   if not LIVE and not OFFLINE:
    # Speculation Rules document prefetch bypasses Playwright navigation routes.
    # Only the shadow home response omits that prefetch hint; live is untouched.
    def shadow_home(route):
     response=route.fetch();html=re.sub(r'<script type="speculationrules">.*?</script>','',response.text(),flags=re.S)
     html=html.replace('</body>','<script>'+(OUT/'return-ui.js').read_text(encoding='utf8')+'</script></body>')
     route.fulfill(response=response,body=html)
    p.context.route(re.compile(r'^https://staging\.rollsbar\.ru/$'),shadow_home)
    p.context.route('**/checkout/',document)
    def cart_response(route):
     response=route.fetch();data=hydrate(response.json());(OUT/'last-response.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf8');print('hydrated response',route.request.url,flush=True);route.fulfill(response=response,json=data)
    p.route('**/wc/store/v1/cart?*',cart_response)
    p.route('**/wc/store/v1/cart',cart_response)
    p.route('**/wc/store/v1/cart/update-customer*',cart_response)
    p.route('**/wc/store/v1/batch*',cart_response)
    p.route('**/wc/store/v1/checkout*',lambda r: (report['submissions'].append(r.request.url),r.abort()) if is_order_submission(r.request) else cart_response(r))
    for asset,mime in [('css/checkout.css','text/css'),('js/checkout.js','application/javascript')]:
     p.route('**/rollsbar-core/assets/'+asset+'*',lambda r,request,a=asset,m=mime:r.fulfill(status=200,content_type=m,body=(ASSETS/a).read_bytes()))
   def navigation_trace(route):
    if route.request.is_navigation_request():print('navigation request',route.request.url,flush=True)
    route.fallback()
   p.context.route('**/*',navigation_trace)
   p.bring_to_front();p.goto(BASE+'/',wait_until='domcontentloaded')
   print('initial visibility',p.evaluate('document.visibilityState'),flush=True)
   try:
    p.wait_for_function("document.querySelector('.rollsbar-product-card')?.getAttribute('aria-busy')==='false' && document.querySelector('.rollsbar-product-card [data-rollsbar-cart-delta=\"1\"]')?.disabled===false")
    if LIVE:
     rules=json.loads(p.locator('script[type="speculationrules"]').inner_text())
     rule_text=json.dumps(rules)
     require(all(path in rule_text for path in ['/checkout/*','/cart/*','/product/*']),'native homepage speculation rules exclude stateful Woo documents')
     report['native_speculation_rules']=rules
    add_first_simple_product(p)
   except Exception:
    report['initial_cart_diagnostic']=p.evaluate("({hidden:document.hidden,status:document.querySelector('.rollsbar-cart-status')?.textContent,busy:document.querySelector('.rollsbar-product-card')?.getAttribute('aria-busy'),config:!!window.rollsbarCart})")
    print('initial cart diagnostic',report['initial_cart_diagnostic'],flush=True);raise
   from_cart(p);p.locator('#billing-phone').wait_for();p.wait_for_timeout(2000)
   if LIVE:identity.verify([])
   (OUT/'candidate.html').write_text(p.content(),encoding='utf8')
   print('protected native country/email context seeded')
   for width in WIDTHS:
    height=1000 if width>700 else 844
    p.set_viewport_size({'width':width,'height':height});ref.set_viewport_size({'width':width,'height':height});p.locator('[role=dialog]').evaluate('e=>e.scrollTop=0');p.wait_for_timeout(500)
    # Locator.click invokes CDP scrollIntoView, which scrolls this already visible
    # heading by 23px after a reopen. A real pointer hit leaves the panel at top.
    p.bring_to_front()
    heading=p.locator('.rollsbar-checkout-title').bounding_box()
    p.mouse.click(heading['x']+10,heading['y']+10)
    ref.locator('.checkout-head h2').click();p.bring_to_front()
    require(p.locator('[role=dialog]').evaluate('e=>e.scrollTop')==0,'visible heading pointer hit preserves modal top')
    require(p.locator('.wc-block-components-notice-banner,.wc-block-components-notice-snackbar').count()==0,'clean checkout has no stale native cart notices')
    map_ready(p)
    shell=geom(p,'.rollsbar-legal-page > .rollsbar-shell');reference=geom(ref,'.checkout-panel')
    p.screenshot(path=str(OUT/f'candidate-{width}.png'));ref.screenshot(path=str(OUT/f'reference-{width}.png'))
    diff=ImageChops.difference(Image.open(OUT/f'candidate-{width}.png').convert('RGB'),Image.open(OUT/f'reference-{width}.png').convert('RGB'));diff.save(OUT/f'diff-{width}.png')
    pixels=list(diff.get_flattened_data());ratio=sum(max(px)>25 for px in pixels)/len(pixels)
    row={'width':width,'candidate':shell,'reference':reference,'pixel_difference_ratio':ratio,'composition':{}};report['checks'].append(row)
    for label,candidate_selector,source_selector in [('name','#billing-first_name','input[name=name]'),('phone','#billing-phone','input[name=phone]'),('map','.rollsbar-checkout-map iframe','#checkoutSchematicMap')]:
     measured=geom(p,candidate_selector);original=geom(ref,source_selector);row['composition'][label]={'candidate':measured,'reference':original}
     require(abs(measured['width']-original['width'])<=2,label+' immutable composition width '+str(width))
     require(abs(measured['y']-original['y'])<=2,label+' immutable composition position '+str(width))
    require(p.locator('.rollsbar-checkout-backdrop').evaluate("e=>getComputedStyle(e).backgroundColor==='rgba(0, 0, 0, 0.46)' && getComputedStyle(e).backdropFilter==='blur(4px)'"),'immutable backdrop')
    close_box=geom(p,'.rollsbar-legal-page__back');source_close=geom(ref,'.checkout-head .close');row['close']={'candidate':close_box,'reference':source_close}
    require(all(abs(close_box[k]-source_close[k])<=1 for k in ['x','y','width','height']),'immutable close geometry '+str(width))
    require(p.locator('.rollsbar-legal-page__back').evaluate("e=>{const s=getComputedStyle(e,'::after');return parseFloat(s.width)>=44&&parseFloat(s.height)>=44}"),'close target extends to 44px without changing source layout')
    require(abs(shell['width']-reference['width'])<=1,'immutable panel width '+str(width))
    require(abs(shell['y']-reference['y'])<=1,'immutable panel vertical position '+str(width))
    require(shell['radius']==reference['radius'] and shell['padding']==reference['padding'] and shell['shadow']==reference['shadow'],'immutable panel surface '+str(width))
    require(shell['overflow']=='auto' and shell['scrollHeight']>shell['clientHeight'],'internal modal scroll '+str(width))
    require(p.evaluate('getComputedStyle(document.body).overflow')=='hidden','body scroll locked')
    require(p.evaluate('document.documentElement.scrollWidth-innerWidth')<=1,'no page overflow')
    require(p.locator('#email,#billing-last_name,#billing-state,#billing-postcode').count()==0,'no disallowed native customer fields')
    country=p.locator('#billing-country')
    require(country.count()==1 and not country.is_visible() and country.input_value()=='RU' and country.is_enabled(),'country is native valid RU internal control, absent from customer UI')
    for key in ['first_name','phone','address_1']:
     require(p.locator('#billing-'+key).is_visible() and p.locator('#billing-'+key).get_attribute('required') is not None,key+' required')
    require(p.locator('#billing-city').get_attribute('required') is None,'locality optional')
    require(p.locator('.wc-block-checkout__sidebar').is_visible(),'one native summary lane')
    summary_title=p.locator('.wc-block-checkout__sidebar .wc-block-components-checkout-order-summary__title')
    require(summary_title.get_attribute('role')!='button' or summary_title.get_attribute('aria-expanded')=='true','native summary initially expanded like source')
    totals=p.evaluate("async()=>{const r=await fetch('/wp-json/wc/store/v1/cart',{credentials:'same-origin'});return (await r.json()).totals}")
    displayed=p.locator('.wc-block-checkout__sidebar .wc-block-components-totals-footer-item .wc-block-components-totals-item__value').inner_text()
    number=float(re.sub(r'[^0-9,.]','',displayed).replace(',','.'))
    require(abs(number-int(totals['total_price'])/(10**totals['currency_minor_unit']))<0.001,'visible total equals authoritative Store API total')
    unit=p.locator('.wc-block-checkout__sidebar .wc-block-components-order-summary-item__individual-prices').first.inner_text()
    require(abs(float(re.sub(r'[^0-9,.]','',unit).replace(',','.'))-number)<0.001,'one-item native unit price equals its authoritative total')
    require(p.locator('.wc-block-checkout__pickup-options').inner_text().find('Симферополь, Кечкеметская улица, 1')>=0,'pickup exact canonical address')
    require(p.locator('input[value="cod"]').is_checked(),'native COD selected')
    require(not any(t in p.locator('.wc-block-checkout__form').inner_text() for t in ['Email','Контактная информация','Вы оформляете заказ как гость']),'no customer email/contact/guest copy')
    for key in ['entrance','door-code','floor','apartment-office']:
     require(p.locator('#order-rollsbar-'+key).get_attribute('required') is None,key+' optional')
    for key in ['first_name','phone','address_1']:
     control=p.locator('#billing-'+key);old=control.input_value();control.fill('')
     require(control.evaluate('e=>e.validity.valueMissing'),'empty '+key+' has native required validation')
     if old:control.fill(old)
    action=p.locator('.wc-block-components-checkout-place-order-button');action.scroll_into_view_if_needed();action.click(trial=True)
    require(action.evaluate('e=>{const r=e.getBoundingClientRect(),t=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return e===t||e.contains(t)}'),'native CTA hit target')
    require(action.bounding_box()['height']>=44,'CTA minimum hit height')
    ref.locator('.checkout-summary button[type=submit]').scroll_into_view_if_needed()
    p.screenshot(path=str(OUT/f'candidate-{width}-cta.png'));ref.screenshot(path=str(OUT/f'reference-{width}-cta.png'))
    ImageChops.difference(Image.open(OUT/f'candidate-{width}-cta.png').convert('RGB'),Image.open(OUT/f'reference-{width}-cta.png').convert('RGB')).save(OUT/f'diff-{width}-cta.png')
    ref.locator('.checkout-panel').evaluate('e=>e.scrollTop=0')
    p.locator('[role=dialog]').evaluate('e=>e.scrollTop=0')
    p.mouse.move(shell['x']+5,height/2);p.mouse.wheel(0,400);p.wait_for_timeout(200)
    require(p.evaluate('scrollY')==0 and p.locator('[role=dialog]').evaluate('e=>e.scrollTop')>0,'wheel scrolls modal only')
    p.locator('[role=dialog]').evaluate('e=>e.scrollTop=0')
    p.locator('.rollsbar-legal-page__back').click();p.wait_for_url(BASE+'/',wait_until='domcontentloaded')
    p.wait_for_function("document.querySelector('.rollsbar-product-card')?.getAttribute('aria-busy')==='false'")
    p.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    require(p.evaluate('scrollY')==900,'close preserves storefront scroll position after native header/cart initialization');from_cart(p)
   p.locator('#order-notes input[type=checkbox]').check()
   note=p.locator('#order-notes textarea');note.wait_for(state='visible')
   require(note.get_attribute('required') is None and note.count()==1,'one native optional customer note')
   note.fill('Комментарий без отправки заказа')
   require(note.input_value()=='Комментарий без отправки заказа','native customer note editable')
   report['dadata']=[choose(p,'Симферополь Кечкеметская 1',True)]
   map_ready(p,reveal=True)
   p.locator('.rollsbar-checkout-map').screenshot(path=str(OUT/'dadata-exact.png'))
   report['dadata'].append(choose(p,'Симферополь Киевская',False))
   map_ready(p,reveal=True)
   p.locator('.rollsbar-checkout-map').screenshot(path=str(OUT/'dadata-low-precision.png'))
   cart=store_cart_state(p);require(cart['itemsCount']==1,'cart summary retains exact isolated native cart item')
   p.locator('[role=dialog]').evaluate('e=>e.scrollTop=0');p.locator('.rollsbar-legal-page__back').focus();p.keyboard.press('Shift+Tab')
   require(p.locator('[role=dialog]').evaluate('e=>e.contains(document.activeElement)'),'focus remains in modal')
   p.keyboard.press('Escape');p.wait_for_url(BASE+'/',wait_until='domcontentloaded')
   p.locator('.rollsbar-header').wait_for(state='visible')
   require(p.locator('.rollsbar-header').is_visible(),'Escape returns to storefront')
   from_cart(p)
   require(p.locator('.wp-block-woocommerce-checkout').count()==1,'reopen has one native checkout lifecycle')
   p.locator('.rollsbar-checkout-backdrop').click(position={'x':1,'y':1});p.wait_for_url(BASE+'/',wait_until='domcontentloaded')
   p.goto(BASE+'/checkout/',wait_until='domcontentloaded');p.locator('[role=dialog]').wait_for()
   require(p.locator('[role=dialog]').count()==1,'direct checkout entry remains modal')
   # Exercise Woo's real submit assembly, stopping in public apiFetch middleware
   # before HTTP. The independent route guard still aborts any escaped POST.
   p.locator('#billing-first_name').fill('Тест')
   p.locator('#billing-phone').fill('+79780000000')
   p.locator('#billing-city').fill('')
   p.locator('#billing-address_1').fill('Симферополь, Кечкеметская улица, 1')
   for key,value in [('entrance','2'),('door-code','10'),('floor','3'),('apartment-office','4')]:p.locator('#order-rollsbar-'+key).fill(value)
   p.locator('#order-notes input[type=checkbox]').check()
   p.locator('#order-notes textarea').fill('Тест без создания заказа')
   p.locator('#order-rollsbar-privacy-consent').check()
   p.evaluate("""() => {
    window.__rollsbarPresubmit=null;window.__rollsbarSubmitCount=0;
    wp.apiFetch.use((options,next)=>{
     const path=options.path||options.url||'';
     if(path.includes('/wc/store/v1/checkout')&&(options.method||'GET').toUpperCase()==='POST'){
      window.__rollsbarPresubmit=JSON.parse(JSON.stringify(options.data));window.__rollsbarSubmitCount++;
      return Promise.reject({code:'rollsbar_qa_presubmit_stop',message:'QA: запрос остановлен до HTTP, заказ не создавался.',data:{status:400}});
     }
     return next(options);
    });
   }""")
   p.locator('.wc-block-components-checkout-place-order-button').click()
   p.wait_for_function('window.__rollsbarPresubmit!==null')
   payload=p.evaluate('window.__rollsbarPresubmit');report['native_presubmit_payload']=payload
   require(p.evaluate('window.__rollsbarSubmitCount')==1,'one native submit assembly, stopped before HTTP')
   require(payload['billing_address']['email'].endswith('@checkout.rollsbar.invalid'),'native submission carries internal compatible email without customer input')
   require(payload.get('create_account') is False and payload['payment_method']=='cod','native guest COD payload without account creation')
   require(payload['billing_address']['country']=='RU' and payload['shipping_address']['country']=='RU' and payload['billing_address']['city']=='','native internal country RU submitted normally, optional locality empty')
   require(payload['customer_note']=='Тест без создания заказа','native customer note storage contract')
   require(payload['additional_fields']['rollsbar/privacy-consent'] is True,'native explicit privacy consent contract')
   for key,value in [('entrance','2'),('door-code','10'),('floor','3'),('apartment-office','4')]:require(payload['additional_fields']['rollsbar/'+key]==value,'native Additional Checkout Fields payload '+key)
   if LIVE:
    require(not identity.errors,'live asset responses readable')
    for asset,body in identity.expected.items():
     rows=[r for r in identity.records if r['asset']==asset]
     require(bool(rows) and all(r['status']==200 and r['sha256']==hashlib.sha256(body).hexdigest() for r in rows),'all reopened native assets match application SHA: '+asset)
    report['asset_identity']=identity.records
   require(not report['submissions'],'zero order submissions');require(not report['errors'],'no JS errors')
  browser.close()
 if fixture:
  report['fixture_unhandled']=fixture.unhandled
  require(not fixture.unhandled,'all offline native requests satisfied by declared fixtures')
 require(all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in report['source_sha256'].items()),'application bytes unchanged throughout this gate')
 report['status']='AUTOMATED_PASS_AWAITING_SCREENSHOT_REVIEW'
except Exception as error:
 report['status']='FAIL';report['failure']=str(error);raise
finally:
 if fixture:
  report['fixture_unhandled']=fixture.unhandled
  fixture.close()
 (OUT/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');server.shutdown();server.server_close()

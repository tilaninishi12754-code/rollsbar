"""Candidate-only preview on real staging; never deploys or submits an order.

Uses the accepted S1-R3Q isolated context, exact-item polling and final cleanup.
Browser response overrides replace only checkout.css and checkout.js.
This is not a baseline generator or proof of deployed candidate code.
"""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'wordpress/deploy'))
from gate_b_browser import (BASE, sync_playwright, isolated_browser_page,
                            add_first_simple_product, require, store_cart_state)

OUT = ROOT / 'qa/visual-results/checkout-parity'
ASSETS = ROOT / 'wordpress/wp-content/plugins/rollsbar-core/assets'


def snapshot(page):
    return page.locator('.wc-block-checkout__form input, .wc-block-checkout__form select').evaluate_all(r"""els => els.map(e => ({
      id:e.id.replace(/^checkbox-control-\d+$/, 'native-generated-checkbox'), type:e.type, required:e.required, visible:!!e.getClientRects().length
    }))""")


def measure(page):
    return page.evaluate("""() => {
      const selectors={surface:'.rollsbar-legal-page > .rollsbar-shell', form:'.wc-block-checkout__main',
        summary:'.wp-block-woocommerce-checkout-order-summary-block', map:'.rollsbar-checkout-map', suggestions:'.rollsbar-address-suggestions:not([hidden])'};
      const m={page:Math.max(0,document.documentElement.scrollWidth-innerWidth)};
      for(const [name,selector] of Object.entries(selectors)){
        const e=[...document.querySelectorAll(selector)].find(e=>e.getClientRects().length);
        if(!e){m[name]=null;continue;}
        const r=e.getBoundingClientRect();
        m[name]=Math.max(0,e.scrollWidth-e.clientWidth,Math.ceil(r.right-innerWidth),Math.ceil(-r.left));
      }
      return m;
    }""")


def capture(page, name, metrics):
    page.locator('.rollsbar-checkout-map').scroll_into_view_if_needed()
    page.wait_for_timeout(650)
    # OOPIF compositing in full-page screenshots may omit offscreen map tiles.
    # Capture the actual visible map separately, before the structural overview.
    page.locator('.rollsbar-checkout-map').screenshot(path=str(OUT/(name+'-map.png')))
    page.evaluate('window.scrollTo(0,0)')
    page.wait_for_timeout(150)
    values=measure(page)
    if any(v and v>0 for v in values.values()):
        page.screenshot(path=str(OUT/(name+'-overflow.png')),full_page=True)
        print('OVERFLOW '+json.dumps(page.locator('.wc-block-checkout__main *').evaluate_all("""els=>els.filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>({tag:e.tagName,cls:e.className,sw:e.scrollWidth,cw:e.clientWidth,box:e.getBoundingClientRect().toJSON()}))"""),ensure_ascii=False))
    require(all(v == 0 for v in values.values() if v is not None), name+': horizontal overflow '+str(values))
    metrics[name]=values
    page.screenshot(path=str(OUT/(name+'.png')), full_page=True)
    page.screenshot(path=str(OUT/(name+'-top.png')))


def geometry(page):
    return page.locator('.rollsbar-legal-page > .rollsbar-shell, .wc-block-checkout__main, .wc-block-checkout__sidebar, .wc-block-components-checkout-step, .wc-block-components-address-form, .rollsbar-checkout-map, .wp-block-woocommerce-checkout-order-summary-block').evaluate_all("""els=>els.filter(e=>e.getClientRects().length).map(e=>({
      cls:e.className, text:e.innerText.slice(0,100), rect:e.getBoundingClientRect().toJSON(),
      padding:getComputedStyle(e).padding, gap:getComputedStyle(e).gap
    }))""")


def choose(page, query, exact):
    address=page.locator('#billing-address_1')
    with page.expect_response(lambda r:'/address-suggestions' in r.url and parse_qs(urlsplit(r.url).query).get('query')==[query]) as response:
        address.fill(query)
    payload=response.value.json()
    require(response.value.status==200 and bool(payload.get('suggestions')),'fresh suggestions match current query')
    items=page.locator('.rollsbar-address-suggestions__item')
    items.first.wait_for(state='visible')
    page.wait_for_function('(display)=>document.querySelector(".rollsbar-address-suggestions__item")?.textContent===display',arg=payload['suggestions'][0]['display'])
    display=items.first.inner_text()
    require('Россия' not in display and 'Укра' not in display,'DaData display excludes country labels')
    items.first.click()
    page.wait_for_function("""exact => {
      const e=document.querySelector('#billing-address_1');
      return e.dataset.rollsbarAddressResolved==='1' && e.dataset.rollsbarAddressAutoZone===(exact?'1':'0');
    }""",arg=exact)
    card=page.locator('.rollsbar-checkout-map')
    require(card.get_attribute('data-exact')==('1' if exact else '0'),'map precision follows DaData')
    src=card.locator('iframe').get_attribute('src')
    if exact:
        require('&pt=' in src,'exact DaData result visualized as point')
        require(address.get_attribute('data-rollsbar-address-qc-geo')=='0','exact qc_geo=0')
        require(parse_qs(urlsplit(src).query)['ll']==[address.get_attribute('data-rollsbar-address-lon')+','+address.get_attribute('data-rollsbar-address-lat')],'map coordinates equal DaData result, without inference')
    else:
        require('&pt=' not in src,'low precision has no customer point')
        require(page.locator('.rollsbar-address-status.is-warning').is_visible(),'low precision clarification visible')
    return {'display':display,'qc_geo':address.get_attribute('data-rollsbar-address-qc-geo'),'map_src':src}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={'kind':'CANDIDATE SHADOW PREVIEW — NOT DEPLOYED','metrics':{},'page_errors':[], 'order_submission_requests':[],
            'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'asset_substitutions':[], 'baseline_geometry':{}, 'candidate_geometry':{}}
    def substitute(route, relative, mime):
        body=(ASSETS/relative).read_bytes()
        report['asset_substitutions'].append({'url':route.request.url,'asset':relative,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)})
        route.fulfill(status=200,content_type=mime,body=body)
    try:
        with sync_playwright() as pw:
            channel=os.environ.get('PLAYWRIGHT_CHANNEL', 'chrome' if sys.platform=='win32' else '')
            browser=pw.chromium.launch(headless=True,**({'channel':channel} if channel else {}))
            try:
                with isolated_browser_page(browser,viewport={'width':1440,'height':1000},locale='ru-RU') as page:
                    page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                    page.on('request',lambda r:report['order_submission_requests'].append(r.url) if r.method=='POST' and ('/wc/store/v1/checkout' in r.url or 'wc-ajax=checkout' in r.url) else None)
                    page.goto(BASE+'/',wait_until='domcontentloaded')
                    product=add_first_simple_product(page)
                    page.goto(BASE+'/checkout/',wait_until='domcontentloaded')
                    page.locator('#billing-phone').wait_for()
                    page.wait_for_timeout(1800)
                    before=snapshot(page)
                    report['native_fields']=before
                    (OUT/'native.html').write_text(page.content(),encoding='utf-8')
                    for width in [1440,1024,701,700,390,320]:
                        page.set_viewport_size({'width':width,'height':1000 if width>700 else 844})
                        page.wait_for_timeout(500)
                        title=page.locator('.wc-block-components-checkout-order-summary__title')
                        if title.get_attribute('role')=='button' and title.get_attribute('aria-expanded')=='false': title.click()
                        capture(page,f'baseline-{width}',report['metrics'])
                        report['baseline_geometry'][str(width)]=geometry(page)
                        page.locator('.wc-block-components-checkout-place-order-button').scroll_into_view_if_needed()
                        page.screenshot(path=str(OUT/f'baseline-{width}-cta.png'))
                    page.set_viewport_size({'width':1440,'height':1000})
                    # Reload with one candidate script, avoiding two copies of the event listeners.
                    page.route('**/rollsbar-core/assets/js/checkout.js*',lambda route:substitute(route,'js/checkout.js','application/javascript'))
                    page.route('**/rollsbar-core/assets/css/checkout.css*',lambda route:substitute(route,'css/checkout.css','text/css'))
                    page.reload(wait_until='domcontentloaded')
                    page.locator('.rollsbar-checkout-map').wait_for()
                    page.wait_for_timeout(2000)
                    after=snapshot(page)
                    report['candidate_fields']=after
                    require(after==before,f'candidate preserves all {len(before)} native inputs/selects and required/visible status (generated checkbox serial normalized)')
                    require({a['asset'] for a in report['asset_substitutions']}=={'js/checkout.js','css/checkout.css'},'both local candidate assets actually substituted')
                    report['cart']=store_cart_state(page)
                    require(product in page.locator('.wc-block-checkout__sidebar').inner_text(),'native summary contains exact product')
                    phone=page.locator('#billing-phone')
                    phone.focus()
                    require(phone.input_value().strip()=='+7','initial +7 preserved')
                    phone.fill('89781234567');phone.blur()
                    require(phone.input_value().startswith('+7 '),'leading 8 normalizes to +7')
                    require(page.locator('#order-rollsbar-privacy-consent').get_attribute('required') is not None,'privacy remains required')
                    require(page.locator('input[value="pickup_location:0"]').is_checked(),'native pickup selected')
                    require(page.locator('input[value="cod"]').is_checked(),'payment at receipt selected')
                    require(page.locator('input[name*=delivery_zone],select[name*=delivery_zone]').count()==0,'no manual zone selector')
                    capture(page,'candidate-1440-initial',report['metrics'])
                    report['map_geometry']=page.locator('.rollsbar-checkout-map, .rollsbar-checkout-map iframe').evaluate_all("els=>els.map(e=>({tag:e.tagName,rect:e.getBoundingClientRect().toJSON(),display:getComputedStyle(e).display,width:getComputedStyle(e).width,height:getComputedStyle(e).height}))")
                    frame=page.locator('.rollsbar-checkout-map iframe').element_handle().content_frame()
                    report['map_document']=frame.evaluate("({width:innerWidth,height:innerHeight,bodyWidth:document.body.scrollWidth})")
                    print('MAP_GEOMETRY '+json.dumps({'outer':report['map_geometry'],'inner':report['map_document']}))
                    address=page.locator('#billing-address_1')
                    address.fill('Симферополь Гагарина 17')
                    page.locator('.rollsbar-address-suggestions__item').first.wait_for()
                    capture(page,'candidate-1440-suggestions',report['metrics'])
                    report['exact']=choose(page,'Симферополь Гагарина 17',True)
                    page.locator('.rollsbar-checkout-map').scroll_into_view_if_needed()
                    page.wait_for_timeout(2000)
                    capture(page,'candidate-1440-exact',report['metrics'])
                    if '--map-only' in sys.argv:
                        frame=page.locator('.rollsbar-checkout-map iframe').element_handle().content_frame()
                        print('MAP_DETAILS '+json.dumps(frame.evaluate("""()=>({width:innerWidth,height:innerHeight,htmlStyle:document.documentElement.getAttribute('style'),text:document.body.innerText.slice(0,500),els:[...document.querySelectorAll('div')].map(e=>({c:e.className,r:e.getBoundingClientRect().toJSON(),d:getComputedStyle(e).display})).filter(x=>x.r.height>=100&&x.r.width>=80).slice(0,20)})"""),ensure_ascii=False))
                        page.locator('.rollsbar-checkout-map').screenshot(path=str(OUT/'map-detail.png'))
                        return
                    report['low']=choose(page,'Дубки Раздерина 12',False)
                    capture(page,'candidate-1440-low',report['metrics'])
                    # Hold an actual provider resolve response until the customer edits.
                    pending=[]
                    def delayed_resolve(route):
                        pending.append(route)
                    page.route('**/address-resolve',delayed_resolve)
                    address.fill('Симферополь Гагарина 17')
                    with page.expect_request(lambda r:'/address-resolve' in r.url and r.method=='POST'):
                        page.locator('.rollsbar-address-suggestions__item').first.click()
                    # Pump route events until the interception is observed, rather
                    # than assuming a 100ms network/runner scheduling deadline.
                    for attempt in range(100):
                        if pending:break
                        page.wait_for_timeout(100)
                    require(len(pending)==1,'live resolve request intercepted for stale-response regression')
                    address.fill('Адрес изменён во время проверки')
                    route=pending[0]
                    response=route.fetch()
                    require(response.status==200,'delayed live DaData resolve HTTP 200')
                    route.fulfill(response=response)
                    page.wait_for_timeout(300)
                    require(address.input_value()=='Адрес изменён во время проверки' and address.get_attribute('data-rollsbar-address-resolved') is None,'late live resolve cannot restore the old address')
                    require('&pt=' not in page.locator('.rollsbar-checkout-map iframe').get_attribute('src'),'late live resolve cannot restore old customer marker')
                    report['stale_resolve']='PASS: actual live resolve delivered after edit, address and map remained cleared'
                    page.unroute('**/address-resolve',delayed_resolve)
                    # Close current suggestions using the existing Escape behavior.
                    address.press('Escape')
                    report['cta']={}
                    report['layout']={}
                    report['required_controls']={}
                    for width in [1440,1024,701,700,390,320]:
                        page.set_viewport_size({'width':width,'height':1000 if width>700 else 844})
                        page.wait_for_timeout(500)
                        # Native mobile summary may collapse; expand via its own control.
                        title=page.locator('.wc-block-components-checkout-order-summary__title')
                        if title.get_attribute('role')=='button' and title.get_attribute('aria-expanded')=='false': title.click()
                        require(page.locator('.wp-block-woocommerce-checkout-order-summary-block:visible').count()==1,f'{width}: exactly one responsive native summary visible')
                        require(all(e['visible'] for e in snapshot(page) if e['required']),f'{width}: all native required inputs remain visible')
                        required=page.locator('.wc-block-checkout__form input[required], .wc-block-checkout__form select[required]')
                        for control in required.all():
                            control.scroll_into_view_if_needed()
                            control.click(trial=True)
                        report['required_controls'][str(width)]=required.evaluate_all('els=>els.map(e=>({id:e.id,willValidate:e.willValidate,valueMissing:e.validity.valueMissing}))')
                        require(all(e['willValidate'] for e in report['required_controls'][str(width)]),f'{width}: native required validation active and controls pointer-reachable')
                        report['layout'][str(width)]=page.locator('.wc-block-components-sidebar-layout').evaluate('(e)=>getComputedStyle(e).gridTemplateColumns')
                        require(len(report['layout'][str(width)].split())==(2 if width>700 else 1),f'{width}: intended desktop/mobile breakpoint')
                        capture(page,f'candidate-{width}-checkout',report['metrics'])
                        report['candidate_geometry'][str(width)]=geometry(page)
                        cta=page.locator('.wc-block-components-checkout-place-order-button')
                        cta.scroll_into_view_if_needed()
                        cta.click(trial=True)
                        info=cta.evaluate("""e=>{const r=e.getBoundingClientRect();const x=r.x+r.width/2,y=r.y+r.height/2;
                          return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,unobscured:e.contains(document.elementFromPoint(x,y))};}""")
                        require(info['left']>=0 and info['right']<=width and info['top']>=0 and info['bottom']<=page.viewport_size['height'] and info['unobscured'],f'{width}: native CTA reachable, unclipped, unobscured')
                        report['cta'][str(width)]=info
                        report['cta'][str(width)]['document_top']=cta.evaluate('e=>e.getBoundingClientRect().top+scrollY')
                        page.screenshot(path=str(OUT/f'candidate-{width}-cta.png'))
                        if width in (700,390,320):
                            address.fill('Симферополь Гагарина 17')
                            page.locator('.rollsbar-address-suggestions__item').first.wait_for()
                            capture(page,f'candidate-{width}-suggestions',report['metrics'])
                            report[f'exact_{width}']=choose(page,'Симферополь Гагарина 17',True)
                            capture(page,f'candidate-{width}-exact',report['metrics'])
                    require(not report['page_errors'],'no uncaught application JS errors')
                    require(not report['order_submission_requests'],'zero checkout submission requests')
            finally:
                browser.close()
        report['cleanup']='PASS: accepted finally helper verified fresh GET items_count=0/items=[]'
        report['result']='PASS'
    except Exception as e:
        report['result']='FAIL';report['error']=str(e)
        raise
    finally:
        (OUT/('map-only-evidence.json' if '--map-only' in sys.argv else 'evidence.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()

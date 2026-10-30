"""Owner remarks: pizza choices, shared navigation and delivery map; no orders."""
import os,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'wordpress/deploy'),str(ROOT/'qa/checkout')]
from gate_b_browser import BASE,require,add_first_simple_product
from delivery_test_context import delivery_page,settle_native
from playwright.sync_api import sync_playwright
out=ROOT/'qa/visual-results/client-ux';out.mkdir(parents=True,exist_ok=True)
report={'status':'RUNNING','release_sha':os.environ['ROLLSBAR_DEPLOY_SHA'],'checks':[],'submitted_orders':0}
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch()
  for width in [1440,701,700,390,320]:
   with delivery_page(b,viewport={'width':width,'height':900},locale='ru-RU') as p:
    errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    p.goto(BASE+'/',wait_until='domcontentloaded')
    data=json.loads(p.locator('#rollsbarProductDetailsData').text_content())
    promo=p.locator('.rollsbar-utility--promo');require('Хит-меню' in promo.inner_text() and promo.get_attribute('href')=='#hits','truthful hit-menu card')
    pizzas=[(key,v) for key,v in data.items() if v.get('pizza')]
    require(len(pizzas)==12,'all 12 pizza identities retained')
    modal=p.locator('#rollsbarProductDetails')
    for key,v in pizzas:
     p.locator('.rollsbar-catalog-section:not(#hits) [data-rollsbar-source-id="'+key+'"] [data-rollsbar-detail-open]').first.click()
     modal.locator('.rollsbar-product-details__add').click()
     choices=modal.locator('.rollsbar-size-choices');require(choices.is_visible(),'visible size choices')
     require(choices.locator('input').count()==len(v['selection']['variations']),'exact native variants')
     require(modal.locator('select[data-variation]').count()==0,'pizza has no dropdown')
     for variation in v['selection']['variations']:
      if not variation['available']:continue
      label=choices.locator('label').filter(has=p.locator('input[value="'+str(variation['id'])+'"]'))
      label.click();selected=json.loads(modal.get_attribute('data-selection'))
      require(selected['variation_id']==variation['id'],'exact selected native variation ID')
      require(variation['price_label'] in modal.locator('.rollsbar-product-options__add').inner_text(),'actual selected price visible')
      require(label.bounding_box()['height']>=44,'size hit target')
     if key==pizzas[0][0]:
      radios=choices.locator('input');radios.first.focus();p.keyboard.press('ArrowRight')
      require(radios.nth(1).is_checked(),'native keyboard arrow selection')
      p.screenshot(path=str(out/f'pizza-{width}.png'))
     p.keyboard.press('Escape');require(not modal.is_visible(),'size modal closes')
    mapframe=p.locator('.rollsbar-delivery-map');p.locator('#delivery').evaluate("e=>e.scrollIntoView({block:'start'})")
    frame=mapframe.element_handle().content_frame();frame.wait_for_function('window.rollsbarMapReady===true')
    tiers=frame.locator('.legend').inner_text()
    for tier in [1200,1500,2000,2500,3000,3500,4000]:require(str(tier) in tiers,'all existing tiers visible')
    require('/assets/delivery-map.html' in mapframe.get_attribute('src'),'same checkout map artifact')
    require(p.locator('iframe[src*="yandex"]').count()==0,'legacy Yandex frame removed')
    require(frame.locator('a[href*="openstreetmap.org/copyright"]').is_visible(),'OSM attribution')
    p.screenshot(path=str(out/f'delivery-{width}.png'))
    p.evaluate('window.scrollTo(0,0)');add_first_simple_product(p);settle_native(p)
    p.goto(BASE+'/rekvizity-prodavca/',wait_until='domcontentloaded')
    toggle=p.locator('[data-rollsbar-menu-open]');toggle.click()
    menu=p.locator('#rollsbarSiteMenu');require(menu.get_attribute('aria-hidden')=='false','internal page menu opens')
    require(p.locator('main').evaluate('e=>e.inert'),'background inert')
    for suffix in ['/#rolls','/#delivery','/#contacts','/otzyvy/','/rabota-v-rolls-bar/','/pravovaya-informaciya/']:
     require(menu.locator('a[href="'+BASE+suffix+'"]').count()==1,'internal link targets correct origin/section')
    p.screenshot(path=str(out/f'menu-{width}.png'))
    p.keyboard.press('Escape');require(menu.get_attribute('aria-hidden')=='true','Escape closes');require(toggle.evaluate('e=>e===document.activeElement'),'focus restored')
    toggle.click();menu.locator('.rollsbar-site-menu__backdrop').click(position={'x':5,'y':200});require(menu.get_attribute('aria-hidden')=='true','backdrop closes')
    toggle.click();menu.locator('.rollsbar-site-menu__close').click();require(menu.get_attribute('aria-hidden')=='true','cross closes')
    if width<=700:
     require(not p.locator('.rollsbar-header .rollsbar-cart-link').is_visible(),'mobile top duplicate removed')
     require(p.locator('[data-rollsbar-mobile-cart]').is_visible(),'bottom cart preserved')
     require(toggle.bounding_box()['width']>=44,'internal menu touch target')
    require(p.evaluate('document.documentElement.scrollWidth<=innerWidth'),'internal page overflow')
    p.goto(BASE+'/checkout/',wait_until='domcontentloaded');p.locator('.rollsbar-checkout-shopping').wait_for();settle_native(p)
    link=p.locator('.rollsbar-checkout-shopping');require(link.is_visible(),'visible return to purchases')
    link.click();p.wait_for_url(BASE+'/');require(p.locator('.rollsbar-product-card').count()==126,'return keeps storefront')
    require(not errors,'no browser errors: '+str(errors))
    report['checks'].append({'width':width,'pizza_identities':len(pizzas),'status':'PASS','map':'same checkout asset','navigation':'PASS','return':'PASS'})
  b.close()
 report['status']='PASS'
finally:(out/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

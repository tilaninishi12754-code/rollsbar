"""Read-only review-map browser gates; no storefront or order requests."""
import json,os,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'wordpress/docs/delivery-draft-2026-10-29'
shots=ROOT/'qa/artifacts/delivery-draft-2026-10-29';shots.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width in [1440,701,700,390,320]:
  context=browser.new_context(viewport={'width':width,'height':940},device_scale_factor=1,accept_downloads=True)
  page=context.new_page();errors=[];external=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  def route(req):
   if not req.request.url.startswith('http://127.0.0.1:8768/'):
    external.append(req.request.url);req.abort()
   else:req.continue_()
  page.route('**/*',route)
  page.goto('http://127.0.0.1:8768/wordpress/docs/delivery-draft-2026-10-29/index.html')
  page.wait_for_function('window.REVIEW && document.querySelectorAll(".row").length===92')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'overflow at {width}'
  assert page.locator('.tier').count()==7
  assert page.evaluate('REVIEW.data.rows.length')==92
  assert page.evaluate('REVIEW.data.status')=='DRAFT_FOR_REVIEW_NOT_LIVE'
  page.screenshot(path=str(shots/f'map-{width}.png'),full_page=False)
  page.locator('#search').fill('Мазанка');assert page.locator('.row').count()==2
  assert all('4000' in s for s in page.locator('.row').all_text_contents())
  page.locator('.row').first.click();assert page.locator('.leaflet-popup').is_visible()
  page.locator('#search').fill('Луговое');page.locator('.row').click()
  assert page.evaluate('REVIEW.map.getCenter().lng')<34.3,'distant Lugovoe namesake selected'
  page.locator('#search').fill('Кирпичное');page.locator('.row').first.click()
  assert page.evaluate('REVIEW.map.getCenter().lng')<34.3,'distant Kirpichnoe namesake selected'
  page.locator('#search').fill('ДКП');assert page.locator('.row').count()==2
  page.locator('.row').filter(has_text='B21').click();assert page.locator('#questions').get_attribute('open') is not None
  page.locator('#q-territories').fill('Проверка: уточнить границу');page.reload()
  page.locator('#questions').evaluate('(e)=>e.open=true')
  assert page.locator('#q-territories').input_value()=='Проверка: уточнить границу'
  with page.expect_download() as info:page.locator('#export').click()
  download=info.value;target=shots/f'answers-test-{width}.json';download.save_as(target)
  answers=json.loads(target.read_text(encoding='utf8'));assert len(answers['questions'])==8
  assert answers['questions'][0]['status']=='answered_needs_review'
  assert answers['questions'][1]['status']=='pending'
  page.locator('#questions').evaluate('(e)=>e.open=false')
  page.locator('#showProposal').uncheck();assert page.evaluate('REVIEW.groups.proposal.every(([f,l])=>!REVIEW.map.hasLayer(l))')
  page.locator('#showProposal').check();page.locator('.tier').first.click()
  assert page.locator('.tier').first.get_attribute('aria-pressed')=='false'
  page.locator('.tier').first.click();page.locator('#showUncertain').check()
  page.locator('#all').click();page.locator('#city').click()
  page.screenshot(path=str(shots/f'review-{width}.png'),full_page=False)
  assert not errors,errors
  assert not external,external
  results.append({'width':width,'result':'PASS','rows':92,'tiers':7,'js_errors':errors,'external_requests':external,'gates':['overflow','source search','namesake location','missing location','layer toggles','review persistence','download pending status','offline vector map']})
  context.close()
 # A forwarded standalone file must work without the local HTTP server as well.
 context=browser.new_context(viewport={'width':1440,'height':940})
 page=context.new_page();page.goto((OUT/'index.html').as_uri())
 page.wait_for_function('window.REVIEW && document.querySelectorAll(".row").length===92')
 assert page.locator('#q-territories').input_value()==''
 page.locator('#all').click();page.wait_for_timeout(350)
 page.screenshot(path=str(shots/'all-localities-file.png'))
 assert page.locator('.place-label').count()>10
 context.close();browser.close()
(OUT/'browser-verification.json').write_text(json.dumps({'result':'PASS','tests':results,'screenshots':'qa/artifacts/delivery-draft-2026-10-29','order_requests':0,'staging_mutation':False},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(results,ensure_ascii=False,indent=2))

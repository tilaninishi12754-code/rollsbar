#!/usr/bin/env python3
"""Media-only real Chromium acceptance against staging. No cart/checkout writes."""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'qa/visual-results/client-media'
BASE = 'https://staging.rollsbar.ru'


def require(condition, reason):
    if not condition:
        raise AssertionError(reason)


def main():
    proof = json.loads((OUT / 'staging.json').read_text(encoding='utf-8'))
    expected = {p['source_id']: p for p in proof['products']}
    require(len(expected) == 45, 'Expected 45 resolved product identities')
    report = {'status': 'RUNNING', 'release_sha': proof['release_sha'], 'http_assets': [], 'viewports': []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for label, viewport in [('desktop', {'width':1440,'height':1000}), ('mobile', {'width':390,'height':900})]:
                context = browser.new_context(viewport=viewport, device_scale_factor=1,
                                              is_mobile=label=='mobile', has_touch=label=='mobile')
                page = context.new_page()
                response = page.goto(BASE + '/?client-media=' + proof['release_sha'], wait_until='domcontentloaded', timeout=60000)
                require(response and response.status == 200, 'Homepage HTTP 200')
                page.locator('.rollsbar-product-card').first.wait_for()
                observed = []
                if label == 'desktop':
                    for asset in proof['assets']:
                        require(urlsplit(asset['url']).hostname == 'staging.rollsbar.ru', 'Canonical media must be local staging uploads')
                        r = context.request.get(asset['url'], timeout=30000)
                        require(r.status == 200, 'Canonical asset HTTP: ' + asset['key'])
                        require(hashlib.sha256(r.body()).hexdigest() == asset['sha256'], 'HTTP canonical bytes: ' + asset['key'])
                        require(r.headers.get('content-type','').split(';')[0] == asset['mime'], 'HTTP MIME: ' + asset['key'])
                        report['http_assets'].append({'key':asset['key'],'status':r.status,'sha256':asset['sha256'],'mime':asset['mime']})
                for source, product in expected.items():
                    card = page.locator(f'.rollsbar-catalog-section:not(#hits) [data-rollsbar-source-id="{source}"]')
                    require(card.count() == 1, 'Exactly one main card: ' + source)
                    image = card.locator('.rollsbar-product-card__media img')
                    require(image.count() == 1 and card.locator('.rollsbar-product-fallback').count() == 0, 'No mapped placeholder: ' + source)
                    image.scroll_into_view_if_needed()
                    image.evaluate('(img) => img.decode()')
                    actual = image.evaluate('(img)=>({src:img.currentSrc||img.src,width:img.naturalWidth,height:img.naturalHeight,complete:img.complete,visible:!!(img.offsetWidth&&img.offsetHeight)})')
                    require(actual['complete'] and actual['visible'] and actual['width'] > 0 and actual['height'] > 0, 'Visible decoded food image: ' + source)
                    require(actual['src'] == product['display_url'], 'DOM displays canonical attachment: ' + source)
                    r = context.request.get(actual['src'], timeout=30000)
                    require(r.status == 200, 'Displayed image HTTP 200: ' + source)
                    observed.append({'source_id':source,'attachment_id':product['attachment_id'],'media_key':product['media_key'],**actual,'http_status':r.status})
                details = json.loads(page.locator('#rollsbarProductDetailsData').text_content())
                for source, product in expected.items():
                    require(product['display_url'] in details[source]['media'], 'Detail media uses canon: ' + source)
                require(page.locator('.rollsbar-product-card').count() == 126, 'Catalog representation invariant 118 + 8 Hits')
                require(page.evaluate('document.documentElement.scrollWidth-innerWidth') <= 1, 'No horizontal overflow')
                targets = [('homepage', None), ('italyanskiy', 'rolls-italyanskiy'), ('ogonek', 'pizza-ogonek'),
                           ('baked-mamenori', 'baked-zapechennye-mamenori-s-lososem'), ('rice', 'baked-rice-shrimp')]
                shots = []
                for name, source in targets:
                    if source:
                        card = page.locator(f'.rollsbar-catalog-section:not(#hits) [data-rollsbar-source-id="{source}"]')
                        card.scroll_into_view_if_needed()
                        card.evaluate('(el)=>window.scrollTo(0,el.getBoundingClientRect().top+scrollY-170)')
                    else:
                        page.evaluate('scrollTo(0,0)')
                    page.evaluate('document.fonts.ready')
                    path = OUT / f'{label}-{name}.png'
                    page.screenshot(path=str(path), animations='disabled')
                    shots.append(path.name)
                new_keys={'zapechennyy-ris','zapechennye-mamenori','ogonek','italyanskiy'}
                require(new_keys <= {r['media_key'] for r in observed}, 'All four new 21.10 images visibly verified')
                report['viewports'].append({'name':label,'viewport':viewport,'mapped_products':observed,'new_21_10_assets':sorted(new_keys),'broken_mapped_images':0,'screenshots':shots})
                context.close()
            report['status']='PASS'
            report['browser_version']=browser.version
        finally:
            browser.close()
            (OUT/'browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'canonical_http_assets':len(report['http_assets']),
                      'desktop_mapped':45,'mobile_mapped':45,'new_21_10_assets':4,'broken_mapped_images':0}))


if __name__ == '__main__': main()

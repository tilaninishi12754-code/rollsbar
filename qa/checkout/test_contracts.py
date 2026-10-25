"""Offline candidate UX regressions. Fixtures are not runtime address evidence."""
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
from playwright.sync_api import sync_playwright

HTML='''<html><body class="woocommerce-checkout"><div class="wp-block-woocommerce-checkout">
<div class="wc-block-components-checkout-step__content"><input id="billing-address_1" autocomplete="address-line1"></div>
<input id="billing-phone" type="tel"><input id="consent" type="checkbox" required>
</div></body></html>'''
JS=(ROOT/'wordpress/wp-content/plugins/rollsbar-core/assets/js/checkout.js').read_text(encoding='utf-8')
CSS=(ROOT/'wordpress/wp-content/plugins/rollsbar-core/assets/css/checkout.css').read_text(encoding='utf-8')


class CheckoutContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        cls.browser=cls.pw.chromium.launch(channel='chrome',headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop()

    def setUp(self):
        self.ctx=self.browser.new_context(viewport={'width':320,'height':844})
        self.page=self.ctx.new_page()
        self.result={'display':'Fixture house','qc_geo':0,'lat':44.9,'lon':34.1,'precision':{'allow_auto_zone':True}}
        self.ctx.route('**/*',self.route)
        self.page.goto('https://fixture.test/')
        self.page.evaluate("window.rollsBarCheckoutConfig={addressSuggestions:{enabled:true,suggestUrl:'/suggest',resolveUrl:'/resolve',debounceMs:10}}")
        self.page.add_script_tag(content=JS)
        self.page.add_style_tag(content=CSS)

    def tearDown(self):self.ctx.close()

    def route(self,route):
        url=route.request.url
        if '/suggest' in url:
            route.fulfill(json={'suggestions':[{'display':'Fixture house','token':'offline-only'}]})
        elif '/resolve' in url:route.fulfill(json=self.result)
        elif url=='https://fixture.test/':route.fulfill(content_type='text/html',body=HTML)
        else:route.abort()

    def select(self):
        self.page.locator('#billing-address_1').fill('Fixture')
        self.page.locator('.rollsbar-address-suggestions__item').click()
        self.page.wait_for_function("document.querySelector('#billing-address_1').dataset.rollsbarAddressResolved==='1'")

    def test_phone_and_no_duplicate_controls(self):
        phone=self.page.locator('#billing-phone')
        self.assertEqual(phone.input_value(),'+7 ')
        phone.fill('89781234567');phone.blur()
        self.assertEqual(phone.input_value(),'+7 9781234567')
        self.page.evaluate("document.body.appendChild(document.createElement('p'))")
        self.assertEqual(self.page.locator('input').count(),3)
        self.assertEqual(self.page.locator('.rollsbar-checkout-map').count(),1)
        self.assertEqual(self.page.locator('.rollsbar-checkout-title').count(),1)
        self.assertIsNotNone(self.page.locator('#consent').get_attribute('required'))

    def test_exact_and_edit_invalidates_point(self):
        self.select()
        self.assertEqual(self.page.locator('.rollsbar-checkout-map').get_attribute('data-exact'),'1')
        self.assertIn('&pt=',self.page.locator('iframe').get_attribute('src'))
        self.page.locator('#billing-address_1').fill('Changed')
        self.assertEqual(self.page.locator('.rollsbar-checkout-map').get_attribute('data-exact'),'0')
        self.assertNotIn('&pt=',self.page.locator('iframe').get_attribute('src'))

    def test_low_precision_never_adds_point(self):
        for qc in [1,2,3,4,5,None]:
            with self.subTest(qc_geo=qc):
                self.result.update(qc_geo=qc,precision={'allow_auto_zone':False})
                self.select()
                self.assertEqual(self.page.locator('.rollsbar-checkout-map').get_attribute('data-exact'),'0')
                self.assertNotIn('&pt=',self.page.locator('iframe').get_attribute('src'))
                self.assertTrue(self.page.locator('.rollsbar-address-status.is-warning').is_visible())

    def test_malformed_exact_coordinates_never_add_point(self):
        for lat,lon,qc in [(None,34.1,0),('',34.1,0),('nan',34.1,0),(91,34.1,0),(44.9,181,0),(44.9,34.1,None),(False,34.1,0)]:
            with self.subTest(lat=lat,lon=lon,qc=qc):
                self.result.update(lat=lat,lon=lon,qc_geo=qc)
                self.select()
                self.assertNotIn('&pt=',self.page.locator('iframe').get_attribute('src'))

    def test_late_resolve_cannot_restore_edited_address_or_point(self):
        pending=[]
        self.page.route('**/resolve',lambda route:pending.append(route))
        self.page.locator('#billing-address_1').fill('Fixture')
        self.page.locator('.rollsbar-address-suggestions__item').click()
        self.page.wait_for_timeout(50)
        self.assertEqual(len(pending),1)
        self.page.locator('#billing-address_1').fill('Edited while resolving')
        pending[0].fulfill(json=self.result)
        self.page.wait_for_timeout(50)
        self.assertEqual(self.page.locator('#billing-address_1').input_value(),'Edited while resolving')
        self.assertNotIn('&pt=',self.page.locator('iframe').get_attribute('src'))

    def test_late_suggestions_cannot_replace_current_query(self):
        # Simulate a provider transport that ignores AbortSignal; the query guard
        # must independently discard its stale success response.
        self.page.evaluate("""() => {
          const realFetch=window.fetch;
          window.fetch=(url,options)=>String(url).includes('/suggest')
            ?new Promise(resolve=>{window.releaseOldSuggestions=()=>resolve({ok:true,json:()=>Promise.resolve({suggestions:[{display:'Stale fixture',token:'old'}]})});})
            :realFetch(url,options);
        }""")
        address=self.page.locator('#billing-address_1')
        address.fill('Old query')
        self.page.wait_for_function('!!window.releaseOldSuggestions')
        address.fill('New query')
        self.page.evaluate('window.releaseOldSuggestions()')
        self.page.wait_for_timeout(50)
        self.assertFalse(self.page.locator('.rollsbar-address-suggestions').is_visible())

    def test_suggestion_reflows_at_320(self):
        self.page.locator('#billing-address_1').fill('Fixture')
        panel=self.page.locator('.rollsbar-address-suggestions')
        panel.wait_for(state='visible')
        box=panel.bounding_box()
        self.assertGreaterEqual(box['x'],0)
        self.assertLessEqual(box['x']+box['width'],320)

    def test_css_scope_and_parse(self):
        self.assertEqual(CSS.count('{'),CSS.count('}'))
        selectors=self.page.evaluate("""() => {
          const out=[];const walk=rules=>{for(const r of rules){if(r.selectorText)out.push(r.selectorText);else if(r.cssRules)walk(r.cssRules);}};
          for(const s of document.styleSheets)walk(s.cssRules);return out;
        }""")
        self.assertGreater(len(selectors),50)
        for selector in selectors:
            self.assertTrue(selector.startswith('body.woocommerce-checkout') or selector.startswith('.rollsbar-address-'),selector)
        self.assertNotIn('delivery-zone-overlay',JS)
        self.assertNotIn('polygon',CSS)


if __name__=='__main__':unittest.main()

"""QA-only deterministic regressions; all browser requests fulfilled offline."""
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'wordpress/deploy'))
import gate_b_browser as gate
from catalog_browser_contract import verify_catalog
from playwright.sync_api import sync_playwright


class ObservationTests(unittest.TestCase):
    def run_case(self, states):
        elapsed = [0.0]
        class Page:
            def wait_for_timeout(self, ms):
                elapsed[0] += ms / 1000
        calls = []
        def read(page, **kwargs):
            calls.append(1)
            return states[min(len(calls) - 1, len(states) - 1)]
        with patch.object(gate, 'store_cart_state', read):
            result = gate.wait_for_store_item(Page(), 47, 'exact-key', timeout=1, interval=.25, clock=lambda: elapsed[0])
        return result, len(calls)

    good = {'status': 200, 'items': [{'id': 47, 'key': 'exact-key', 'name': 'Тест'}]}
    empty = {'status': 200, 'items': []}

    def test_immediate(self):
        self.assertEqual(self.run_case([self.good])[1], 1)

    def test_delayed(self):
        self.assertEqual(self.run_case([self.empty, self.empty, self.good])[1], 3)

    def test_permanent_absence(self):
        with self.assertRaisesRegex(AssertionError, 'after 5 attempts'):
            self.run_case([self.empty])

    def test_wrong_product_same_name_and_key(self):
        with self.assertRaisesRegex(AssertionError, 'Exact Store API item absent'):
            self.run_case([{'status': 200, 'items': [{'id': 48, 'key': 'exact-key', 'name': 'Тест'}]}])

    def test_wrong_line_same_product(self):
        with self.assertRaises(AssertionError):
            self.run_case([{'status': 200, 'items': [{'id': 47, 'key': 'wrong-key'}]}])

    def test_http_error_even_with_right_item(self):
        with self.assertRaisesRegex(AssertionError, 'HTTP 200'):
            self.run_case([{**self.good, 'status': 503}])

    def test_catalog_regression(self):
        ids = [f'p{i}' for i in range(118)]
        verify_catalog(ids, ids[:8], ids + ids[:8], ids)
        with self.assertRaises(AssertionError):
            verify_catalog(ids, ids[:8], ids + ids[1:9], ids)

    def test_old_response_predicate_accepts_startup_read_new_rejects(self):
        def response(payload):
            return SimpleNamespace(url=gate.BASE + '/?wc-ajax=rollsbar_cart',
                                   request=SimpleNamespace(method='POST', post_data=urlencode({'request': __import__('json').dumps(payload)})))
        startup = response({'operation': 'read'})
        self.assertTrue('wc-ajax=rollsbar_cart' in startup.url and startup.request.method == 'POST')
        self.assertFalse(gate.is_cart_add_response(startup, 'source', 47))
        self.assertTrue(gate.is_cart_add_response(response({'operation': 'add', 'source_id': 'source', 'product_id': 47}), 'source', 47))
        self.assertFalse(gate.is_cart_add_response(response({'operation': 'add', 'source_id': 'other', 'product_id': 47}), 'source', 47))


class CleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        channel = os.environ.get('PLAYWRIGHT_CHANNEL')
        cls.browser = cls.pw.chromium.launch(**({'channel': channel} if channel else {}))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def fixture(self, page, *, sticky=False, fail_remove=False):
        items = [{'key': 'a', 'id': 47}, {'key': 'b', 'id': 48}]
        calls = []
        def route(r):
            req = r.request
            path = req.url.split(gate.BASE)[-1]
            calls.append((req.method, path))
            if path == '/':
                return r.fulfill(status=200, content_type='text/html', body='<html></html>')
            if req.method == 'DELETE':
                return r.fulfill(json=[])
            if path.endswith('/remove-item'):
                self.assertEqual(req.headers.get('nonce'), 'fixture-nonce')
                self.assertEqual(req.method, 'POST')
                key = req.post_data_json['key']
                self.assertIn(key, [i['key'] for i in items])
                if not sticky:
                    items[:] = [i for i in items if i['key'] != key]
                return r.fulfill(status=500 if fail_remove else 200, json={'items': items})
            self.assertEqual(path, '/wp-json/wc/store/v1/cart')
            return r.fulfill(headers={'Nonce': 'fixture-nonce'}, json={'items': items, 'items_count': len(items)})
        page.route('**/*', route)
        page.goto(gate.BASE + '/')
        return items, calls

    def test_old_list_contract_fails(self):
        with self.browser.new_context() as ctx:
            page = ctx.new_page()
            self.fixture(page)
            result = page.evaluate("""async () => {
              const r = await fetch('/wp-json/wc/store/v1/cart/items', {method:'DELETE'});
              return {status:r.status, cart:await r.json()};
            }""")
            with self.assertRaises(TypeError):
                _ = result['cart']['items_count']

    def test_supported_removal_and_fresh_final_get(self):
        with self.browser.new_context() as ctx:
            page = ctx.new_page()
            items, calls = self.fixture(page)
            gate.clean_test_cart(page)
            self.assertEqual(items, [])
            self.assertEqual([m for m, _ in calls].count('POST'), 2)
            self.assertEqual(calls[-1], ('GET', '/wp-json/wc/store/v1/cart'))
            self.assertNotIn('DELETE', [m for m, _ in calls])

    def test_final_nonempty_fails(self):
        with self.browser.new_context() as ctx:
            page = ctx.new_page()
            self.fixture(page, sticky=True)
            with self.assertRaises(AssertionError):
                gate.clean_test_cart(page)

    def test_cleanup_on_primary_failure_and_context_isolation(self):
        with self.browser.new_context() as other:
            other_page = other.new_page()
            other_items, _ = self.fixture(other_page)
            with self.assertRaisesRegex(AssertionError, 'primary failure'):
                with gate.isolated_browser_page(self.browser) as page:
                    items, _ = self.fixture(page)
                    raise AssertionError('primary failure')
            self.assertEqual(items, [])
            self.assertEqual(len(other_items), 2)

    def test_both_failures_reported_primary_preserved(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            with self.assertRaisesRegex(AssertionError, 'primary failure') as caught:
                with gate.isolated_browser_page(self.browser) as page:
                    self.fixture(page, fail_remove=True)
                    raise AssertionError('primary failure')
        self.assertIn('cleanup', output.getvalue())
        self.assertIn('Cleanup also failed', caught.exception.__notes__[0])

    def test_cleanup_failure_alone_fails(self):
        with self.assertRaisesRegex(Exception, 'Cleanup remove-item HTTP 500'):
            with gate.isolated_browser_page(self.browser) as page:
                self.fixture(page, fail_remove=True)


if __name__ == '__main__':
    unittest.main()

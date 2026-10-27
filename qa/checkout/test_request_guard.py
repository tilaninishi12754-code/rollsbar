"""Protect real order submission while allowing WordPress native REST updates."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from request_guard import is_order_submission

class NativeRequestGuard(unittest.TestCase):
 def test_effective_rest_methods_and_legacy_guard(self):
  native='https://staging.rollsbar.ru/wp-json/wc/store/v1/checkout?__experimental_calc_totals=true'
  legacy='https://staging.rollsbar.ru/?wc-ajax=checkout'
  for url,method,override,blocked in [
   (native,'POST',None,True),(native,'POST','PUT',False),
   (native,'POST','PATCH',False),(native,'PUT','POST',True),
   (native,'GET',None,False),(legacy,'POST','PUT',True),
   ('https://staging.rollsbar.ru/?wc-ajax=rollsbar_cart','POST',None,False),
  ]:
   with self.subTest(url=url,method=method,override=override):
    request=SimpleNamespace(url=url,method=method,headers={} if override is None else {'x-http-method-override':override})
    self.assertEqual(is_order_submission(request),blocked)

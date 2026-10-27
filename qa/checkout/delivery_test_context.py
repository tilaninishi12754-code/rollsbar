"""Wait for native Woo's queue before the unchanged strict isolated cart cleanup."""
import sys,time
from contextlib import contextmanager
from gate_b_browser import isolated_browser_page,require

@contextmanager
def delivery_page(browser,**options):
 with isolated_browser_page(browser,**options) as page:
  pending=set();last=[time.monotonic()]
  def start(request):
   if '/wc/store/' in request.url:pending.add(request);last[0]=time.monotonic()
  def finish(request):
   if request in pending:pending.discard(request);last[0]=time.monotonic()
  page.on('request',start);page.on('requestfinished',finish);page.on('requestfailed',finish)
  try:yield page
  finally:
   primary=sys.exc_info()[1]
   try:
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
     idle=page.evaluate('''()=>{
      const cart=window.wp?.data?.select('wc/store/cart'),checkout=window.wp?.data?.select('wc/store/checkout');
      return !cart?.isCustomerDataUpdating?.()&&!checkout?.isCalculating?.();
     }''')
     if not pending and idle and time.monotonic()-last[0]>=.5:break
     page.wait_for_timeout(100)
    require(not pending and idle and time.monotonic()-last[0]>=.5,'native Woo request/calculation queue settled before strict cleanup')
   except Exception as error:
    if primary is None:raise
    primary.add_note('Native queue cleanup readiness failed: '+repr(error))

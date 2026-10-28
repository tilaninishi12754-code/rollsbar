"""Wait for the current document's Woo queue before unchanged strict cart cleanup."""
import sys,time
from contextlib import contextmanager
from weakref import WeakKeyDictionary
from urllib.parse import urlsplit
from gate_b_browser import isolated_browser_page,require
from request_guard import is_order_submission,effective_rest_method
_queues=WeakKeyDictionary()

def settle_native(page):
 pending,last=_queues[page]
 deadline=time.monotonic()+10;quiet_since=time.monotonic();idle=False
 while time.monotonic()<deadline:
  idle=page.evaluate('''()=>{
   const cart=window.wp?.data?.select('wc/store/cart'),checkout=window.wp?.data?.select('wc/store/checkout');
   return !cart?.isCustomerDataUpdating?.()&&!checkout?.isCalculating?.();
  }''')
  quiet_since=max(quiet_since,last[0])
  if not pending and idle and time.monotonic()-quiet_since>=.5:break
  page.wait_for_timeout(100)
 if pending or not idle:print('NATIVE_QUEUE_PENDING',[(r.method,r.url) for r in pending],{'idle':idle},flush=True)
 require(not pending and idle and time.monotonic()-quiet_since>=.5,'native Woo request/calculation queue settled before navigation or strict cleanup')

@contextmanager
def delivery_page(browser,**options):
 with isolated_browser_page(browser,**options) as page:
  # WP apiFetch may transport PUT as POST + X-HTTP-Method-Override. Preserve
  # those native session updates while still blocking every effective order POST.
  page.context.route('**/*',lambda route:route.abort() if is_order_submission(route.request) else route.continue_())
  pending=set();last=[time.monotonic()]
  _queues[page]=(pending,last)
  def start(request):
   if '/wc/store/' in request.url:
    # Chromium can deliver an old document's autosave request after navigation,
    # without a terminal page event. This is not the current document's queue.
    if autosave(request) and not urlsplit(page.url).path.startswith('/checkout') and urlsplit(request.headers.get('referer','')).path.startswith('/checkout'):
     print('NATIVE_NAVIGATION_INTERRUPTED_AUTOSAVE',request.url,flush=True);return
    pending.add(request);last[0]=time.monotonic()
  def finish(request):
   if request in pending:pending.discard(request);last[0]=time.monotonic()
  page.on('request',start);page.on('requestfinished',finish);page.on('requestfailed',finish)
  def autosave(request):
   return effective_rest_method(request)=='PUT' and '/wc/store/v1/checkout' in request.url
  def navigated(frame):
   if frame!=page.main_frame:return
   for request in list(pending):
    if autosave(request):
     pending.discard(request);print('NATIVE_NAVIGATION_INTERRUPTED_AUTOSAVE',request.url,flush=True)
   last[0]=time.monotonic()
  page.on('framenavigated',navigated)
  try:yield page
  finally:
   primary=sys.exc_info()[1]
   try:
    settle_native(page)
   except Exception as error:
    if primary is None:raise
    primary.add_note('Native queue cleanup readiness failed: '+repr(error))

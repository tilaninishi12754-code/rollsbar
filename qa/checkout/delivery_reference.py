"""Immutable modal chrome comparison; retain unmasked full-frame pixel diffs.

The owner changed field composition and restored an advisory map, so full-content pixel
equality is not an acceptance claim. Existing frozen baselines stay untouched.
"""
import sys,os,json,subprocess,hashlib,mimetypes
from urllib.parse import urlsplit,unquote
from functools import lru_cache
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from PIL import Image,ImageChops,ImageStat
sys.stdout.reconfigure(encoding='utf8',line_buffering=True)
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'wordpress/deploy'))
from gate_b_browser import BASE,isolated_browser_page,add_first_simple_product,require
from playwright.sync_api import sync_playwright
from request_guard import is_order_submission
from release_gate import AssetIdentity,release_assets
from delivery_test_context import delivery_page,settle_native
SOURCE_REF='5e7836e22110ec076603bb1fa2b12f8bb90ee756:index.html'
SOURCE=subprocess.check_output(['git','show',SOURCE_REF],cwd=ROOT)
source_assets={}
@lru_cache(maxsize=256)
def source_asset(path):
 try:return subprocess.check_output(['git','show',SOURCE_REF.split(':')[0]+':'+path],cwd=ROOT,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError:return None
OUT=ROOT/'qa/visual-results/delivery-reference';OUT.mkdir(parents=True,exist_ok=True)
class Reference(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  path=unquote(urlsplit(self.path).path).lstrip('/')
  if '..' in Path(path).parts or '\\' in path:self.send_error(400);return
  body=SOURCE if path=='reference.html' else source_asset(path)
  if body is None:self.send_error(404);return
  if path!='reference.html':source_assets[path]=hashlib.sha256(body).hexdigest()
  self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8' if path=='reference.html' else mimetypes.guess_type(path)[0] or 'application/octet-stream');self.end_headers();self.wfile.write(body)
server=ThreadingHTTPServer(('127.0.0.1',0),Reference);Thread(target=server.serve_forever,daemon=True).start()
report={'status':'RUNNING','release_sha':os.environ['ROLLSBAR_DEPLOY_SHA'],'reference':SOURCE_REF,'source_sha256':hashlib.sha256(SOURCE).hexdigest(),'checks':[],'pixel_equality_claimed':False,'masks':[]}
def geometry(p,selector):
 return p.locator(selector).evaluate('e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {x:r.x,y:r.y,width:r.width,height:r.height,padding:s.padding,radius:s.borderRadius,shadow:s.boxShadow}}')
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  ref=browser.new_page(viewport={'width':1440,'height':900})
  # The source bytes above are served verbatim. No CSS/content substitutions.
  ref.route('**/*',lambda r:r.continue_() if r.request.url.startswith('http://127.0.0.1:') else r.abort())
  ref.goto(f'http://127.0.0.1:{server.server_port}/reference.html',wait_until='load')
  if ref.locator('#cookieAccept').is_visible():ref.locator('#cookieAccept').click()
  ref.evaluate('document.querySelector("#checkoutModal").classList.add("open");document.body.style.overflow="hidden"')
  with delivery_page(browser,viewport={'width':1440,'height':900},locale='ru-RU') as p:
   p.context.route('**/*',lambda r:r.abort() if is_order_submission(r.request) else r.fallback())
   identity=AssetIdentity(release_assets(os.environ['ROLLSBAR_DEPLOY_SHA']),BASE);p.on('response',identity.observe)
   p.goto(BASE+'/',wait_until='domcontentloaded');add_first_simple_product(p)
   settle_native(p)
   p.goto(BASE+'/checkout/',wait_until='domcontentloaded');p.locator('[data-rollsbar-modal="1"]').wait_for(state='visible')
   for width in [1440,701,700,390,320]:
    p.set_viewport_size({'width':width,'height':900});ref.set_viewport_size({'width':width,'height':900})
    p.locator('[data-rollsbar-modal="1"][role=dialog]').evaluate('e=>e.scrollTop=0');ref.locator('.checkout-panel').evaluate('e=>e.scrollTop=0')
    ref.wait_for_timeout(400)
    native=geometry(p,'[data-rollsbar-modal="1"]');source=geometry(ref,'.checkout-panel')
    for key in ['x','width']:require(abs(native[key]-source[key])<=2,'immutable modal '+key+' at '+str(width))
    for key in ['padding','radius','shadow']:require(native[key]==source[key],'immutable modal '+key+' at '+str(width))
    require(native['height']<=900*.92+2,'original modal viewport height bound')
    require(abs(native['y']-((900-native['height'])/2 if width>700 else 900-native['height']))<=2,'approved vertical modal alignment')
    backdrop=p.locator('.rollsbar-checkout-backdrop').evaluate('e=>{let s=getComputedStyle(e),r=e.getBoundingClientRect();return {background:s.backgroundColor,blur:s.backdropFilter,x:r.x,y:r.y,width:r.width,height:r.height}}')
    source_backdrop=ref.locator('#checkoutModal > .backdrop').evaluate('e=>{let s=getComputedStyle(e);return {background:s.backgroundColor,blur:s.backdropFilter}}')
    require(backdrop['background']==source_backdrop['background'] and backdrop['blur']==source_backdrop['blur'],'immutable backdrop color/blur')
    require(abs(backdrop['x'])<=1 and abs(backdrop['y'])<=1 and abs(backdrop['width']-width)<=1 and abs(backdrop['height']-900)<=1,'backdrop covers viewport')
    require(abs(geometry(p,'.wc-block-checkout__sidebar')['width']-geometry(ref,'.checkout-summary')['width'])<=2,'approved desktop/mobile summary lane width')
    p.screenshot(path=str(OUT/f'candidate-{width}.png'),animations='disabled');ref.screenshot(path=str(OUT/f'reference-{width}.png'),animations='disabled')
    diff=ImageChops.difference(Image.open(OUT/f'candidate-{width}.png').convert('RGB'),Image.open(OUT/f'reference-{width}.png').convert('RGB'));diff.save(OUT/f'diff-{width}.png')
    report['checks'].append({'width':width,'status':'PASS','native':native,'source':source,'unmasked_mean_absolute_pixel_difference':sum(ImageStat.Stat(diff).mean)/3})
   identity.verify([])
  browser.close()
 report['status']='MODAL_CHROME_PASS_CONTENT_CHANGED_BY_OWNER'
finally:
 server.shutdown()
 report['immutable_asset_sha256']=source_assets
 (OUT/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

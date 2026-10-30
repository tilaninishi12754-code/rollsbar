"""Un-routed storefront first-paint probe; no cart mutations/order submissions."""
import json,sys,argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
out=Path('qa/visual-results/storefront-loading');out.mkdir(parents=True,exist_ok=True)
rows=[]
with sync_playwright() as pw:
 b=pw.chromium.launch()
 for width in [1440,390]:
  for run in range(3):
   c=b.new_context(viewport={'width':width,'height':900},locale='ru-RU');p=c.new_page()
   response=p.goto('https://staging.rollsbar.ru/',wait_until='domcontentloaded',timeout=60000)
   p.wait_for_function('performance.getEntriesByName("first-contentful-paint").length>0')
   p.locator('[data-rollsbar-cart-delta]').first.wait_for(state='visible')
   row=p.evaluate('''()=>{const n=performance.getEntriesByType('navigation')[0];return {ttfb:n.responseStart,dns:n.domainLookupEnd-n.domainLookupStart,connect:n.connectEnd-n.connectStart,server_wait:n.responseStart-n.requestStart,html_end:n.responseEnd,dom_ready:n.domContentLoadedEventEnd,fcp:performance.getEntriesByName('first-contentful-paint')[0].startTime,resources:performance.getEntriesByType('resource').sort((a,b)=>b.duration-a.duration).slice(0,12).map(r=>({url:r.name,duration:r.duration,start:r.startTime,size:r.transferSize}))}}''')
   row.update(width=width,run=run,status=response.status);rows.append(row)
   print(json.dumps({k:v for k,v in row.items() if k!='resources'}),flush=True)
   c.close()
 b.close()
(out/(args.label+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')

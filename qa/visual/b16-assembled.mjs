import {chromium} from '../node_modules/@playwright/test/index.mjs';
import {startPreview} from './server.mjs';
import {writeFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const preview=process.env.ROLLSBAR_REUSE_PREVIEW==='1'?{close:async()=>{}}:await startPreview();
const browser=await chromium.launch();
const rows=[];
try {
 for(const width of [1440,1051,1050,1024,701,700,390,320]){
  const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
  const pair={width};
  for(const mode of ['approved','current']){
   const page=await context.newPage();
   await page.addInitScript(()=>{try{localStorage.setItem('rollsbar_cookie_notice','1');}catch{}});
   await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
   await page.goto(`http://127.0.0.1:4178/${mode==='approved'?'approved/demo.html':'current/'}`);
   const doc=mode==='approved'?page.frameLocator('#stage').frameLocator('#site'):page;
   await doc.locator(mode==='approved'?'body[data-final-demo-fixes="1"]':'.rollsbar-product-grid').first().waitFor();
   if(mode==='approved')pair.approvedRaw=await doc.locator('body').evaluate(body=>{
    const w=body.ownerDocument.defaultView;
    return [...body.querySelectorAll('section[id],footer')].map(n=>{const r=n.getBoundingClientRect();return {id:n.id||'footer',top:r.top+w.scrollY,height:r.height};});
   });
   if(mode==='approved')await doc.locator('body').evaluate(body=>{
    // Existing B6B accepted canonical accent copies, not a B16 allowance.
    for(const [id,color]of Object.entries({'pizza-pepperoni':'blue','sets-hit-set':'red','soups-tom-yam':'warm'}))
     for(const btn of body.querySelectorAll(`[data-original-add="${id}"]`))btn.closest('article').classList.add('client-accent',`client-accent-${color}`);
   });
   pair[mode]=await doc.locator('body').evaluate(async body=>{
    await body.ownerDocument.fonts.ready;
    const d=body.ownerDocument,w=d.defaultView;
    const rect=n=>{const r=n.getBoundingClientRect();return {top:r.top+w.scrollY,height:r.height,left:r.left,width:r.width};};
    const sections=['rolls','pizza','hits','combo','sets','baked','tempura','desserts','drinks','snacks','wok','soups','delivery','contacts'].map(id=>{const n=d.getElementById(id),h=n?.querySelector('h2');return {id,...(n?rect(n):{}),heading:h?.textContent.trim(),headingRect:h?rect(h):null,paddingTop:n?w.getComputedStyle(n).paddingTop:null};});
    const ids=[...d.querySelectorAll('[id]')].map(n=>n.id);
    const selectors={header:'header',categories:'.category-nav,.rollsbar-category-nav',promo:'.client-promo-wrap,.rollsbar-utilities',footer:'footer'};
    const landmarks=Object.fromEntries(Object.entries(selectors).map(([k,s])=>[k,rect(d.querySelector(s))]));
    const copy=[...d.querySelectorAll('#delivery .delivery-card__head p,#delivery .condition span,#delivery .notice')].map(n=>({text:n.textContent.trim(),...rect(n)}));
    const order=[...d.querySelectorAll('section[id]')].map(n=>n.id).filter(id=>sections.some(s=>s.id===id));
    const deliveryStyles=Object.fromEntries(['.delivery-layout','.delivery-card','.delivery-card__head','.conditions-card','.notice','.map-note','.yandex-map-wrap','.map-zone-legend'].map(selector=>{
     const s=w.getComputedStyle(d.querySelector('#delivery '+selector));return [selector,Object.fromEntries(['backgroundColor','color','borderRadius','borderTopWidth','borderTopColor','paddingTop','paddingRight','paddingBottom','paddingLeft','fontSize','lineHeight','gap'].map(k=>[k,s[k]]))];
    }));
    return {sections,order,landmarks,copy,deliveryStyles,duplicates:ids.filter((id,i)=>ids.indexOf(id)!==i),pageHeight:d.documentElement.scrollHeight,overflow:d.documentElement.scrollWidth-w.innerWidth};
   });
   if(process.env.ROLLSBAR_B16_DIAGNOSTICS==='1'&&[1440,320].includes(width))await doc.locator('#delivery').screenshot({path:`qa/visual-results/b16-${mode}-${width}-delivery.png`});
   await page.close();
  }
  rows.push(pair);await context.close();
 }
 writeFileSync('qa/visual/B16_ASSEMBLED.json',JSON.stringify(rows,null,2)+'\n');
 if(process.argv.includes('--measure'))console.log(JSON.stringify(rows.map(r=>({width:r.width,deltas:r.current.sections.map((s,i)=>({id:s.id,top:s.top-r.approved.sections[i].top,height:s.height-r.approved.sections[i].height}))})),null,2));
 if(!process.argv.includes('--measure'))for(const r of rows){
  assert.deepEqual(r.current.duplicates,[]);assert.equal(r.current.overflow,0);
  assert.deepEqual(r.current.order,r.approved.order);assert.deepEqual(r.current.order,r.current.sections.map(s=>s.id));
  assert.deepEqual(r.current.deliveryStyles,r.approved.deliveryStyles,`${r.width} Delivery surfaces/typography/spacing`);
  for(let i=0;i<r.current.sections.length;i++){
   const a=r.approved.sections[i],c=r.current.sections[i];
   if(i>0)assert(Math.abs(c.top-a.top)<=.02,`${r.width} ${c.id} start`);
   // First section owns approved main padding in current's wrapper; compare content.
   assert(Math.abs(c.headingRect.top-a.headingRect.top)<=.02,`${r.width} ${c.id} heading`);
   assert(Math.abs(c.top+c.height-a.top-a.height)<=.02,`${r.width} ${c.id} end`);
  }
  for(const k of Object.keys(r.current.landmarks)){
   const a=r.approved.landmarks[k],c=r.current.landmarks[k];
   assert(Math.abs(a.top-c.top)<=.02,`${r.width} ${k} start`);assert(Math.abs(a.height-c.height)<=.02,`${r.width} ${k} height`);
  }
  assert.equal(r.current.pageHeight,r.approved.pageHeight,`${r.width} document end`);
  console.log(`B16 assembled ${r.width}: PASS`);
 }
}finally{await browser.close();await preview.close();}

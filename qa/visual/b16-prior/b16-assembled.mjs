import {chromium} from '../node_modules/@playwright/test/index.mjs';
import {startPreview} from './server.mjs';
import {writeFileSync} from 'node:fs';
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
   pair[mode]=await doc.locator('body').evaluate(async body=>{
    await body.ownerDocument.fonts.ready;
    const d=body.ownerDocument,w=d.defaultView;
    const rect=n=>{const r=n.getBoundingClientRect();return {top:r.top+w.scrollY,height:r.height,left:r.left,width:r.width};};
    const sections=['rolls','pizza','hits','combo','sets','baked','tempura','desserts','drinks','snacks','wok','soups','delivery','contacts'].map(id=>{const n=d.getElementById(id),h=n?.querySelector('h2');return {id,...(n?rect(n):{}),heading:h?.textContent.trim(),headingRect:h?rect(h):null,paddingTop:n?w.getComputedStyle(n).paddingTop:null};});
    const ids=[...d.querySelectorAll('[id]')].map(n=>n.id);
    return {sections,duplicates:ids.filter((id,i)=>ids.indexOf(id)!==i),pageHeight:d.documentElement.scrollHeight,overflow:d.documentElement.scrollWidth-w.innerWidth};
   });
   await page.close();
  }
  rows.push(pair);await context.close();
 }
 writeFileSync('qa/visual/B16_ASSEMBLED.json',JSON.stringify(rows,null,2)+'\n');
 console.log(JSON.stringify(rows.map(r=>({width:r.width,duplicates:r.current.duplicates,overflow:r.current.overflow,deltas:r.current.sections.map((s,i)=>({id:s.id,top:s.top-r.approved.sections[i].top,height:s.height-r.approved.sections[i].height}))})),null,2));
}finally{await browser.close();await preview.close();}

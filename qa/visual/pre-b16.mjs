// Geometry/behavior only. Never reads or writes screenshot expectations.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { chromium, firefox, webkit, expect } from '../node_modules/@playwright/test/index.mjs';
import { startPreview } from './server.mjs';
import { cardGeometry } from './b6b-card-helpers.mjs';
import { footerOverflow } from './b15-footer-helpers.mjs';
import { searchGeometry } from './b14-search-helpers.mjs';

export const canonicalWidths=[1440,1051,1050,1024,701,700,390,320];
export const denseWidths=[...new Set([...Array.from({length:57},(_,i)=>320+i*20),390,699,701,899,900,901,1023,1024,1025,1049,1050,1051,1439])].sort((a,b)=>a-b);
const engines={chromium,firefox,webkit};
const filter=process.argv[2];
if(filter&&!Object.hasOwn(engines,filter))throw Error('Optional argument: chromium, firefox, webkit');
const manifest=JSON.parse(readFileSync('qa/visual/baseline-manifest.json'));
function hashes(){
 assert.equal(Object.keys(manifest.hashes).length,285);
 for(const [file,hash] of Object.entries(manifest.hashes))assert.equal(createHash('sha256').update(readFileSync(`qa/visual/baselines/${file}`)).digest('hex'),hash,file);
 return 285;
}
const output='qa/visual/PRE_B16_RESPONSIVE_CROSS_BROWSER.json';
const evidence={status:'RUNNING',node:process.version,playwright:JSON.parse(readFileSync('qa/node_modules/@playwright/test/package.json')).version,
 grid:{algorithm:'320 + 20*n, n=0..56; union explicit breakpoint neighbors and 390',widths:denseWidths,maxOrdinaryGap:20},
 baselineHashes:hashes(),browsers:{},rows:[],scope:'Local PHP/Woo adapters; no live backend verification; B16 not started'};
evidence.diagnostic=!!(filter||process.env.ROLLSBAR_QA_WIDTHS);
const revisions=JSON.parse(readFileSync('qa/node_modules/.pnpm/playwright-core@'+evidence.playwright+'/node_modules/playwright-core/browsers.json')).browsers;
const save=()=>writeFileSync(output,JSON.stringify(evidence,null,2)+'\n');
const preview=await startPreview();
try {
 for(const [engine,type] of Object.entries(engines)){
  if(filter&&engine!==filter)continue;
  const browser=await type.launch({timeout:30000});
  evidence.browsers[engine]={version:browser.version(),revision:revisions.find(b=>b.name===engine).revision,executable:type.executablePath()};save();
  try {
   for(const width of process.env.ROLLSBAR_QA_WIDTHS?process.env.ROLLSBAR_QA_WIDTHS.split(',').map(Number):engine==='chromium'?denseWidths:canonicalWidths){
    const row={browser:engine,width,height:900,status:'RUNNING',states:[],jsErrors:[],warnings:[],metrics:{}};
    evidence.rows.push(row);save();
    const context=await browser.newContext({viewport:{width,height:900},deviceScaleFactor:1,locale:'ru-RU',timezoneId:'Europe/Moscow',colorScheme:'light',reducedMotion:'reduce',serviceWorkers:'block'});
    const page=await context.newPage();page.setDefaultTimeout(10000);
    page.on('pageerror',e=>row.jsErrors.push(e.message));
    page.on('console',m=>{if(m.type()==='warning')row.warnings.push(m.text());if(m.type()==='error'&&!m.text().startsWith('Failed to load resource:'))row.jsErrors.push(m.text());});
    let state='load';
    const step=async(name,fn)=>{state=name;await fn();row.states.push(name);};
    const body=page.locator('body'),modal=page.locator('#rollsbarProductDetails'),drawer=page.locator('#rollsbarCartDrawer');
    const cards=id=>page.locator(`.rollsbar-product-card[data-rollsbar-source-id="${id}"]`);
    const frame=()=>page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
    const request=request=>page.evaluate(async request=>{
     const r=await fetch('/fixture-cart',{method:'POST',body:new URLSearchParams({nonce:'local-fixture',request:JSON.stringify(request)})});const result=await r.json();if(!result.success)throw Error(JSON.stringify(result));return result.data;
    },request);
    const unlocked=async()=>{await expect(body).not.toHaveCSS('overflow','hidden');await expect(page.locator('[inert]')).toHaveCount(0);};
    const panelGeometry=async(selector,key)=>{
     const metrics=await page.locator(selector).evaluate(p=>{
      const r=p.getBoundingClientRect();return {horizontal:Math.max(0,-r.left,r.right-innerWidth,p.scrollWidth-p.clientWidth),vertical:Math.max(0,-r.top,r.bottom-innerHeight),scrollHeight:p.scrollHeight,clientHeight:p.clientHeight};
     });row.metrics[key]=metrics;assert.equal(metrics.horizontal,0,`${key} horizontal`);assert.equal(metrics.vertical,0,`${key} vertical`);
    };
    const reachable=async locator=>{
     await locator.scrollIntoViewIfNeeded();await expect(locator).toBeInViewport();
     const m=await locator.evaluate(n=>{const r=n.getBoundingClientRect();const x=(r.left+r.right)/2,y=(r.top+r.bottom)/2;const top=document.elementFromPoint(x,y);return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,hit:!!top&&(n===top||n.contains(top))};});
     assert(m.left>=0&&m.right<=width&&m.top>=0&&m.bottom<=900&&m.hit,JSON.stringify(m));
    };
    const cartTrigger=populated=>page.locator(width<=700&&populated?'[data-rollsbar-orderbar]':width<=900?'[data-rollsbar-mobile-cart]':'.rollsbar-cart-link').first();
    const totals=async()=>{
     const data=await request({operation:'read'}),count=data.lines.reduce((n,l)=>n+l.quantity,0);
     for(const badge of await page.locator('.rollsbar-cart-count').all())await expect(badge).toHaveText(String(count));
     const normalize=s=>s.replace(/\s+/g,' ').trim();
     assert.equal(normalize(await page.locator('.rollsbar-header-cart-total').textContent()),normalize(data.subtotal));
     assert.equal(normalize(await page.locator('[data-rollsbar-order-total]').textContent()),normalize(data.subtotal));
     await expect(page.locator('[data-rollsbar-orderbar]')).toBeVisible({visible:width<=700&&count>0});
     await expect(page.locator('.rollsbar-cart-link:visible,[data-rollsbar-mobile-cart]:visible,[data-rollsbar-orderbar]:visible')).toHaveCount(1);
     await reachable(cartTrigger(count>0));return data;
    };
    const allCards=async key=>{
     const rows=await body.evaluate(cardGeometry);assert.equal(rows.length,126);
     const failures=rows.filter(c=>c.overflow||c.clipping||c.overlap||c.inkOverlap);
     const paintedFailures=await page.locator('.rollsbar-product-card').evaluateAll(cs=>cs.flatMap(c=>{
      const r=c.getBoundingClientRect(),p=c.querySelector('.rollsbar-price'),range=document.createRange();range.selectNodeContents(p);const ink=range.getBoundingClientRect();
      const excess=Math.max(0,c.scrollWidth-c.clientWidth,ink.right-r.right,r.left-ink.left,ink.bottom-r.bottom,r.top-ink.top);
      return excess>.02?[{id:c.dataset.rollsbarSourceId,excess,card:r.toJSON(),ink:ink.toJSON()}]:[];
     }));
     row.metrics[key]={representations:rows.length,failures,paintedFailures};assert.deepEqual(failures,[]);assert.deepEqual(paintedFailures,[]);
    };
    try {
     await step('load and catalog invariants',async()=>{
      await page.addInitScript(()=>{try{localStorage.setItem('rollsbar_cookie_notice','1');}catch{}});
      await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
      await page.goto('http://127.0.0.1:4178/current/');
      await expect(page.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();
      await page.addStyleTag({content:'*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}'});
      await page.evaluate(()=>document.fonts.ready);await frame();
      const ids=await page.locator('.rollsbar-product-card').evaluateAll(cs=>cs.map(c=>c.dataset.rollsbarSourceId));
      const source=JSON.parse(readFileSync('wordpress/data/catalog.json')).products.map(p=>p.id);
      assert.equal(ids.length,126);assert.deepEqual([...new Set(ids)].sort(),source.sort());assert.equal(await page.locator('#hits .rollsbar-product-card').count(),8);
      const products=JSON.parse(await page.locator('#rollsbarProductDetailsData').textContent());
      const parents=Object.values(products).filter(p=>p.selection.variations.length);
      const wok=Object.entries(products).filter(([id])=>id.startsWith('wok-'));
      row.invariants={canonical:new Set(ids).size,representations:ids.length,hits:8,variableParents:parents.length,variations:parents.reduce((n,p)=>n+p.selection.variations.length,0),wok:wok.length,wokChoices:wok.reduce((n,[,p])=>n+p.selection.options[0].choices.length,0),shrimpChoices:products['shrimp-tempura'].selection.options[0].choices.length};
      assert.deepEqual(row.invariants,{canonical:118,representations:126,hits:8,variableParents:13,variations:26,wok:6,wokChoices:18,shrimpChoices:3});
     });
     await step('global header sticky navigation promo cards',async()=>{
      const geometry=await page.evaluate(()=>{
       const bounds=n=>{const r=n.getBoundingClientRect();return Math.max(0,-r.left,r.right-innerWidth);};
       const header=document.querySelector('.rollsbar-header');
       const controls=[...header.querySelectorAll('a,button,input')].filter(n=>n.getClientRects().length&&getComputedStyle(n).visibility!=='hidden');
       const nav=document.querySelector('.rollsbar-category-nav');
       const collisions=[];for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){const a=controls[i],b=controls[j];if(a.contains(b)||b.contains(a))continue;const x=a.getBoundingClientRect(),y=b.getBoundingClientRect();if(Math.min(x.right,y.right)-Math.max(x.left,y.left)>.5&&Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top)>.5)collisions.push([a.outerHTML,b.outerHTML]);}
       return {page:Math.max(0,document.documentElement.scrollWidth-innerWidth),bodyOverflowX:getComputedStyle(document.body).overflowX,htmlOverflowX:getComputedStyle(document.documentElement).overflowX,header:bounds(header),controls:Math.max(0,...controls.map(bounds)),collisions,nav:bounds(nav),sticky:getComputedStyle(nav).position,promo:bounds(document.querySelector('.rollsbar-utilities')),cards:Math.max(0,...[...document.querySelectorAll('.rollsbar-product-card')].map(bounds))};
      });row.metrics.global=geometry;
      for(const key of ['page','header','controls','nav','promo','cards'])assert.equal(geometry[key],0,key);
      assert(!['hidden','clip'].includes(geometry.bodyOverflowX));assert(!['hidden','clip'].includes(geometry.htmlOverflowX));assert.deepEqual(geometry.collisions,[]);assert.equal(geometry.sticky,'sticky');
      await page.evaluate(()=>scrollTo(0,600));await frame();
      const nav=await page.locator('.rollsbar-category-nav').boundingBox(),header=await page.locator('.rollsbar-header').boundingBox();
      row.metrics.sticky={nav,header};
      assert(nav.y>=header.y+header.height-1,JSON.stringify(row.metrics.sticky));assert(nav.y+nav.height<=900);
      await allCards('initialCards');await totals();
     });
     await step('details close focus scroll and internal scroll',async()=>{
      const opener=cards('tyahan-chicken').first().locator('h3 a');await opener.click();await expect(modal).toBeVisible();
      await panelGeometry('.rollsbar-product-details__panel','details');
      const panel=modal.locator('.rollsbar-product-details__panel');
      await panel.evaluate(p=>p.scrollTop=p.scrollHeight);const m=await panel.evaluate(p=>({needed:p.scrollHeight>p.clientHeight,top:p.scrollTop}));assert(!m.needed||m.top>0);row.metrics.detailsScroll=m;
      await reachable(modal.locator('.rollsbar-product-details__close'));await page.keyboard.press('Escape');await expect(modal).not.toBeVisible();await expect(opener).toBeFocused();await unlocked();
      // Playwright may scroll the opener before clicking (notably WebKit behind
      // sticky navigation). Restoration is relative to the actual opening event.
      await opener.evaluate(n=>n.addEventListener('click',()=>{window.__preB16OpeningY=scrollY;},{capture:true,once:true}));
      await opener.click();await modal.locator('.rollsbar-product-details__close').click();
      row.metrics.detailsRestoration=await page.evaluate(()=>({opening:window.__preB16OpeningY,restored:scrollY}));
      assert.equal(row.metrics.detailsRestoration.restored,row.metrics.detailsRestoration.opening);await unlocked();
     });
     await step('variable WOK shrimp selector options and add',async()=>{
      for(const id of ['snacks-naggetsy','wok-udon-chicken','shrimp-tempura']){
       const opener=cards(id).first().locator('[data-rollsbar-selection-open]');await opener.click();await expect(modal).toBeVisible();
       await panelGeometry('.rollsbar-product-details__panel',`selector:${id}`);
       const select=modal.locator('select');await reachable(select);await select.selectOption({index:1});await expect(modal.locator('.rollsbar-product-options__add')).toBeEnabled();
       await reachable(modal.locator('.rollsbar-product-options__close'));await reachable(modal.locator('.rollsbar-product-options__add'));
       await modal.locator('.rollsbar-product-options__add').click();await expect(modal).not.toBeVisible();await expect(opener).toBeFocused();await unlocked();
      }
      await totals();
     });
     await step('simple counters zero and Catalog Hits synchronization',async()=>{
      const cs=cards('rolls-filadelfiya');assert.equal(await cs.count(),2);
      await cs.first().locator('[data-rollsbar-cart-delta="1"]').click();
      for(const c of await cs.all())await expect(c.locator('.rollsbar-product-counter span')).toHaveText('1');
      await cs.last().locator('[data-rollsbar-cart-delta="1"]').click();
      for(const c of await cs.all())await expect(c.locator('.rollsbar-product-counter span')).toHaveText('2');
      await cs.first().locator('[data-rollsbar-cart-delta="-1"]').click();await cs.last().locator('[data-rollsbar-cart-delta="-1"]').click();
      for(const c of await cs.all())await expect(c.locator('.rollsbar-product-counter')).toHaveCount(0);
      for(const id of ['rolls-filadelfiya','sets-mega-set','soups-tom-yam'])await cards(id).first().locator('[data-rollsbar-cart-delta="1"]').click();
      await allCards('counterCards');await totals();
     });
     await step('drawer quantity remove close and scroll restoration',async()=>{
      const trigger=cartTrigger(true);await trigger.click();await expect(drawer).toBeVisible();await panelGeometry('.rollsbar-cart-drawer__panel','drawer');
      const line=drawer.locator('.rollsbar-cart-item[data-source-id="rolls-filadelfiya"]');
      await line.locator('[data-drawer-action="line_plus"]').click();for(const c of await cards('rolls-filadelfiya').all())await expect(c.locator('.rollsbar-product-counter span')).toHaveText('2');
      await line.locator('[data-drawer-action="line_minus"]').click();await expect(line.locator('.rollsbar-drawer-qty span')).toHaveText('1');await reachable(line.locator('[data-drawer-action="line_remove"]'));await line.locator('[data-drawer-action="line_remove"]').click();await expect(line).toHaveCount(0);
      await reachable(drawer.locator('.rollsbar-drawer-close'));await page.keyboard.press('Escape');await expect(trigger).toBeFocused();await unlocked();
      const y=await page.evaluate(()=>scrollY);await trigger.click();await drawer.locator('.rollsbar-drawer-close').click();assert.equal(await page.evaluate(()=>scrollY),y);await unlocked();
     });
     await step('populated drawer vertical scrolling and bottom controls',async()=>{
      const products=JSON.parse(await page.locator('#rollsbarProductDetailsData').textContent());
      for(const [id,p] of Object.entries(products).filter(([,p])=>!p.selection.required).slice(0,15))await request({operation:'add',source_id:id,product_id:p.woo_id});
      const seeded=await request({operation:'read'});
      await cartTrigger(true).click();await expect(drawer.locator('.rollsbar-cart-item')).toHaveCount(seeded.lines.length);
      await panelGeometry('.rollsbar-cart-drawer__panel','longDrawer');
      const list=drawer.locator('.rollsbar-drawer-body');
      const m=await list.evaluate(p=>{p.scrollTop=p.scrollHeight;return {horizontal:Math.max(0,p.scrollWidth-p.clientWidth),top:p.scrollTop,range:p.scrollHeight-p.clientHeight};});row.metrics.drawerScroll=m;assert.equal(m.horizontal,0);assert(m.range>0&&m.top>0);
      await reachable(drawer.locator('[data-drawer-action="line_remove"]').last());await reachable(drawer.locator('.rollsbar-drawer-close'));await page.keyboard.press('Escape');await unlocked();await totals();
     });
     await step('live search query result details Escape focus',async()=>{
      await page.evaluate(()=>scrollTo(0,0));const open=page.locator('[data-rollsbar-search-open]');await open.click();
      const input=page.locator('.product-search__input');await expect(input).toBeFocused();await input.fill('Тяхан');
      const g=await body.evaluate(searchGeometry);row.metrics.search=g;for(const k of ['page','header','search','panel','results'])assert.equal(g[k],0,k);
      const result=page.locator('[data-search-product="tyahan-chicken"]');await reachable(input);await reachable(result);await result.click();await expect(modal).toHaveAttribute('data-source-id','tyahan-chicken');await expect(modal).toBeVisible();await page.keyboard.press('Escape');await unlocked();
      await open.click();await input.fill('неттакогоблюда999');await page.keyboard.press('Escape');await expect(page.locator('.product-search')).not.toBeVisible();await expect(open).toBeFocused();await unlocked();
     });
     await step('footer fixed controls reachability',async()=>{
      await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));await frame();
      const footer=page.locator('.rollsbar-footer');await expect(footer).toBeInViewport();
      for(const link of await footer.locator('a').all())await reachable(link);
      await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));await frame();
      const fixed=await cartTrigger(true).boundingBox();
      for(const link of await footer.locator('a').all()){const r=await link.boundingBox();assert(r.y>=0&&r.y+r.height<=900);if(width<=900)assert(r.y+r.height<fixed.y);}
      row.metrics.inlineBoxes=await page.locator('#contacts a').evaluateAll(ns=>ns.map(n=>({text:n.textContent,clientWidth:n.clientWidth,scrollWidth:n.scrollWidth,rects:[...n.getClientRects()].map(r=>({left:r.left,right:r.right}))})));
      const m=await body.evaluate(footerOverflow);row.metrics.footer=m;assert.deepEqual(m,{page:0,footer:0,content:0,header:0,search:0,mobile:0});
     });
     await step('remove all empty cart access and restoration',async()=>{
      await cartTrigger(true).click();
      let remaining=await drawer.locator('.rollsbar-cart-item').count();
      while(remaining){await drawer.locator('[data-drawer-action="line_remove"]').first().click();await expect(drawer.locator('.rollsbar-cart-item')).toHaveCount(--remaining);}
      await expect(page.locator('.rollsbar-cart-empty')).toBeVisible();await page.keyboard.press('Escape');await unlocked();await totals();
      const trigger=cartTrigger(false);await trigger.focus();await page.keyboard.press('Enter');await expect(drawer).toBeVisible();await page.keyboard.press('Escape');await expect(trigger).toBeFocused();await unlocked();
      assert.deepEqual(row.jsErrors,[]);assert.deepEqual(row.warnings,[]);
     });
     row.status='PASS';console.log(`${engine} ${width}: PASS`);
    } catch(error){
     row.status='FAIL';row.failure={state,message:error.message,stack:error.stack};
     row.failure.elements=await page.evaluate(()=>[...document.querySelectorAll('.rollsbar-footer a,.rollsbar-footer p,#contacts article,#contacts a')].filter(n=>n.getClientRects().length).map(n=>({tag:n.tagName,text:n.textContent,display:getComputedStyle(n).display,scroll:n.scrollWidth,client:n.clientWidth,rect:n.getBoundingClientRect().toJSON()})));
     const dir=`qa/visual-results/pre-b16/${engine}-${width}`;mkdirSync(dir,{recursive:true});
     row.failure.screenshot=`${dir}/failure.png`;await page.screenshot({path:row.failure.screenshot}).catch(()=>{});
     writeFileSync(`${dir}/failure.json`,JSON.stringify(row,null,2));console.log(`${engine} ${width}: FAIL (${state}): ${error.message.slice(0,240)}`);
    } finally {await context.close();save();}
   }
  } finally {await browser.close();}
 }
 if(!evidence.diagnostic)for(const name of Object.keys(engines))assert.deepEqual(evidence.rows.filter(r=>r.browser===name).map(r=>r.width),name==='chromium'?denseWidths:canonicalWidths);
 evidence.baselineHashesAfter=hashes();evidence.status=evidence.rows.every(r=>r.status==='PASS')?(evidence.diagnostic?'DIAGNOSTIC_PASS':'PASS'):'FAIL';save();
 process.exitCode=['PASS','DIAGNOSTIC_PASS'].includes(evidence.status)?0:1;
} catch(error){evidence.status='BLOCKED';evidence.infrastructureError={message:error.message,stack:error.stack};save();process.exitCode=1;console.error(error.message);
} finally {await preview.close();}

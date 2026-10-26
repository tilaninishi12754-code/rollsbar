import { chromium, webkit, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import { startPreview } from './server.mjs';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
const live=process.env.ROLLSBAR_UX_BASE;
if(live&&new URL(live).origin!=='https://staging.rollsbar.ru')throw Error('Only staging is authorized');
const out='qa/visual-results/storefront-ux'+(live?'-staging':'');mkdirSync(out,{recursive:true});
const report={status:'RUNNING',release_sha:process.env.ROLLSBAR_DEPLOY_SHA||'candidate',live_backend:!!live,checks:[],screenshots:[]};
const server=live?null:await startPreview({port:4180});
async function run(engine,name){
 const browser=await engine.launch();
 try{
 for(const [width,height] of [[1440,900],[390,844],[390,900],[430,932],[320,568]]){
  const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce',locale:'ru-RU'}),page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>localStorage.setItem('rollsbar_cookie_notice','1'));
  if(!live)await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
  const base=live||'http://127.0.0.1:4180/current/';
  await page.goto(base+(live?'/?ux='+report.release_sha:''),{waitUntil:'domcontentloaded'});
  await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});
  await expect(page.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();
  const data=JSON.parse(await page.locator('#rollsbarProductDetailsData').textContent());
  expect(Object.keys(data)).toHaveLength(118);
  expect(await page.locator('.rollsbar-product-card').count()).toBe(126);
  if(live&&width===1440){
   const media=JSON.parse(readFileSync(out+'/media.json','utf8'));
   for(const asset of media.assets){const r=await context.request.get(asset.url);expect(r.ok()).toBeTruthy();expect(createHash('sha256').update(await r.body()).digest('hex')).toBe(asset.sha256);}
   for(const product of media.products){
    const img=page.locator('.rollsbar-catalog-section:not(#hits) [data-rollsbar-source-id="'+product.source_id+'"] .rollsbar-product-card__media img');
    expect(await img.getAttribute('src')).toBe(product.display_url);expect(data[product.source_id].media).toContain(product.display_url);
   }
   report.media={assets:media.assets.length,products:media.products.length,status:'PASS'};
  }
  const simple=Object.keys(data).find(id=>!data[id].selection.required),pizza='pizza-tsezar',option=Object.keys(data).find(id=>data[id].selection.options.length&&!data[id].selection.blocked);
  const pizzaId=data[pizza]?pizza:Object.keys(data).find(id=>data[id].pizza&&data[id].name.includes('Цезарь'));
  if(!pizzaId)throw Error('Missing Caesar pizza');
  const card=id=>page.locator('.rollsbar-catalog-section:not(#hits) [data-rollsbar-source-id="'+id+'"]').first();
  const modal=page.locator('#rollsbarProductDetails');
  async function open(id){await card(id).locator('[data-rollsbar-detail-open]').first().click();await expect(modal).toBeVisible();}
  async function qty(n){await expect(modal.locator('.rollsbar-detail-quantity')).toBeVisible();await expect(modal.locator('[data-detail-delta="-1"]')).toBeDisabled();for(let i=1;i<n;i++)await modal.locator('[data-detail-delta="1"]').click();await expect(modal.locator('output')).toHaveText(String(n));}
  async function snap(){return page.evaluate(async()=>{const c=window.rollsbarCart;return (await(await fetch(c.url,{method:'POST',credentials:'same-origin',body:new URLSearchParams({nonce:c.nonce,request:JSON.stringify({operation:'read'})})})).json()).data;});}
  async function request(req){return page.evaluate(async req=>{const c=window.rollsbarCart;return (await(await fetch(c.url,{method:'POST',credentials:'same-origin',body:new URLSearchParams({nonce:c.nonce,request:JSON.stringify(req)})})).json());},req);}
  async function shot(label){const path=out+'/'+name+'-'+width+'x'+height+'-'+label+'.png';await page.screenshot({path});report.screenshots.push(path);}
  async function geometry(){
   const g=await page.evaluate(()=>{const h=document.querySelector('.rollsbar-header').getBoundingClientRect(),n=document.querySelector('.rollsbar-category-nav').getBoundingClientRect();return {top:h.top,bottom:h.bottom,nav:n.top,overflow:document.documentElement.scrollWidth-innerWidth};});
   expect(g.top).toBe(0);expect(g.overflow).toBe(0);if(width<=700)expect(Math.abs(g.nav-g.bottom)).toBeLessThan(1.1);
   return g;
  }
  await open(simple);await qty(3);await shot('details-quantity');
  const adds=[];page.on('request',r=>{try{const q=JSON.parse(new URLSearchParams(r.postData()).get('request'));if(q.operation==='add')adds.push(q);}catch{}});
  await modal.locator('.rollsbar-product-details__add').click();await expect(modal).toBeHidden();expect(adds.length).toBe(1);expect(adds[0].quantity).toBe(3);
  expect((await snap()).counts[simple]).toBe(3);await expect(card(simple).locator('.rollsbar-product-counter span')).toHaveText('3');
  await card(simple).locator('[data-rollsbar-cart-delta="-1"]').click();await expect(card(simple).locator('.rollsbar-product-counter span')).toHaveText('2');
  await card(simple).locator('[data-rollsbar-cart-delta="1"]').click();await expect(card(simple).locator('.rollsbar-product-counter span')).toHaveText('3');
  const variants=data[pizzaId].selection.variations;
  const thirty=variants.find(v=>/30/.test(v.label)),fifty=variants.find(v=>/50/.test(v.label));expect(!!thirty&&!!fifty).toBeTruthy();
  for(const [v,n] of [[thirty,2],[fifty,3]]){
   await open(pizzaId);await modal.locator('.rollsbar-product-details__add').click();await modal.locator('[data-variation]').selectOption(String(v.id));await qty(n);await modal.locator('.rollsbar-product-options__add').click();await expect(modal).toBeHidden();
   const state=await snap(),line=state.lines.find(l=>l.source_id===pizzaId&&l.variation_id===v.id);expect(line.quantity).toBe(n);
   if(v===thirty){
    await expect(card(pizzaId).locator('.rollsbar-product-counter span')).toHaveText('2');await card(pizzaId).locator('[data-rollsbar-cart-delta="1"]').click();await expect(card(pizzaId).locator('.rollsbar-product-counter span')).toHaveText('3');
    expect((await snap()).lines.find(l=>l.key===line.key).quantity).toBe(3);
    await page.reload({waitUntil:'domcontentloaded'});await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});await expect(card(pizzaId).locator('.rollsbar-product-counter span')).toHaveText('3');
    await card(pizzaId).locator('[data-rollsbar-cart-delta="-1"]').click();await expect(card(pizzaId).locator('.rollsbar-product-counter span')).toHaveText('2');
   }
  }
  await expect(card(pizzaId).locator('.rollsbar-pizza-total')).toHaveText('5 в корзине');
  const before=await snap();await card(pizzaId).locator('.rollsbar-pizza-total').click();await expect(modal.locator('.rollsbar-product-options')).toBeVisible();expect((await snap()).lines).toEqual(before.lines);await page.keyboard.press('Escape');
  const line=before.lines.find(l=>l.source_id===pizzaId);expect((await request({operation:'line_plus',key:line.key,source_id:pizzaId,variation_id:line.variation_id})).success).toBe(false);
  // Drawer preserves unambiguous editing even when two sizes exist.
  await page.locator(width<=700?'[data-rollsbar-orderbar]':'.rollsbar-cart-link').click();const drawer=page.locator('#rollsbarCartDrawer');
  await drawer.locator('[data-cart-key="'+line.key+'"] [data-drawer-action="line_plus"]').click();await expect(drawer.locator('[data-cart-key="'+line.key+'"] .rollsbar-drawer-qty span')).toHaveText('3');await page.keyboard.press('Escape');
  await open(option);await modal.locator('.rollsbar-product-details__add').click();await qty(2);await modal.locator('.rollsbar-product-options__add').click();await expect(modal).toBeHidden();expect((await snap()).counts[option]).toBe(2);
  const stable=await snap();
  for(const quantity of [0,-1,1.5,'2',null,true]){expect((await request({operation:'add',source_id:simple,product_id:data[simple].woo_id,quantity})).success).toBe(false);}
  for(const req of [{source_id:'wrong',product_id:data[simple].woo_id},{source_id:simple,product_id:data[simple].woo_id,variation_id:fifty.id},{source_id:option,product_id:data[option].woo_id,options:['wrong']},{source_id:pizzaId,product_id:data[pizzaId].woo_id,variation_id:data[Object.keys(data).find(id=>data[id].variable&&!data[id].pizza)].selection.variations[0].id}])expect((await request({operation:'add',quantity:2,...req})).success).toBe(false);
  expect((await snap()).lines).toEqual(stable.lines);
  for(const l of (await snap()).lines.filter(l=>l.source_id===pizzaId))await request({operation:'line_remove',key:l.key});
  await page.reload({waitUntil:'domcontentloaded'});await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});await expect(card(pizzaId).locator('[data-rollsbar-selection-open]')).toBeVisible();
  await open(pizzaId);await modal.locator('.rollsbar-product-details__add').click();await modal.locator('.rollsbar-product-options__add').click();await expect(modal).toBeHidden();await card(pizzaId).locator('[data-rollsbar-cart-delta="-1"]').click();await expect(card(pizzaId).locator('[data-rollsbar-selection-open]')).toBeVisible();expect((await snap()).counts[pizzaId]).toBeUndefined();
  await page.evaluate(()=>scrollTo(0,0));await expect(page.locator('.client-back-top')).toBeHidden();
  const geometries=[];for(const y of [0,300,700,1500,3500]){await page.evaluate(y=>scrollTo(0,y),y);await page.waitForTimeout(100);geometries.push({y,...await geometry()});}
  await expect(page.locator('.client-back-top')).toBeVisible();
  if(width<=700){await expect(page.locator('.mobile-phone')).toHaveAttribute('href','tel:+79786882288');
   const rects=await page.locator('.mobile-phone,.client-back-top,[data-rollsbar-orderbar]').evaluateAll(ns=>ns.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,r:r.right,b:r.bottom};}));for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){const a=rects[i],b=rects[j];expect(a.r<=b.x||b.r<=a.x||a.b<=b.y||b.b<=a.y).toBeTruthy();}}
  await shot('scrolled-controls');await page.locator('.client-back-top').click();await page.waitForFunction(()=>scrollY<2);await geometry();
  await page.evaluate(()=>scrollTo(0,900));
  for(const [trigger,close] of [['[data-rollsbar-search-open]','.product-search__close'],['[data-rollsbar-menu-open]','.rollsbar-site-menu__close']]){await page.locator(trigger).click();await page.locator(close).click();await geometry();}
  await open(simple);await page.keyboard.press('Escape');await geometry();await page.locator(width<=700?'[data-rollsbar-orderbar]':'.rollsbar-cart-link').click();await page.keyboard.press('Escape');await geometry();
  const ancestry=await page.locator('.rollsbar-header').evaluate(n=>{const rows=[];for(let a=n.parentElement;a;a=a.parentElement){const s=getComputedStyle(a);rows.push({tag:a.tagName,overflowX:s.overflowX,overflowY:s.overflowY,transform:s.transform,contain:s.contain});}return {ancestors:rows,visualViewport:window.visualViewport?{offsetTop:visualViewport.offsetTop,height:visualViewport.height,scale:visualViewport.scale}:null};});
  const queries=['пицца','пицца цезарь','цезарь пицца','пицца четыре сыра','четыре сыра','ролл филадельфия','филадельфия','  ПИЦЦА   ЦЕЗАРЬ  ','запечённые','запеченные','фила'];
  await page.locator('[data-rollsbar-search-open]').click();const results={};
  for(const q of queries){await page.locator('#rollsbarSearchInput').fill(q);const ids=await page.locator('[data-search-product]').evaluateAll(ns=>ns.map(n=>n.dataset.searchProduct));expect(ids.length,q).toBeGreaterThan(0);results[q]=ids;}
  expect(results['пицца цезарь']).toContain(pizzaId);expect(results['цезарь пицца']).toEqual(results['пицца цезарь']);expect(results['  ПИЦЦА   ЦЕЗАРЬ  ']).toEqual(results['пицца цезарь']);expect(results['запечённые']).toEqual(results['запеченные']);
  await page.locator('#rollsbarSearchInput').fill('пицца неттакогоблюда999');await expect(page.locator('[data-search-product]')).toHaveCount(0);
  await page.locator('#rollsbarSearchInput').fill('сыр');expect(await page.locator('[data-search-product]').first().locator('b').textContent()).toMatch(/сыр/i);
  await page.locator('#rollsbarSearchInput').fill('пицца цезарь');await page.locator('[data-search-product="'+pizzaId+'"]').click();await expect(modal).toHaveAttribute('data-source-id',pizzaId);await page.keyboard.press('Escape');
  await page.locator('[data-rollsbar-search-open]').click();await page.locator('#rollsbarSearchInput').fill('пицца четыре сыра');await shot('multi-word-search');await page.keyboard.press('Escape');
  if(live){const store=await context.request.get('https://staging.rollsbar.ru/wp-json/wc/store/v1/cart');expect(store.ok()).toBeTruthy();expect((await store.json()).items.reduce((n,l)=>n+l.quantity,0)).toBe((await snap()).lines.reduce((n,l)=>n+l.quantity,0));}
  expect(errors).toEqual([]);
  // Only this isolated anonymous test cart is cleaned up. Never submit an order.
  for(const l of (await snap()).lines)await request({operation:'line_remove',key:l.key});
  report.checks.push({engine:name,width,height,status:'PASS',queries:results,header:geometries,ancestry});writeFileSync(out+'/browser.json',JSON.stringify(report,null,2));
  console.log(name,width,height,'PASS');await context.close();
 }
 }finally{await browser.close();}
}
try{await run(chromium,'chromium');if(!live)await run(webkit,'webkit');report.status='PASS';}catch(e){report.status='FAIL';report.error=e.stack;throw e;}finally{writeFileSync(out+'/browser.json',JSON.stringify(report,null,2));await server?.close();}

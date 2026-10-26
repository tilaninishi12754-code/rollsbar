import { chromium, webkit, expect } from '@playwright/test';
import { mkdirSync,writeFileSync } from 'node:fs';
import { startPreview } from './server.mjs';
const live=process.env.ROLLSBAR_UX_BASE;
if(live&&new URL(live).origin!=='https://staging.rollsbar.ru')throw Error('Staging only');
const out=live?'qa/visual-results/storefront-ux-staging/interaction':'qa/visual-results/interaction-stability';mkdirSync(out,{recursive:true});
const report={status:'RUNNING',release_sha:process.env.ROLLSBAR_DEPLOY_SHA||'candidate',checks:[],screenshots:[]};
const server=live?null:await startPreview({port:4181});
try{for(const [name,engine] of [['chromium',chromium],...(!live?[['webkit',webkit]]:[])]){
const browser=await engine.launch();try{for(const width of [320,390,430,701,900,1440]){
 const context=await browser.newContext({viewport:{width,height:900},hasTouch:true,isMobile:width<=430,reducedMotion:'reduce'}),page=await context.newPage();
 await page.addInitScript(()=>localStorage.setItem('rollsbar_cookie_notice','1'));
 if(!live)await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
 const endpoint=live?'**/*wc-ajax=rollsbar_cart*':'**/fixture-cart';
 const base=live?live+'/?interaction='+report.release_sha:'http://127.0.0.1:4181/current/';
 const requests=[];page.on('request',r=>{try{const q=JSON.parse(new URLSearchParams(r.postData()).get('request'));if(q)requests.push(q)}catch{}});
 await page.goto(base,{waitUntil:'domcontentloaded'});
 const ready=()=>expect(page.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();await ready();
 const data=JSON.parse(await page.locator('#rollsbarProductDetailsData').textContent());
 const simple=Object.keys(data).find(id=>!data[id].selection.required),pizza=Object.keys(data).find(id=>data[id].pizza&&data[id].variable),vs=data[pizza].selection.variations;
 const card=id=>page.locator('.rollsbar-catalog-section:not(#hits) [data-rollsbar-source-id="'+id+'"]').first();
 const modal=page.locator('#rollsbarProductDetails'),drawer=page.locator('#rollsbarCartDrawer');
 const req=q=>page.evaluate(async request=>{const c=rollsbarCart;return(await(await fetch(c.url,{method:'POST',body:new URLSearchParams({nonce:c.nonce,request:JSON.stringify(request)})})).json()).data},q);
 const snap=()=>req({operation:'read'});
 async function reload(){await page.reload({waitUntil:'domcontentloaded'});await ready()}
 async function hit(loc,label){const box=await loc.boundingBox();expect(box,label).toBeTruthy();const result=await loc.evaluate(n=>{const r=n.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2,t=document.elementFromPoint(x,y);return {ok:!!t&&(t===n||n.contains(t)),target:t?.outerHTML.slice(0,400),inert:n.inert,visibility:getComputedStyle(n).visibility,scroll:scrollY,box:r.toJSON()}});if(!result.ok)console.log(label,result);expect(result.ok,label).toBe(true);return {label,...result}}
 async function tap(loc,label){await hit(loc,label);await loc.tap()}
 function cart(){return page.locator(width>900?'.rollsbar-cart-link':width>700?'[data-rollsbar-mobile-cart]': '[data-rollsbar-orderbar]:not([hidden]),[data-rollsbar-mobile-cart]:not([hidden])').first()}
 async function openCart(){await tap(cart(),'cart');await expect(drawer).toBeVisible();await expect(drawer.locator('.rollsbar-cart-drawer__panel')).toHaveAttribute('aria-busy','false');await page.keyboard.press('Escape');await expect(drawer).toBeHidden()}
 async function back(){await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';scrollTo(0,1100)});await expect(page.locator('.client-back-top')).toBeVisible();await expect(page.locator('.client-back-top')).toHaveClass(/show/);await page.locator('.client-back-top').evaluate(n=>n.getAnimations().forEach(a=>a.finish()));await tap(page.locator('.client-back-top'),'back top');await page.waitForFunction(()=>scrollY<2)}
 async function choose(v){await card(pizza).locator('[data-rollsbar-detail-open]').first().click();await modal.locator('.rollsbar-product-details__add').click();await modal.locator('[data-variation]').selectOption(String(v.id));await modal.locator('.rollsbar-product-options__add').tap();await expect(modal).toBeHidden();await ready()}
 const hits=[];
 await openCart();await back();
 // Controlled native pointer sequence: deliver response between down/up.
 // No synthetic replacement click and no timing sleeps.
 for(const target of ['cart','back','pending-cart']){
  for(const l of (await snap()).lines)await req({operation:'line_remove',key:l.key});await reload();
  await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';scrollTo(0,1100)});
  await expect(page.locator('.client-back-top')).toHaveClass(/show/);await page.locator('.client-back-top').evaluate(n=>n.getAnimations().forEach(a=>a.finish()));
  let release,arrived;const held=new Promise(r=>arrived=r);
  await page.route(endpoint,async route=>{const q=JSON.parse(new URLSearchParams(route.request().postData()).get('request'));if(q.operation!=='add')return route.continue();const response=await route.fetch();await new Promise(r=>{release=r;arrived()});await route.fulfill({response})});
  // Start mutation through an actual card tap, then scroll back to the fixed controls.
  await card(simple).locator('[data-rollsbar-cart-delta="1"]').tap();await held;
  await expect(card(simple)).toHaveAttribute('aria-busy','true');
  expect(await card(simple).evaluate(n=>getComputedStyle(n.querySelector('.rollsbar-product-card__body'),'::after').content)).toContain('Обновляем');
  if(width===390&&target==='cart'){const path=out+'/'+name+'-390-pending.png';await page.screenshot({path});report.screenshots.push(path);}
  const mutations=requests.filter(r=>r.operation==='add').length;
  await card(simple).locator('[data-rollsbar-cart-delta="1"]').evaluate(n=>n.click());expect(requests.filter(r=>r.operation==='add').length).toBe(mutations);
  await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';scrollTo(0,1100)});
  const loc=target!=='back'?cart():page.locator('.client-back-top');await expect(loc).toBeVisible();if(target==='back')await expect(loc).toHaveClass(/show/);await loc.evaluate(n=>n.getAnimations().forEach(a=>a.finish()));hits.push(await hit(loc,target+' pending'));
  const r=await loc.boundingBox(),x=r.x+r.width/2,y=target==='back'?r.y+r.height-5:r.y+r.height/2;
  await page.mouse.move(x,y);await page.mouse.down();if(target==='pending-cart'){await page.mouse.up();await expect(drawer).toBeVisible();await expect(drawer.locator('.rollsbar-cart-drawer__panel')).toHaveAttribute('aria-busy','true');}const finished=page.waitForEvent('requestfinished',r=>r.postData()?.includes('%22operation%22%3A%22add%22'));release();await finished;
  if(target!=='pending-cart')await page.mouse.up();await page.unroute(endpoint);if(target!=='back'){await expect(drawer).toBeVisible();await page.keyboard.press('Escape')}else await page.waitForFunction(()=>scrollY<2);
  await ready();expect((await snap()).counts[simple]).toBe(1);
 }
 // Repeated real taps after canonical rerenders, plus persisted state.
 for(let cycle=0;cycle<4;cycle++){
  await card(simple).locator('[data-rollsbar-cart-delta="1"]').tap();await ready();await openCart();await back();
  await card(simple).locator('[data-rollsbar-cart-delta="-1"]').tap();await ready();
  if(cycle===2)await reload();
 }
 await choose(vs[0]);await expect(card(pizza).locator('.rollsbar-product-counter span')).toHaveText('1');
 for(const persisted of [false,true]){if(persisted)await reload();const before=(await snap()).lines.find(l=>l.source_id===pizza);await card(pizza).locator('[data-rollsbar-cart-delta="1"]').tap();await ready();await expect(modal).toBeHidden();expect((await snap()).lines.find(l=>l.key===before.key).quantity).toBe(before.quantity+1)}
 await choose(vs[1]);await expect(card(pizza).locator('.rollsbar-pizza-total')).toBeVisible();const multi=await snap();await card(pizza).locator('.rollsbar-pizza-total').tap();await expect(modal.locator('.rollsbar-product-options')).toBeVisible();expect((await snap()).lines).toEqual(multi.lines);await page.keyboard.press('Escape');
 // Native Woo / another window removes a size while this card still projects two.
 await req({operation:'line_remove',key:multi.lines.find(l=>l.source_id===pizza&&l.variation_id===vs[1].id).key});
 await card(pizza).locator('.rollsbar-pizza-total').tap();await expect(card(pizza).locator('.rollsbar-product-counter span')).toHaveText('4');await expect(modal).toBeHidden();
 for(let n=3;n>=0;n--){await card(pizza).locator('[data-rollsbar-cart-delta="-1"]').tap();await ready();if(n)await expect(card(pizza).locator('.rollsbar-product-counter span')).toHaveText(String(n))}expect((await snap()).lines.some(l=>l.source_id===pizza)).toBe(false);await choose(vs[0]);
 // Failed response: restore usable controls, expose an error, do not retry add.
 let failed=false;await page.route(endpoint,route=>{const q=JSON.parse(new URLSearchParams(route.request().postData()).get('request'));if(q.operation==='add'&&!failed){failed=true;return route.fulfill({status:503,body:'unavailable'})}return route.continue()});
 await card(simple).locator('[data-rollsbar-cart-delta="1"]').tap();await expect(page.locator('.rollsbar-cart-error')).toBeVisible();await ready();await page.unroute(endpoint);
 for(const populated of [true,false]){
  if(!populated){for(const l of (await snap()).lines)await req({operation:'line_remove',key:l.key});await reload()}
  await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';scrollTo(0,1100)});await expect(page.locator('.client-back-top')).toBeVisible();await expect(page.locator('.client-back-top')).toHaveClass(/show/);await page.locator('.client-back-top').evaluate(n=>n.getAnimations().forEach(a=>a.finish()));
  for(const loc of [cart(),page.locator('.client-back-top'),...(width<=700?[page.locator('.mobile-phone')]:[])])hits.push(await hit(loc,'fixed '+populated));
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBe(0);
  const path=out+'/'+name+'-'+width+'-'+populated+'.png';await page.screenshot({path});report.screenshots.push(path);
  await openCart();await back();
 }
 report.checks.push({engine:name,width,status:'PASS',cycles:4,hits,requests:requests.length});writeFileSync(out+'/browser.json',JSON.stringify(report,null,2));console.log(name,width,'stability PASS');await context.close();
}}finally{await browser.close()}}
report.status='PASS';}catch(e){report.status='FAIL';report.error=e.stack;throw e}finally{writeFileSync(out+'/browser.json',JSON.stringify(report,null,2));await server?.close()}



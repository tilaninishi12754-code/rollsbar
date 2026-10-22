import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const baseline = process.env.ROLLSBAR_BASELINE==='1';
const exceptions = JSON.parse(readFileSync('qa/visual/accepted-exceptions.json'));
test.beforeEach(({},info)=>{
  for(const exception of exceptions.filter(row=>row.tests.includes(info.title)))
    info.annotations.push({type:'accepted-exception',description:exception.scope+': '+exception.reason});
});
test.beforeAll(({}, info)=>{
  if (baseline) return;
  expect(info.config.updateSnapshots).toBe('none');
  const manifest=JSON.parse(readFileSync('qa/visual/baseline-manifest.json'));
  expect(manifest.approvedSHA).toBe('a5e524392abcf89ffd5ace2a18218a6b59ed3b61');
  expect(process.platform).toBe(manifest.platform);
  expect(JSON.parse(readFileSync('qa/node_modules/@playwright/test/package.json')).version).toBe(manifest.playwright);
  for(const [file,hash] of Object.entries(manifest.hashes)) expect(createHash('sha256').update(readFileSync(`qa/visual/baselines/${file}`)).digest('hex'),file).toBe(hash);
});
async function ready(page) {
  await page.addInitScript(()=>localStorage.setItem('rollsbar_cookie_notice','1'));
  await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
  await page.goto(`http://127.0.0.1:4178/${baseline?'approved/demo.html':'current/'}`);
  const doc=baseline?page.frameLocator('#stage').frameLocator('#site'):page;
  await expect(doc.locator(baseline?'body[data-final-demo-fixes="1"]':'.rollsbar-product-grid').first()).toBeVisible();
  await doc.locator('body').evaluate(async body=>{
    const d=body.ownerDocument;
    const style=d.createElement('style');style.textContent='*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}.product-detail-modal__backdrop,.client-modal__backdrop,.rollsbar-product-details__backdrop{background:#f3f4f5!important;backdrop-filter:none!important}';d.head.append(style);
    await d.fonts.ready;
    await Promise.all([...d.images].filter(i=>!i.loading||i.loading!=='lazy').map(i=>i.decode().catch(()=>{})));
  });
  await page.mouse.move(0,899);
  if(!baseline)await expect(doc.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();
  return doc;
}
async function capture(page,locator,name) {
  await locator.scrollIntoViewIfNeeded();
  await locator.evaluate(async (node,alignOrigin)=>{
    node.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});
    node.ownerDocument.activeElement?.blur();
    if(alignOrigin) {
      const rect=node.getBoundingClientRect();
      node.style.position='relative';
      node.style.left=`${Math.round(rect.x)-rect.x}px`;
      node.style.top=`${Math.round(rect.y)-rect.y}px`;
    }
    await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
  },name.includes('media')||name.includes('title'));
  await page.mouse.move(0,899);
  const choiceCaps={1440:34,1051:22,1050:34,1024:34,701:22,700:34,390:34,320:0};
  const narrowCounter=page.viewportSize().width===320&&['b11-simple-counter','b11-simple-repeat'].includes(name);
  await expect(locator).toHaveScreenshot(name+'.png',name==='details'?{maxDiffPixels:20}:name==='selector-heading'?{maxDiffPixels:1}:name==='selector-choices'?{maxDiffPixels:choiceCaps[page.viewportSize().width]}:narrowCounter?{maxDiffPixels:38}:{});
}
const targets=[
 ['header','.topbar','.rollsbar-header'],
 ['categories','.category-nav','.rollsbar-category-nav'],
 ['promo','.client-promo-wrap','.rollsbar-utilities'],
 ['catalog-shell','#rolls .section-heading','#rolls .rollsbar-section-heading'],
 ['ordinary-media','[data-original-add="rolls-filadelfiya-s-krevetkoy"]','rolls-filadelfiya-s-krevetkoy'],
 ['ordinary-title','[data-original-add="rolls-filadelfiya-s-krevetkoy"]','rolls-filadelfiya-s-krevetkoy'],
 ['variable-media','[data-original-add="snacks-naggetsy"]','snacks-naggetsy'],
 ['variable-title','[data-original-add="snacks-naggetsy"]','snacks-naggetsy']
];
for(const [name,approved,current] of targets) test(name,async({page})=>{
 const doc=await ready(page);
 let target,card;
 if(name.includes('media')||name.includes('title')) {
   card=baseline?doc.locator(approved).first().locator('xpath=ancestor::article'):doc.locator(`[data-rollsbar-source-id="${current}"]`).first();
   target=card.locator(name.endsWith('media')?(baseline?'.product-card__visual':'.rollsbar-product-card__media'):'h3');
 } else target=doc.locator(baseline?approved:current).first();
 await capture(page,target,name);
 if(name==='ordinary-media') {
   const shell=await card.boundingBox(),media=await target.boundingBox();
   await expect(page).toHaveScreenshot('card-shell.png',{clip:{x:shell.x,y:shell.y,width:shell.width,height:media.y+media.height-shell.y}});
 }
});
test('details',async({page})=>{
 const doc=await ready(page);
 const id='tyahan-chicken';
 if(baseline) await doc.locator(`[data-original-add="${id}"]`).first().locator('xpath=ancestor::article').locator('h3').click();
 else await doc.locator(`[data-rollsbar-source-id="${id}"]`).first().locator('h3 a').click();
 await capture(page,doc.locator(baseline?'.product-detail-modal__panel':'.rollsbar-product-details__panel'),'details');
});
test('selector',async({page})=>{
 const doc=await ready(page);
 const id='snacks-naggetsy';
 await doc.locator(baseline?`[data-client-choose="${id}"]`:`[data-rollsbar-source-id="${id}"] [data-rollsbar-selection-open]`).first().click();
 const choices=doc.locator(baseline?'#clientProductOptions':'.rollsbar-product-options__groups');
 const optionText=await choices.locator('option').allTextContents();
 expect(optionText.map(s=>s.replace(/\s+/g,' ').trim())).toEqual(['6 шт — 150 ₽','10 шт — 200 ₽']);
 expect(await choices.locator('select').evaluate(s=>s.selectedIndex)).toBe(0);
 if(!baseline) await expect(doc.locator('.rollsbar-product-options__add')).toBeEnabled();
 // Preserve the accepted heading/choices assertions independently of B11's CTA.
 await capture(page,doc.locator(baseline?'.client-modal__head':'.rollsbar-product-options__head'),'selector-heading');
 await capture(page,choices,'selector-choices');
});

test('b11 simple actions',async({page})=>{
 const doc=await ready(page),id='rolls-filadelfiya-s-krevetkoy';
 const control=()=>doc.locator(baseline?`[data-client-control="${id}"]`:`[data-rollsbar-source-id="${id}"] .rollsbar-product-control,[data-rollsbar-source-id="${id}"] .rollsbar-product-counter`).first();
 await capture(page,control().locator('button'),'b11-simple-add');
 await control().locator('button').click();
 await expect(control().locator('span')).toHaveText('1');
 await capture(page,control().locator(baseline?'.client-counter':':scope'),'b11-simple-counter');
 await control().locator('button').last().click();
 await expect(control().locator('span')).toHaveText('2');
 await capture(page,control().locator(baseline?'.client-counter':':scope'),'b11-simple-repeat');
});

test('b11 selector actions',async({page})=>{
 const doc=await ready(page),id='snacks-naggetsy';
 const choose=doc.locator(baseline?`[data-client-choose="${id}"]`:`[data-rollsbar-source-id="${id}"] [data-rollsbar-selection-open]`).first();
 await capture(page,choose,'b11-variable-action');
 await choose.click();
 const add=doc.locator(baseline?'#clientProductAdd':'.rollsbar-product-options__add');
 await expect(add).toBeEnabled();
 await capture(page,add,'b11-selector-enabled');
 await add.click();
 await expect(doc.locator(baseline?'.client-modal': '#rollsbarProductDetails')).not.toBeVisible();
 await capture(page,choose,'b11-selector-post-add');
});

test('b11 geometry and preservation',async({page},info)=>{
 test.skip(baseline,'Current functional geometry; expected images are generated only by the visual tests.');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='warning'||(m.type()==='error'&&!m.text().startsWith('Failed to load resource:')))errors.push(m.text());});
 const doc=await ready(page);
 const ids=await doc.locator('.rollsbar-product-card').evaluateAll(cards=>cards.map(c=>c.dataset.rollsbarSourceId));
 expect(ids).toHaveLength(126);expect(new Set(ids).size).toBe(118);
 const hits=['rolls-filadelfiya','rolls-kaliforniya-klassicheskaya','pizza-pepperoni','sets-filadelfiya-set','sets-hit-set','baked-zapechennye-roll-s-lososem','shrimp-tempura','soups-tom-yam'];
 expect(await doc.locator('#hits .rollsbar-product-card').evaluateAll(cards=>cards.map(c=>c.dataset.rollsbarSourceId))).toEqual(hits);
 const measure=()=>doc.locator('body').evaluate(body=>{
  const overflow=(child,parent)=>{const c=child.getBoundingClientRect(),p=parent.getBoundingClientRect();return Math.max(0,c.right-p.right,p.left-c.left);};
  const actions=[...body.querySelectorAll('.rollsbar-product-card .rollsbar-product-action,.rollsbar-product-counter')];
  return {page:Math.max(0,body.ownerDocument.documentElement.scrollWidth-innerWidth),action:Math.max(0,...actions.map(a=>overflow(a,a.closest('article'))))};
 });
 expect(await measure()).toEqual({page:0,action:0});
 const card=doc.locator('[data-rollsbar-source-id="rolls-filadelfiya-s-krevetkoy"]').first();
 await card.locator('button').focus();await page.keyboard.press('Enter');
 await expect(card.locator('.rollsbar-product-counter span')).toHaveText('1');
 await expect(card.locator('[data-rollsbar-cart-delta="1"]')).toBeFocused();
 expect(await measure()).toEqual({page:0,action:0});
 await card.locator('[data-rollsbar-cart-delta="-1"]').click();
 await expect(card.locator('.rollsbar-product-control button')).toBeVisible();
 await card.locator('h3 a').click();
 const modal=doc.locator('#rollsbarProductDetails');
 await expect(modal).toBeVisible();await expect(doc.locator('body')).toHaveCSS('overflow','hidden');
 await page.keyboard.press('Escape');await expect(modal).not.toBeVisible();
 await expect(card.locator('h3 a')).toBeFocused();
 const products=JSON.parse(await doc.locator('#rollsbarProductDetailsData').textContent());
 let selectorOverflow=0;
 for(const [id,p] of Object.entries(products).filter(([,p])=>p.selection.required)){
  const choose=doc.locator(`[data-rollsbar-source-id="${id}"] [data-rollsbar-selection-open]`).first();
  await choose.click();
  selectorOverflow=Math.max(selectorOverflow,await modal.evaluate(m=>{const p=m.querySelector('.rollsbar-product-details__panel').getBoundingClientRect();return Math.max(0,...[...m.querySelectorAll('select,.rollsbar-product-options__add')].map(c=>{const r=c.getBoundingClientRect();return Math.max(0,r.right-p.right,p.left-r.left);}));}));
  await page.keyboard.press('Escape');await expect(choose).toBeFocused();
 }
 expect(selectorOverflow).toBe(0);expect(errors).toEqual([]);
 await info.attach('overflow.json',{body:JSON.stringify({width:page.viewportSize().width,...await measure(),selector:selectorOverflow,jsErrors:errors}),contentType:'application/json'});
});

test('b11 exhaustive cart choices and duplicates',async({page})=>{
 test.skip(baseline||![1440,320].includes(page.viewportSize().width),'Exhaustive mutations on desktop and narrow mobile; geometry runs at all widths.');
 test.setTimeout(120000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='warning'||(m.type()==='error'&&!m.text().startsWith('Failed to load resource:')))errors.push(m.text());});
 const payloads=[];page.on('request',r=>{if(r.url().endsWith('/fixture-cart'))payloads.push(JSON.parse(new URLSearchParams(r.postData()).get('request')));});
 const doc=await ready(page),modal=doc.locator('#rollsbarProductDetails');
 const products=JSON.parse(await doc.locator('#rollsbarProductDetailsData').textContent());
 const read=()=>page.evaluate(async()=>{const r=await fetch('/fixture-cart',{method:'POST',body:new URLSearchParams({nonce:'local-fixture',request:JSON.stringify({operation:'read'})})});return r.json();});
 let variations=0,options=0,parents=0;
 for(const [id,p] of Object.entries(products).filter(([,p])=>p.selection.required)){
  const choices=p.variable?p.selection.variations:p.selection.options[0].choices;
  if(p.variable)parents++;
  for(const choice of choices){
   await doc.locator(`[data-rollsbar-source-id="${id}"] [data-rollsbar-selection-open]`).first().click();
   const control=modal.locator('select');
   await control.selectOption(String(p.variable?choice.id:choice));
   const state=JSON.parse(await modal.getAttribute('data-selection'));expect(state.valid).toBe(true);
   if(p.variable){expect(state.variation_id).toBe(choice.id);variations++;}else{expect(state.options[0].value).toBe(choice);options++;}
   await modal.locator('.rollsbar-product-options__add').click();await expect(modal).not.toBeVisible();
  }
  const result=await read();expect(result.data.counts[id]).toBe(choices.length);
 }
 expect({parents,variations,options}).toEqual({parents:13,variations:26,options:21});
 expect(payloads.filter(r=>r.operation==='add')).toHaveLength(47);
 for(const id of ['rolls-filadelfiya','rolls-kaliforniya-klassicheskaya','pizza-pepperoni','sets-filadelfiya-set','sets-hit-set','baked-zapechennye-roll-s-lososem','shrimp-tempura','soups-tom-yam']){
  const cards=doc.locator(`[data-rollsbar-source-id="${id}"]`);expect(await cards.count()).toBe(2);
  const p=products[id];
  if(!p.selection.required){
   await cards.first().locator('[data-rollsbar-cart-delta="1"]').click();
   for(const c of await cards.all())await expect(c.locator('.rollsbar-product-counter span')).toHaveText('1');
   await cards.last().locator('[data-rollsbar-cart-delta="1"]').click();
   for(const c of await cards.all())await expect(c.locator('.rollsbar-product-counter span')).toHaveText('2');
   await cards.first().locator('[data-rollsbar-cart-delta="-1"]').click();
   await expect(cards.last().locator('.rollsbar-product-counter span')).toHaveText('1');
   await cards.last().locator('[data-rollsbar-cart-delta="-1"]').click();
   for(const c of await cards.all())await expect(c.locator('.rollsbar-product-control button')).toBeVisible();
  }else{
   for(const c of await cards.all()){
    await c.locator('[data-rollsbar-selection-open]').click();expect(await modal.getAttribute('data-source-id')).toBe(id);
    expect(JSON.parse(await modal.getAttribute('data-selection')).source_id).toBe(id);
    await modal.locator('.rollsbar-product-options__add').click();await expect(modal).not.toBeVisible();
   }
  }
 }
 const id='snacks-naggetsy',choose=doc.locator(`[data-rollsbar-source-id="${id}"] [data-rollsbar-selection-open]`).first();
 await choose.click();await modal.locator('select').evaluate(s=>{s.value='invalid';s.dispatchEvent(new Event('change',{bubbles:true}));});
 await expect(modal.locator('.rollsbar-product-options__add')).toBeDisabled();
 await page.keyboard.press('Escape');await choose.click();expect(await modal.locator('select').evaluate(s=>s.selectedIndex)).toBe(0);
 await page.keyboard.press('Tab');await page.keyboard.press('Tab');await page.keyboard.press('Tab');
 expect(await modal.evaluate(m=>m.contains(m.ownerDocument.activeElement))).toBe(true);
 await page.keyboard.press('Escape');
 // Real server rejection: selected choice belongs to another parent; counts cannot change.
 const before=(await read()).data.counts;
 const rejected=await page.evaluate(async request=>{const r=await fetch('/fixture-cart',{method:'POST',body:new URLSearchParams({nonce:'local-fixture',request:JSON.stringify(request)})});return r.json();},{operation:'add',source_id:id,product_id:products[id].woo_id,variation_id:products['pizza-pepperoni'].selection.variations[0].id});
 expect(rejected.success).toBe(false);expect(rejected.data.counts).toEqual(before);
 // UI failure and recovery must leave the selector open and actionable.
 await choose.click();await page.route('**/fixture-cart',async route=>{const r=JSON.parse(new URLSearchParams(route.request().postData()).get('request'));if(r.operation==='add')await route.fulfill({json:{success:false,data:{counts:before,message:'Товар недоступен.'}}});else await route.continue();});
 await modal.locator('.rollsbar-product-options__add').click();await expect(modal.locator('.rollsbar-cart-error')).toHaveText('Товар недоступен.');await expect(modal.locator('.rollsbar-product-options__add')).toBeEnabled();
 await page.unroute('**/fixture-cart');await modal.locator('.rollsbar-product-options__add').click();await expect(modal).not.toBeVisible();
 const simple=doc.locator('[data-rollsbar-source-id="rolls-filadelfiya-s-krevetkoy"]').first();
 await simple.locator('h3 a').click();await modal.locator('.rollsbar-product-details__add').click();await expect(modal).not.toBeVisible();
 await expect(simple.locator('.rollsbar-product-counter span')).toHaveText('1');
 await simple.locator('h3 a').click();await modal.locator('.rollsbar-product-details__close').click();await expect(simple.locator('h3 a')).toBeFocused();
 await simple.locator('h3 a').click();await modal.locator('.rollsbar-product-details__backdrop').click({position:{x:1,y:1},force:true});await expect(modal).not.toBeVisible();
 // Two simultaneous activations are guarded while the native cart request is in flight.
 await simple.locator('[data-rollsbar-cart-delta="1"]').evaluate(b=>{b.click();b.click();});await expect(simple.locator('.rollsbar-product-counter span')).toHaveText('2');
 expect(errors).toEqual([]);
});

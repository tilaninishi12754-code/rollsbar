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
  await page.addInitScript(()=>{try{localStorage.setItem('rollsbar_cookie_notice','1');}catch{/* Initial opaque iframe documents have no storage. */}});
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

// B12: expected pixels are captured only from the immutable approved iframe chain.
const drawerSelectors={panel:'.rollsbar-cart-drawer__panel',line:'.rollsbar-cart-item',qty:'.rollsbar-drawer-qty',body:'.rollsbar-drawer-body'};
async function drawerOpen(doc) {
 await doc.locator('body').evaluate(async b=>{const w=b.ownerDocument.defaultView;b.ownerDocument.documentElement.style.scrollBehavior='auto';w.scrollTo(0,0);await new Promise(r=>w.requestAnimationFrame(()=>w.requestAnimationFrame(r)));});
 await doc.locator(baseline?'[data-cart-open]':'.rollsbar-cart-link').first().evaluate(b=>b.click());
 await expect(doc.locator(baseline?'#cartDrawer': '#rollsbarCartDrawer')).toBeVisible();
 if(!baseline)await expect(doc.locator(drawerSelectors.panel)).toHaveAttribute('aria-busy','false');
}
async function drawerAdd(doc,id,choice=0){
 const line=doc.locator(baseline?'.cart-item':drawerSelectors.line),before=await line.count();
 const choose=doc.locator(baseline?`[data-client-choose="${id}"]`:`[data-rollsbar-source-id="${id}"] [data-rollsbar-selection-open]`).first();
 if(await choose.count()){
  await choose.click();
  const modal=doc.locator(baseline?'.client-modal':'#rollsbarProductDetails');
  await modal.locator('select').first().selectOption({index:choice});
  await modal.locator(baseline?'#clientProductAdd':'.rollsbar-product-options__add').click();
  await expect(modal).not.toBeVisible();
 }else{
  await doc.locator(baseline?`[data-original-add="${id}"]`:`[data-rollsbar-source-id="${id}"] [data-rollsbar-cart-delta="1"]`).first().evaluate(b=>b.click());
 }
 await expect(line).toHaveCount(before+1);
}
test('b12 drawer approved states',async({page})=>{
 test.setTimeout(90000);
 const doc=await ready(page),panel=doc.locator(baseline?'.cart-drawer__panel':drawerSelectors.panel);
 const close=()=>doc.locator(baseline?'.drawer-head [data-cart-close]':'.rollsbar-drawer-close').click();
 const shot=async name=>{await panel.evaluate(p=>p.ownerDocument.activeElement?.blur());await page.mouse.move(0,899);await expect(panel).toHaveScreenshot(`b12-${name}.png`);};
 await drawerOpen(doc);await shot('empty');await close();
 await drawerAdd(doc,'tyahan-chicken');await drawerOpen(doc);await shot('simple');
 await doc.locator(baseline?'.cart-item [data-plus]':'.rollsbar-cart-item [data-drawer-action="line_plus"]').click();
 await expect(doc.locator(baseline?'.cart-item .qty span':'.rollsbar-drawer-qty span')).toHaveText('2');
 await shot('quantity');await close();
 await drawerAdd(doc,'pizza-pepperoni',1);await drawerOpen(doc);await shot('variable');await close();
 await drawerAdd(doc,'wok-udon-chicken',2);await drawerOpen(doc);await shot('wok-option');await close();
 // Immutable approved shrimp options are pending; cover confirmed shrimp choices functionally.
 await drawerAdd(doc,'wok-soba-chicken',1);await drawerOpen(doc);await shot('multi-options');
 await doc.locator(baseline?'[data-mode="pickup"]':'[data-drawer-mode="pickup"]').click();
 await expect(doc.locator(baseline?'#cartTotals':'.rollsbar-cart-totals')).toContainText('Самовывоз');
 await shot('pickup');
 await doc.locator(baseline?'[data-upsell="u-soy"]':'[data-drawer-upsell="upsell-soy-sauce"]').click();
 await expect(doc.locator(baseline?'.cart-item':drawerSelectors.line)).toHaveCount(5);
 await shot('upsell');await close();
 for(const id of ['rolls-filadelfiya','rolls-kaliforniya-klassicheskaya','sets-filadelfiya-set','baked-zapechennye-roll-s-lososem','soups-tom-yam','tyahan-sea'])await drawerAdd(doc,id);
 await drawerOpen(doc);const body=doc.locator(baseline?'.drawer-body':drawerSelectors.body);
 await body.evaluate(b=>b.scrollTop=0);await shot('long-top');
 await body.evaluate(b=>b.scrollTop=b.scrollHeight);await shot('long-bottom');
});

test('b12 geometry focus and empty lifecycle',async({page},info)=>{
 test.skip(baseline,'Current functional QA only.');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='warning'||(m.type()==='error'&&!m.text().startsWith('Failed to load resource:')))errors.push(m.text());});
 const doc=await ready(page),drawer=doc.locator('#rollsbarCartDrawer'),panel=doc.locator(drawerSelectors.panel);
 const trigger=doc.locator(page.viewportSize().width<=900?'[data-rollsbar-mobile-cart]':'.rollsbar-cart-link').first();
 await expect(trigger).toBeVisible();
 await doc.locator('body').evaluate(()=>{document.documentElement.style.scrollBehavior='auto';scrollTo(0,600);});
 const y=await page.evaluate(()=>scrollY);
 await trigger.focus();await page.keyboard.press('Enter');await expect(drawer).toBeVisible();
 await expect(doc.locator('.rollsbar-drawer-close')).toBeFocused();
 await expect(doc.locator('.rollsbar-cart-empty')).toHaveText('Корзина пока пустая. Добавьте блюда из меню.');
 await expect(doc.locator('body')).toHaveCSS('overflow','hidden');
 await expect(doc.locator('.rollsbar-drawer-checkout')).toHaveAttribute('aria-disabled','true');
 await page.keyboard.press('Shift+Tab');await expect(doc.locator('.rollsbar-drawer-checkout')).toBeFocused();
 await page.keyboard.press('Tab');await expect(doc.locator('.rollsbar-drawer-close')).toBeFocused();
 const metrics=await panel.evaluate(p=>{
  const b=p.querySelector('.rollsbar-drawer-body'),r=p.getBoundingClientRect();
  return {page:Math.max(0,document.documentElement.scrollWidth-innerWidth),drawer:Math.max(0,p.scrollWidth-p.clientWidth),content:Math.max(0,b.scrollWidth-b.clientWidth),width:r.width,right:r.right,backdrop:getComputedStyle(document.querySelector('.rollsbar-cart-drawer__backdrop')).backgroundColor,blur:getComputedStyle(document.querySelector('.rollsbar-cart-drawer__backdrop')).backdropFilter};
 });
 expect(metrics).toEqual({page:0,drawer:0,content:0,width:Math.min(470,page.viewportSize().width),right:page.viewportSize().width,backdrop:'rgba(0, 0, 0, 0.46)',blur:'blur(4px)'});
 await page.keyboard.press('Escape');await expect(drawer).not.toBeVisible();await expect(trigger).toBeFocused();
 expect(await page.evaluate(()=>scrollY)).toBe(y);await expect(doc.locator('body')).not.toHaveCSS('overflow','hidden');
 await trigger.click();await doc.locator('.rollsbar-drawer-close').click();await expect(trigger).toBeFocused();
 await trigger.click();
 if(page.viewportSize().width>470)await doc.locator('.rollsbar-cart-drawer__backdrop').click({position:{x:1,y:1}});
 else await page.keyboard.press('Escape'); // Full-width approved mobile panel covers the backdrop.
 await expect(drawer).not.toBeVisible();
 expect(await doc.locator('[inert]').count()).toBe(0);expect(errors).toEqual([]);
 await info.attach('b12-overflow.json',{body:JSON.stringify({viewport:page.viewportSize().width,...metrics,jsErrors:errors}),contentType:'application/json'});
});

test('b12 canonical drawer mutations and recovery',async({page},info)=>{
 test.skip(baseline||![1440,320].includes(page.viewportSize().width),'Shared mutation path at desktop/narrow mobile; data exhaustive in PHP and B11.');
 test.setTimeout(120000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='warning'||(m.type()==='error'&&!m.text().startsWith('Failed to load resource:')))errors.push(m.text());});
 const doc=await ready(page),drawer=doc.locator('#rollsbarCartDrawer'),modal=doc.locator('#rollsbarProductDetails');
 const request=async r=>page.evaluate(async request=>{const response=await fetch('/fixture-cart',{method:'POST',body:new URLSearchParams({nonce:'local-fixture',request:JSON.stringify(request)})});return response.json();},r);
 const close=()=>doc.locator('.rollsbar-drawer-close').click();
 const row=id=>doc.locator(`.rollsbar-cart-item[data-source-id="${id}"]`);
 const id='rolls-filadelfiya',cards=doc.locator(`[data-rollsbar-source-id="${id}"]`);
 await cards.first().locator('[data-rollsbar-cart-delta="1"]').click();await expect(cards.last().locator('.rollsbar-product-counter span')).toHaveText('1');
 await drawerOpen(doc);await expect(row(id).locator('.rollsbar-drawer-qty span')).toHaveText('1');
 await row(id).locator('[data-drawer-action="line_plus"]').focus();await page.keyboard.press('Enter');
 await expect(row(id).locator('.rollsbar-drawer-qty span')).toHaveText('2');await expect(row(id).locator('[data-drawer-action="line_plus"]')).toBeFocused();
 for(const card of await cards.all())await expect(card.locator('.rollsbar-product-counter span')).toHaveText('2');
 await row(id).locator('[data-drawer-action="line_minus"]').click();await expect(row(id).locator('.rollsbar-drawer-qty span')).toHaveText('1');
 await row(id).locator('[data-drawer-action="line_minus"]').click();await expect(row(id)).toHaveCount(0);await expect(doc.locator('.rollsbar-cart-empty')).toBeVisible();await expect(doc.locator('.rollsbar-drawer-close')).toBeFocused();
 for(const card of await cards.all())await expect(card.locator('[data-rollsbar-cart-delta="1"]')).toBeVisible();
 await close();
 // Same parent with two native variations, and same product with incompatible options.
 await drawerAdd(doc,'pizza-pepperoni',0);await drawerAdd(doc,'pizza-pepperoni',1);
 await drawerAdd(doc,'wok-udon-chicken',0);await drawerAdd(doc,'wok-udon-chicken',2);
 await drawerAdd(doc,'shrimp-tempura',1);await drawerAdd(doc,'snacks-naggetsy',0);
 await drawerOpen(doc);await expect(row('pizza-pepperoni')).toHaveCount(2);await expect(row('wok-udon-chicken')).toHaveCount(2);
 const state=(await request({operation:'read'})).data;
 for(const item of state.lines){const line=doc.locator(`[data-cart-key="${item.key}"]`);await expect(line.locator('h4')).toHaveText(item.name);await expect(line.locator('small')).toHaveText(item.unit_price);}
 expect(state.lines.filter(l=>l.source_id==='pizza-pepperoni').map(l=>l.variation_id)[0]).not.toBe(state.lines.filter(l=>l.source_id==='pizza-pepperoni')[1].variation_id);
 await row('wok-udon-chicken').first().locator('[data-drawer-action="line_plus"]').click();
 await expect(row('wok-udon-chicken').first().locator('.rollsbar-drawer-qty span')).toHaveText('2');await expect(row('wok-udon-chicken').last().locator('.rollsbar-drawer-qty span')).toHaveText('1');
 await row('pizza-pepperoni').first().locator('[data-drawer-action="line_remove"]').click();await expect(row('pizza-pepperoni')).toHaveCount(1);
 for(const sourceId of ['upsell-soy-sauce','upsell-ginger','upsell-wasabi']){await doc.locator(`[data-drawer-upsell="${sourceId}"]`).click();await expect(row(sourceId)).toHaveCount(1);}
 expect(await doc.locator('.rollsbar-product-card').count()).toBe(126);
 const subtotal=(await request({operation:'read'})).data.subtotal;for(const value of await doc.locator('[data-rollsbar-drawer-subtotal]').all())await expect(value).toHaveText(subtotal);
 await doc.locator('[data-drawer-mode="pickup"]').click();await expect(doc.locator('[data-drawer-mode="pickup"]')).toHaveAttribute('aria-pressed','true');await close();await drawerOpen(doc);await expect(doc.locator('[data-drawer-mode="pickup"]')).toHaveAttribute('aria-pressed','true');
 // A lost response after a successful mutation is reconciled, never retried.
 let lost=false;await page.route('**/fixture-cart',async route=>{const r=JSON.parse(new URLSearchParams(route.request().postData()).get('request'));if(!lost&&r.operation==='line_plus'){lost=true;await route.fetch();await route.abort();}else await route.continue();});
 const before=Number(await row('shrimp-tempura').locator('.rollsbar-drawer-qty span').textContent());
 await row('shrimp-tempura').locator('[data-drawer-action="line_plus"]').click();await expect(doc.locator('.rollsbar-drawer-error')).not.toBeEmpty();await expect(row('shrimp-tempura').locator('.rollsbar-drawer-qty span')).toHaveText(String(before+1));await page.unroute('**/fixture-cart');
 await row('shrimp-tempura').locator('[data-drawer-action="line_plus"]').click();await expect(row('shrimp-tempura').locator('.rollsbar-drawer-qty span')).toHaveText(String(before+2));await expect(doc.locator('.rollsbar-drawer-error')).toBeEmpty();
 await close();
 // Real B9 fallback stays confined, and transitioning from a selector cannot retain its lock.
 await doc.locator('[data-rollsbar-source-id="snacks-naggetsy"] [data-rollsbar-selection-open]').first().click();await expect(modal).toBeVisible();
 await doc.locator('.rollsbar-cart-link').first().evaluate(b=>b.click());await expect(drawer).toBeVisible();await expect(modal).not.toBeVisible();
 const overflow=await drawer.evaluate(d=>{const p=d.querySelector('.rollsbar-cart-drawer__panel'),b=d.querySelector('.rollsbar-drawer-body');return {page:Math.max(0,document.documentElement.scrollWidth-innerWidth),drawer:Math.max(0,p.scrollWidth-p.clientWidth),content:Math.max(0,b.scrollWidth-b.clientWidth)};});expect(overflow).toEqual({page:0,drawer:0,content:0});
 await close();
 const data=JSON.parse(await doc.locator('#rollsbarProductDetailsData').textContent());
 for(const p of Object.values(data).filter(p=>!p.selection.required).slice(0,12))await request({operation:'add',source_id:p.source_id||Object.keys(data).find(key=>data[key].woo_id===p.woo_id),product_id:p.woo_id});
 await drawerOpen(doc);const body=doc.locator('.rollsbar-drawer-body');expect(await body.evaluate(b=>b.scrollHeight>b.clientHeight)).toBe(true);await body.evaluate(b=>b.scrollTop=b.scrollHeight);expect(await body.evaluate(b=>b.scrollTop)).toBeGreaterThan(0);
 await expect(doc.locator('.rollsbar-drawer-checkout')).toHaveAttribute('href','/checkout/');
 // Keep checkout native: intercept only the existing checkout navigation boundary.
 await page.route('**/checkout/',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><title>Native checkout boundary</title>'}));
 const current=(await request({operation:'read'})).data;for(const item of current.lines)await request({operation:'line_remove',key:item.key});await close();await drawerOpen(doc);await expect(doc.locator('.rollsbar-cart-empty')).toBeVisible();await expect(doc.locator('.rollsbar-cart-item')).toHaveCount(0);
 await close();await expect(doc.locator('body')).not.toHaveCSS('overflow','hidden');expect(await doc.locator('[inert]').count()).toBe(0);expect(errors).toEqual([]);
 await info.attach('b12-functional.json',{body:JSON.stringify({width:page.viewportSize().width,overflow,jsErrors:errors,distinctVariations:true,distinctOptions:true,lostResponseReconciled:true,hiddenUpsells:3}),contentType:'application/json'});
 await drawerOpen(doc);await doc.locator('[data-drawer-upsell="upsell-ginger"]').click();await expect(row('upsell-ginger')).toHaveCount(1);
 await doc.locator('.rollsbar-drawer-checkout').click();await expect(page).toHaveURL('http://127.0.0.1:4178/checkout/');expect(errors).toEqual([]);
});

// B13: capture only immutable approved cart controls, using the existing B12 actions.
async function b13State(doc,count){
 await expect(doc.locator(baseline?'.cart-count':'.rollsbar-cart-count').first()).toHaveText(String(count));
 if(!baseline)await expect(doc.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();
 await doc.locator('body').evaluate(async b=>{b.ownerDocument.defaultView.scrollTo(0,0);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});
}
test('b13 approved header and mobile totals',async({page},info)=>{
 test.setTimeout(90000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='warning'||(m.type()==='error'&&!m.text().startsWith('Failed to load resource:')))errors.push(m.text());});
 const doc=await ready(page),width=page.viewportSize().width;
 const header=doc.locator(baseline?'.cart-button':'.rollsbar-cart-link').first();
 const bar=doc.locator(baseline?'.client-order-bar':'[data-rollsbar-orderbar]');
 const empty=doc.locator(baseline?'.mobile-cart':'[data-rollsbar-mobile-cart]');
 const shot=async name=>{
  await doc.locator('body').evaluate(async b=>{b.ownerDocument.activeElement?.blur();b.ownerDocument.defaultView.scrollTo(0,0);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});
  if(width<=700){await expect(bar).toBeVisible();await expect(bar).toHaveScreenshot(`b13-${name}.png`);}
  else if(width>900){await expect(header).toBeVisible();await expect(header).toHaveScreenshot(`b13-${name}.png`);}
 };
 await b13State(doc,0);await expect(bar).not.toBeVisible();
 await expect(header).toBeVisible({visible:width>900});
 if(width<=700){
  await expect(empty).toBeVisible();
  // Isolate only the background outside the circular control from deferred page rows.
  await empty.evaluate(n=>{const r=n.getBoundingClientRect(),p=n.ownerDocument.createElement('div');p.id='b13-capture-backing';Object.assign(p.style,{position:'fixed',left:r.x+'px',top:r.y+'px',width:r.width+'px',height:r.height+'px',background:'#fff',zIndex:String(Number(getComputedStyle(n).zIndex)-1),pointerEvents:'none'});n.ownerDocument.body.append(p);});
  await expect(empty).toHaveScreenshot('b13-empty-mobile.png');
  await doc.locator('#b13-capture-backing').evaluate(n=>n.remove());
 }
 await drawerAdd(doc,'tyahan-chicken');await b13State(doc,1);await shot('one');
 const card=doc.locator(baseline?'[data-client-control="tyahan-chicken"]':'[data-rollsbar-source-id="tyahan-chicken"] .rollsbar-product-counter').first();
 await card.locator('button').last().click();await b13State(doc,2);await shot('quantity');
 await drawerAdd(doc,'pizza-pepperoni',1);await drawerAdd(doc,'wok-udon-chicken',2);await b13State(doc,4);await shot('selected');
 await expect(bar).toBeVisible({visible:width<=700});
 const metrics=await doc.locator('body').evaluate(b=>{
  const d=b.ownerDocument,w=d.defaultView,h=d.querySelector('.rollsbar-header,.topbar');
  const excess=n=>n&&n.getClientRects().length?Math.max(0,n.scrollWidth-n.clientWidth):0;
  return {page:Math.max(0,d.documentElement.scrollWidth-w.innerWidth),header:excess(h),mobile:excess(d.querySelector('[data-rollsbar-orderbar],.client-order-bar'))};
 });
 expect(metrics).toEqual({page:0,header:0,mobile:0});expect(errors).toEqual([]);
 if(!baseline){
  const trigger=width<=700?bar:width>900?header:empty;
  await trigger.focus();await page.keyboard.press('Enter');await expect(doc.locator('#rollsbarCartDrawer')).toBeVisible();await expect(bar).not.toBeVisible();
  await page.keyboard.press('Escape');await expect(trigger).toBeFocused();await expect(doc.locator('[inert]')).toHaveCount(0);
  await info.attach('b13-geometry.json',{body:JSON.stringify({width,...metrics,jsErrors:errors}),contentType:'application/json'});
 }
});

test('b13 canonical synchronization and transitions',async({page},info)=>{
 test.skip(baseline||![1440,320].includes(page.viewportSize().width),'Shared snapshot rendering; geometry and approved states covered at all eight widths.');
 test.setTimeout(120000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='warning'||(m.type()==='error'&&!m.text().startsWith('Failed to load resource:')))errors.push(m.text());});
 const doc=await ready(page),bar=doc.locator('[data-rollsbar-orderbar]');
 const check=async()=>{
  await expect(doc.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();
  const state=await page.evaluate(async()=>{const r=await fetch('/fixture-cart',{method:'POST',body:new URLSearchParams({nonce:'local-fixture',request:JSON.stringify({operation:'read'})})});return (await r.json()).data;});
  const count=state.lines.reduce((n,l)=>n+l.quantity,0);
  for(const badge of await doc.locator('.rollsbar-cart-count').all())await expect(badge).toHaveText(String(count));
  const total=state.subtotal.replace(/(\d)[ \u00a0\u202f](?=\d)/g,'$1\u00a0').replace(/\u00a0(?=₽)/g,' ');
  await expect(doc.locator('.rollsbar-header-cart-total')).toHaveText(total);
  await expect(doc.locator('[data-rollsbar-order-total]')).toHaveText(total);
  return state;
 };
 await check();
 const cards=doc.locator('[data-rollsbar-source-id="rolls-filadelfiya"]');
 await cards.first().locator('[data-rollsbar-cart-delta="1"]').click();await check();
 for(const c of await cards.all())await expect(c.locator('.rollsbar-product-counter span')).toHaveText('1');
 for(let n=2;n<=25;n++){await cards.last().locator('[data-rollsbar-cart-delta="1"]').click();await check();const word=n>=11&&n<=19?'товаров':n%10===1?'товар':n%10>=2&&n%10<=4?'товара':'товаров';await expect(doc.locator('[data-rollsbar-order-count]')).toHaveText(`${n} ${word}`);}
 await cards.first().locator('[data-rollsbar-cart-delta="-1"]').click();await check();
 await drawerAdd(doc,'pizza-pepperoni',1);await check();await drawerAdd(doc,'wok-udon-chicken',2);await check();await drawerAdd(doc,'shrimp-tempura',1);await check();
 await drawerOpen(doc);
 for(const action of ['line_plus','line_minus']){await doc.locator(`.rollsbar-cart-item [data-drawer-action="${action}"]`).first().click();await check();}
 await doc.locator('[data-drawer-upsell="upsell-soy-sauce"]').click();await check();
 await doc.locator('.rollsbar-drawer-close').click();
 for(const width of [1440,1051,1050,1024,701,700,390,320]){
  await page.setViewportSize({width,height:900});await check();
  await expect(bar).toBeVisible({visible:width<=700});
  const trigger=doc.locator(width<=700?'[data-rollsbar-orderbar]':width>900?'.rollsbar-cart-link':'[data-rollsbar-mobile-cart]');
  await trigger.click();await expect(doc.locator('#rollsbarCartDrawer')).toBeVisible();await expect(bar).not.toBeVisible();await page.keyboard.press('Escape');await expect(trigger).toBeFocused();
 }
 // Final removal while the opener disappears must return focus to the empty mobile control.
 await bar.click();
 while(await doc.locator('.rollsbar-cart-item').count()){await doc.locator('[data-drawer-action="line_remove"]').first().click();await check();}
 await expect(doc.locator('.rollsbar-cart-empty')).toBeVisible();await page.keyboard.press('Escape');await expect(bar).not.toBeVisible();await expect(doc.locator('[data-rollsbar-mobile-cart]')).toBeFocused();
 await expect(doc.locator('body')).not.toHaveCSS('overflow','hidden');await expect(doc.locator('[inert]')).toHaveCount(0);expect(errors).toEqual([]);
 await info.attach('b13-functional.json',{body:JSON.stringify({pass:true,jsErrors:errors,breakpoints:8,canonicalServerComparison:true}),contentType:'application/json'});
});

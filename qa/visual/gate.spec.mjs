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
  await expect(locator).toHaveScreenshot(name+'.png',name==='details'?{maxDiffPixels:20}:name==='selector-heading'?{maxDiffPixels:1}:name==='selector-choices'?{maxDiffPixels:choiceCaps[page.viewportSize().width]}:{});
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
 if(!baseline) await expect(doc.locator('.rollsbar-product-options__add')).toBeDisabled();
 // CTA is intentionally disabled in B10; capture equivalent heading and choices independently.
 await capture(page,doc.locator(baseline?'.client-modal__head':'.rollsbar-product-options__head'),'selector-heading');
 await capture(page,choices,'selector-choices');
});

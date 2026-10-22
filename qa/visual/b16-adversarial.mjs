// Independent post-gate sequence: long cart -> page bottom -> search/details -> drawer.
import {chromium,expect} from '../node_modules/@playwright/test/index.mjs';
import {startPreview} from './server.mjs';
import {writeFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const preview=await startPreview(),browser=await chromium.launch(),rows=[];
try{for(const width of [1440,1051,1050,1024,701,700,390,320]){
 const page=await browser.newPage({viewport:{width,height:900}}),errors=[];
 await page.addInitScript(()=>{try{localStorage.setItem('rollsbar_cookie_notice','1');}catch{}});
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='warning'||m.type()==='error'&&!m.text().startsWith('Failed to load resource:'))errors.push(m.text());});
 await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
 await page.goto('http://127.0.0.1:4178/current/');
 await expect(page.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();
 const seeded=await page.evaluate(async()=>{
  const products=JSON.parse(document.querySelector('#rollsbarProductDetailsData').textContent);
  for(const [id,p]of Object.entries(products).filter(([,p])=>!p.selection.required).slice(0,15))await fetch('/fixture-cart',{method:'POST',body:new URLSearchParams({nonce:'local-fixture',request:JSON.stringify({operation:'add',source_id:id,product_id:p.woo_id})})});
  return 15;
 });
 // Refresh fixture totals before opening UI.
 await page.reload();await expect(page.locator('.rollsbar-cart-count').first()).toHaveText(String(seeded));
 const drawer=page.locator('#rollsbarCartDrawer'),modal=page.locator('#rollsbarProductDetails');
 const trigger=page.locator(width<=700?'[data-rollsbar-orderbar]':width<=900?'[data-rollsbar-mobile-cart]':'.rollsbar-cart-link').first();
 await trigger.click();await expect(drawer.locator('.rollsbar-cart-item')).toHaveCount(seeded);
 await drawer.locator('.rollsbar-drawer-body').evaluate(n=>n.scrollTop=n.scrollHeight);
 await page.keyboard.press('Escape');
 await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
 const open=page.locator('[data-rollsbar-search-open]');await open.click();
 await page.locator('.product-search__input').fill('Тяхан');
 await page.locator('[data-search-product="tyahan-chicken"]').click();await expect(modal).toBeVisible();await page.keyboard.press('Escape');
 await trigger.click();await expect(drawer).toBeVisible();await page.keyboard.press('Escape');
 await open.click();await page.locator('.product-search__input').fill('неттакогоблюда999');await page.keyboard.press('Escape');await expect(open).toBeFocused();
 await expect(page.locator('[inert]')).toHaveCount(0);await expect(page.locator('body')).not.toHaveCSS('overflow','hidden');
 await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
 for(const link of await page.locator('.rollsbar-footer a').all()){
  await link.scrollIntoViewIfNeeded();
  assert(await link.evaluate(n=>{const r=n.getBoundingClientRect(),t=document.elementFromPoint((r.left+r.right)/2,(r.top+r.bottom)/2);return !!t&&(n===t||n.contains(t));}));
 }
 const duplicates=await page.evaluate(()=>{const ids=[...document.querySelectorAll('[id]')].map(n=>n.id);return ids.filter((id,i)=>ids.indexOf(id)!==i);});
 assert.deepEqual(duplicates,[]);assert.deepEqual(errors,[]);
 rows.push({width,status:'PASS',seeded,sequence:'long cart → footer → search/details → drawer → no-results Escape → footer',errors,duplicates});
 console.log(`B16 adversarial ${width}: PASS`);await page.close();
}writeFileSync('qa/visual/B16_ADVERSARIAL.json',JSON.stringify(rows,null,2)+'\n');
}finally{await browser.close();await preview.close();}

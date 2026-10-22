// Local-only populated-cart overflow proof; renders the real current theme/plugin.
import assert from 'node:assert/strict';
import { chromium } from '../node_modules/@playwright/test/index.mjs';
import { startPreview } from './server.mjs';
const preview=await startPreview(),browser=await chromium.launch();
const rows=[];
try {
 for(const width of [1440,1051,1050,1024,701,700,390,320]){
  const context=await browser.newContext({viewport:{width,height:900},deviceScaleFactor:1,locale:'ru-RU',timezoneId:'Europe/Moscow',reducedMotion:'reduce'});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>localStorage.setItem('rollsbar_cookie_notice','1'));
  await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
  await page.goto('http://127.0.0.1:4178/current/');
  await page.waitForFunction(()=>document.querySelector('[data-rollsbar-cart-delta]:not([disabled])'));
  await page.evaluate(async()=>{
   const products=JSON.parse(document.getElementById('rollsbarProductDetailsData').textContent);
   for(const [id,p] of Object.entries(products).filter(([,p])=>!p.selection.required).slice(0,15)){
    const response=await fetch('/fixture-cart',{method:'POST',body:new URLSearchParams({nonce:'local-fixture',request:JSON.stringify({operation:'add',source_id:id,product_id:p.woo_id})})});
    if(!(await response.json()).success)throw Error('Unable to seed canonical cart');
   }
  });
  await page.locator('[data-rollsbar-selection-open]').first().click();
  const selector=await page.locator('#rollsbarProductDetails').evaluate(m=>{
   const p=m.querySelector('.rollsbar-product-details__panel').getBoundingClientRect();
   return Math.max(0,...[...m.querySelectorAll('select,.rollsbar-product-options__add')].map(c=>{const r=c.getBoundingClientRect();return Math.max(0,r.right-p.right,p.left-r.left);}));
  });
  await page.keyboard.press('Escape');
  await page.locator('.rollsbar-cart-link').first().evaluate(b=>b.click());
  await page.waitForFunction(()=>document.querySelectorAll('.rollsbar-cart-item').length===15&&document.querySelector('.rollsbar-cart-drawer__panel').getAttribute('aria-busy')==='false');
  const metrics=await page.locator('.rollsbar-cart-drawer__panel').evaluate(p=>{
   const b=p.querySelector('.rollsbar-drawer-body');
   const action=Math.max(0,...[...document.querySelectorAll('.rollsbar-product-card .rollsbar-product-action,.rollsbar-product-counter')].map(a=>{const r=a.getBoundingClientRect(),c=a.closest('article').getBoundingClientRect();return Math.max(0,r.right-c.right,c.left-r.left);}));
   return {page:Math.max(0,document.documentElement.scrollWidth-innerWidth),drawer:Math.max(0,p.scrollWidth-p.clientWidth),content:Math.max(0,b.scrollWidth-b.clientWidth),action,verticalScroll:b.scrollHeight>b.clientHeight};
  });
  assert.deepEqual({...metrics,selector},{page:0,drawer:0,content:0,action:0,verticalScroll:true,selector:0});
  assert.deepEqual(errors,[]);
  await page.locator('.rollsbar-drawer-close').click();
  const controls=await page.evaluate(()=>{
   const excess=n=>n&&n.getClientRects().length?Math.max(0,n.scrollWidth-n.clientWidth,n.getBoundingClientRect().right-innerWidth,-n.getBoundingClientRect().left):0;
   return {header:excess(document.querySelector('.rollsbar-header')),mobile:excess(document.querySelector('[data-rollsbar-orderbar]'))};
  });
  assert.deepEqual(controls,{header:0,mobile:0});
  rows.push({width,...metrics,...controls,selector,jsErrors:errors});
  await context.close();
 }
 console.log(JSON.stringify({pass:true,rows},null,2));
} finally {await browser.close();await preview.close();}

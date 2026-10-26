import { chromium, expect } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { startPreview } from './server.mjs';
const live=process.env.ROLLSBAR_UX_BASE;
if(live&&new URL(live).origin!=='https://staging.rollsbar.ru')throw Error('Only staging authorized');
const out='qa/visual-results/'+(live?'storefront-ux-staging':'storefront-controls');mkdirSync(out,{recursive:true});
const report={status:'RUNNING',scope:'floating-controls-701-900',inherited_full_acceptance_sha:'2ad7e69c690b21bb33ff48c6c92119b01ea8a218',release_sha:process.env.ROLLSBAR_DEPLOY_SHA||'candidate',checks:[],screenshots:[]};
const server=live?null:await startPreview({port:4180}),browser=await chromium.launch();
try{
 for(const width of [701,900]){
  const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'}),page=await context.newPage();
  await page.addInitScript(()=>localStorage.setItem('rollsbar_cookie_notice','1'));
  if(!live)await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
  await page.goto(live?live+'/?ux-controls='+report.release_sha:'http://127.0.0.1:4180/current/',{waitUntil:'domcontentloaded'});
  await expect(page.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();
  await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});
  const states=[];
  for(const populated of [false,true]){
   if(populated)await page.locator('[data-rollsbar-cart-delta="1"]').first().click();
   await expect(page.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();
   await page.evaluate(()=>scrollTo(0,1000));await expect(page.locator('.client-back-top')).toBeVisible();
   const rects=await page.locator('.client-back-top,.rollsbar-mobile-cart').evaluateAll(ns=>ns.map(n=>({class:n.className,rect:n.getBoundingClientRect().toJSON()})));
   const back=rects.find(n=>n.class.includes('back-top')).rect,cart=rects.find(n=>n.class.includes('mobile-cart')).rect;
   expect(back.bottom).toBeLessThan(cart.top);expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBe(0);
   const path=out+'/controls-'+width+'-'+(populated?'populated':'empty')+'.png';await page.screenshot({path});report.screenshots.push(path);states.push({populated,rects});
   await page.locator('[data-rollsbar-mobile-cart]').click();await expect(page.locator('#rollsbarCartDrawer')).toBeVisible();await page.keyboard.press('Escape');
   await page.locator('.client-back-top').click();await page.waitForFunction(()=>scrollY<2);await expect(page.locator('.client-back-top')).toBeHidden();
  }
  await page.evaluate(async()=>{const c=window.rollsbarCart;async function req(request){return(await(await fetch(c.url,{method:'POST',body:new URLSearchParams({nonce:c.nonce,request:JSON.stringify(request)})})).json());}const result=await req({operation:'read'});for(const l of result.data.lines)await req({operation:'line_remove',key:l.key});});
  report.checks.push({width,height:900,status:'PASS',states});console.log(width,'controls PASS');await context.close();
 }
 report.status='PASS';
}catch(e){report.status='FAIL';report.error=e.stack;throw e;}
finally{writeFileSync(out+'/browser.json',JSON.stringify(report,null,2));await browser.close();await server?.close();}

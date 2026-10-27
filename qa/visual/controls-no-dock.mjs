import {chromium,expect} from '@playwright/test';
import {mkdirSync,writeFileSync} from 'node:fs';
import {startPreview} from './server.mjs';
const live=process.env.ROLLSBAR_UX_BASE;
if(live&&live!=='https://staging.rollsbar.ru')throw Error('Staging only');
const out='qa/visual-results/'+(live?'storefront-ux-staging':'controls-no-dock');mkdirSync(out,{recursive:true});
const report={status:'RUNNING',scope:'controls-no-dock',inherited_full_acceptance_sha:'529cbf3dc536b13dce40d74bbfbb8d054a9f2cfd',release_sha:process.env.ROLLSBAR_DEPLOY_SHA||'candidate',checks:[],screenshots:[]};
const server=live?null:await startPreview({port:4180}),browser=await chromium.launch();
try{for(const width of [320,390,701,900,1440]){
 const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce',locale:'ru-RU'}),page=await context.newPage();
 await page.addInitScript(()=>localStorage.setItem('rollsbar_cookie_notice','1'));
 if(!live)await context.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
 await page.goto(live?live+'/?no-dock='+report.release_sha:'http://127.0.0.1:4180/current/',{waitUntil:'load'});
 const ready=()=>expect(page.locator('[data-rollsbar-cart-delta]').first()).toBeEnabled();await ready();
 const cart=()=>page.locator(width>900?'.rollsbar-cart-link':width>700?'[data-rollsbar-mobile-cart]':'[data-rollsbar-orderbar]:not([hidden]),[data-rollsbar-mobile-cart]:not([hidden])').first();
 const back=page.locator('.client-back-top'),states=[];
 async function hit(loc){await expect(loc).toBeVisible();expect(await loc.evaluate(n=>{const r=n.getBoundingClientRect();return [0.2,0.5,0.8].every(x=>[0.2,0.5,0.8].every(y=>{const t=document.elementFromPoint(r.x+r.width*x,r.y+r.height*y);return t===n||n.contains(t)}))})).toBe(true)}
 for(const populated of [false,true]){
  if(populated){await page.locator('[data-rollsbar-cart-delta="1"]').first().click();await ready()}
  await page.evaluate(()=>scrollTo({top:1100,behavior:'instant'}));await expect(back).toBeVisible();
  await back.evaluate(n=>n.getAnimations().forEach(a=>a.finish()));
  expect(await page.locator('.rollsbar-controls-dock').evaluate(n=>getComputedStyle(n).display)).toBe('none');
  await hit(back);await hit(cart());if(width<=700)await hit(page.locator('.mobile-phone'));
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBe(0);
  const path=out+'/no-dock-'+width+'-'+populated+'.png';await page.screenshot({path});report.screenshots.push(path);
  await cart().click();await expect(page.locator('#rollsbarCartDrawer')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('#rollsbarCartDrawer')).toBeHidden();
  await back.click();await page.waitForFunction(()=>scrollY<2);states.push({populated,cartFirstTap:true,backFirstTap:true,noFullWidthShelf:true});
 }
 await page.evaluate(async()=>{const c=rollsbarCart,req=async request=>(await(await fetch(c.url,{method:'POST',body:new URLSearchParams({nonce:c.nonce,request:JSON.stringify(request)})})).json()).data;for(const l of (await req({operation:'read'})).lines)await req({operation:'line_remove',key:l.key});});
 report.checks.push({width,status:'PASS',states});console.log(width,'no-dock controls PASS');await context.close();
}report.status='PASS'}catch(e){report.status='FAIL';report.error=e.stack;throw e}finally{writeFileSync(out+'/browser.json',JSON.stringify(report,null,2));await browser.close();await server?.close()}

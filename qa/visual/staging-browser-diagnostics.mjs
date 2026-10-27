/** Staging-only browser evidence. Original test assertions/timeouts remain intact. */
import {chromium} from '@playwright/test';
import {mkdirSync,writeFileSync} from 'node:fs';
if(process.env.ROLLSBAR_UX_BASE!=='https://staging.rollsbar.ru')throw Error('Diagnostics require staging');
const out='qa/visual-results/storefront-ux-staging/diagnostics';mkdirSync(out,{recursive:true});
const launch=chromium.launch.bind(chromium);let serial=0;
chromium.launch=async(...args)=>{
 const browser=await launch(...args),newContext=browser.newContext.bind(browser),finishers=new Map();
 browser.newContext=async(...contextArgs)=>{
  const context=await newContext(...contextArgs),id=++serial,events=[],start=Date.now();
  await context.tracing.start({screenshots:true,snapshots:true,sources:true});
  const flush=()=>writeFileSync(out+'/context-'+id+'.json',JSON.stringify({release_sha:process.env.ROLLSBAR_DEPLOY_SHA,viewport:contextArgs[0]?.viewport,events},null,2));
  function record(kind,request,extra={}){if(!request.url().includes('wc-ajax=rollsbar_cart'))return;let operation;try{operation=JSON.parse(new URLSearchParams(request.postData()).get('request'))}catch{}events.push({kind,elapsed_ms:Date.now()-start,operation,timing:request.timing(),...extra});flush()}
  context.on('request',r=>record('request',r));context.on('requestfailed',r=>record('failed',r,{failure:r.failure()}));
  context.on('requestfinished',async r=>{let result;try{const response=await r.response(),body=await response.json();result={http:response.status(),success:body.success,lines:body.data?.lines?.map(l=>({key:l.key,source_id:l.source_id,variation_id:l.variation_id,quantity:l.quantity}))}}catch{}record('finished',r,{result})});
  let finished=false;
  async function finish(){if(finished)return;finished=true;for(const [n,page] of context.pages().entries()){try{await page.screenshot({path:out+'/context-'+id+'-page-'+n+'.png',timeout:3000})}catch{}}try{await context.tracing.stop({path:out+'/context-'+id+'-trace.zip'})}catch{}flush();finishers.delete(context)}
  finishers.set(context,finish);const close=context.close.bind(context);context.close=async(...a)=>{await finish();return close(...a)};return context;
 };
 const close=browser.close.bind(browser);browser.close=async(...a)=>{for(const finish of [...finishers.values()])await finish();return close(...a)};return browser;
};

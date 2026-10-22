import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { startPreview, approvedSHA } from './server.mjs';
const mode = process.argv[2];
const targeted=['b11','b12','b13'].includes(process.argv[3])&&process.argv.length===4;
if (!['test','baseline'].includes(mode) || (process.argv.length!==3&&!targeted)) throw Error('Use test or baseline, optionally followed by b11, b12 or b13; CLI snapshot-update overrides are forbidden');
const protectedHashes=JSON.parse(readFileSync('qa/visual/baseline-manifest.json')).hashes;
const preview = await startPreview({renderCurrent:mode!=='baseline'});
try {
  const env = {...process.env, ROLLSBAR_BASELINE:mode==='baseline'?'1':'0'};
  const exit = await new Promise(resolve=>{
    const args=['qa/node_modules/@playwright/test/cli.js','test','-c','qa/visual/playwright.config.mjs'];
    if(targeted)args.push('--grep',process.argv[3]);
    const child=spawn(process.execPath,args,{env,stdio:'inherit'});
    child.on('exit',resolve);
  });
  if (mode==='baseline' && exit===0) {
    for(const [file,hash] of Object.entries(protectedHashes)) {
      const actual=createHash('sha256').update(readFileSync(`qa/visual/baselines/${file}`)).digest('hex');
      if(actual!==hash)throw Error(`STOP: protected baseline changed: ${file}`);
    }
    const hashes={};
    for (const folder of readdirSync('qa/visual/baselines')) for(const file of readdirSync(`qa/visual/baselines/${folder}`)) {
      hashes[`${folder}/${file}`]=createHash('sha256').update(readFileSync(`qa/visual/baselines/${folder}/${file}`)).digest('hex');
    }
    writeFileSync('qa/visual/baseline-manifest.json',JSON.stringify({approvedSHA,source:'demo.html > client-fixes.html > index.html',platform:process.platform,node:process.version,playwright:JSON.parse(readFileSync('qa/node_modules/@playwright/test/package.json')).version,hashes},null,2)+'\n');
  }
  process.exitCode=exit??1;
} finally { await preview.close(); }

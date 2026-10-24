const fs = require('fs');
const path = require('path');
const {createRequire} = require('module');
const requireQA = createRequire(path.resolve('qa/package.json'));
const requireTest = createRequire(requireQA.resolve('@playwright/test'));
const requirePlaywright = createRequire(requireTest.resolve('playwright'));
const core = path.dirname(requirePlaywright.resolve('playwright-core/package.json'));
const {yaml} = require(path.join(core, 'lib/utilsBundle.js'));
const workflows = [];
for (const filename of fs.readdirSync('.github/workflows').filter(x => x.endsWith('.yml'))) {
  const source = fs.readFileSync(path.join('.github/workflows', filename), 'utf8');
  const doc = yaml.parseDocument(source, {uniqueKeys: true});
  if (doc.errors.length) throw Error(filename + ': invalid YAML');
  const w = doc.toJS();
  if (!w.on || !w.jobs) throw Error(filename + ': missing trigger/jobs');
  const push = w.on.push;
  if (push && JSON.stringify(push.branches) !== JSON.stringify(['wordpress/migration-2026-10-01'])) throw Error(filename + ': repair push trigger not proven safe');
  if (w.on.workflow_run || w.on.workflow_call || w.on.schedule) throw Error(filename + ': indirect workflow trigger requires audit');
  workflows.push({filename, name:w.name, push:push || null});
}
console.log(JSON.stringify({pass:true, workflows}, null, 2));

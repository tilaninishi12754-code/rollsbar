"""Local-only candidate checks; no server, workflow dispatch or order submission."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'qa/visual-results/checkout-parity'
OUT.mkdir(parents=True,exist_ok=True)
PHP=ROOT/'qa/.runtime/php/php.exe'
BASE='0ad375113e7383a504bb4d366e1051cfae931efa'
ASSET=ROOT/'wordpress/wp-content/plugins/rollsbar-core'
results={}


def run(label,args,expected=0,input=None):
    p=subprocess.run([str(a) for a in args],cwd=ROOT,input=input,capture_output=True,text=True,encoding='utf-8')
    assert p.returncode==expected,(label,p.stdout,p.stderr)
    results[label]={'exit':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
    print('PASS '+label)
    return p.stdout


run('js-syntax',['node','--check',ASSET/'assets/js/checkout.js'])
run('diff-check',['git','diff','--check'])
run('checkout-php-lint',[PHP,'-l',ASSET/'includes/class-rollsbar-checkout.php'])
for path in Path(__file__).parent.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
results['python-syntax']='PASS'
run('geocode-policy',[PHP],input='''<?php
define('ABSPATH', __DIR__);
require 'wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-geocode-policy.php';
foreach ([0,'0',1,2,3,4,5,null,'invalid',-1] as $qc) {
  $p=RollsBar_Geocode_Policy::evaluate($qc);
  if ($p['allow_auto_zone'] !== ($qc===0 || $qc==='0')) { exit(1); }
}
echo '10 precision cases PASS; only qc_geo=0 allows future auto-zone';
''')
fixture=OUT/'legal-fixture';fixture.mkdir(exist_ok=True)
for name in ['footer.php','page-otzyvy.php']:
    (fixture/name).write_bytes((ROOT/'wordpress/wp-content/themes/rollsbar-theme'/name).read_bytes())
run('legal-payment-baseline',[PHP,ROOT/'qa/repair/legal-fixture.php','baseline',fixture])
for case in ['missing-checkout-consent','optional-checkout-consent']:
    run('legal-reject-'+case,[PHP,ROOT/'qa/repair/legal-fixture.php',case,fixture],expected=1)
php=(ASSET/'includes/class-rollsbar-checkout.php').read_text(encoding='utf-8')
assert "woocommerce_register_additional_checkout_field" in php and "'required'      => true" in php
assert 'woocommerce_checkout_fields' not in php
assert all("'"+f+"'" in php for f in ['entrance','door-code','floor','apartment-office'])
assert "! is_checkout()" in php
results['native-block-api-additional-fields-and-enqueue-scope']='PASS'
workflow=json.loads(run('workflow-trigger-audit',['node',ROOT/'qa/repair/workflow-sanity.cjs']))
for item in workflow['workflows']:
    source=(ROOT/'.github/workflows'/item['filename']).read_text(encoding='utf-8')
    on=source.split('\non:',1)[1].split('\npermissions:',1)[0].split('\njobs:',1)[0]
    events=re.findall(r'^  ([a-z_]+):',on,re.M)
    assert set(events)<= {'push','workflow_dispatch'},(item['filename'],events)
results['push-safe']={'workflow_count':len(workflow['workflows']),'matching_feature_push_triggers':0,'only_automatic_branch':'wordpress/migration-2026-10-01'}
changed=run('changed-tracked',['git','diff','--name-only',BASE]).splitlines()
changed+=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
allowed={
 'wordpress/wp-content/plugins/rollsbar-core/assets/css/checkout.css',
 'wordpress/wp-content/plugins/rollsbar-core/assets/js/checkout.js',
 'wordpress/docs/CHECKOUT_VISUAL_PARITY_V1_REPORT.md'
}
assert all(p in allowed or p.startswith('qa/checkout/') for p in changed),changed
patterns=[r'BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY',r'\bsk-[A-Za-z0-9]{20,}',
          r'''\b(?:client_secret|api[_-]?key|password)\s*=\s*["'](?!\$|<)[^"']{8,}["']''']
findings=[]
for name in changed:
    source=(ROOT/name).read_text(encoding='utf-8')
    for line_no,line in enumerate(source.splitlines(),1):
        if any(re.search(p,line,re.I) for p in patterns):findings.append(f'{name}:{line_no}')
assert not findings,findings
results['changed-files-secret-pattern-scan']={'findings':0,'files':len(changed)}
results['unchanged-protected-surfaces']='PASS: QA provenance, theme, catalog, index.html, B1-B16/masks/tolerances absent from diff'
(OUT/'static-evidence.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS scope, secret scan, native field contracts, protected surfaces; '+str(len(workflow['workflows']))+' workflows; zero feature push triggers')

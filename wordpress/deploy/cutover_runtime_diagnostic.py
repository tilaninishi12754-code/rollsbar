import json,pathlib
from cutover_prepare import run
manifest=json.loads(pathlib.Path('wordpress/deploy/runtime-promotion-manifest.json').read_text())
script='set -euo pipefail\nroot="$HOME/www/rollsbar.ru"\n'
for i in manifest:
 script+='digest=$(sha256sum "$root/'+i['path']+'" | cut -d" " -f1)\n'
 script+='if [[ "$digest" == '+i['before']+' ]]; then echo '+i['path'].split('/')[-1]+'=base; elif [[ "$digest" == '+i['after']+' ]]; then echo '+i['path'].split('/')[-1]+'=candidate; else echo '+i['path'].split('/')[-1]+'=other; fi\n'
script+='''for file in "$HOME/rollsbar-backups/production-runtime-"*/native-fixture.log; do
 if [[ -f "$file" ]]; then grep -E '^PASS |Exception|Fatal error|Error:' "$file" | tail -n 8; fi
done
'''
print(run(None,script,timeout=120))

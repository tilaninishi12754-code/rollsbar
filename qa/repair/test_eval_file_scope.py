"""Behavioral eval-file scope regression; fixture SQL only, no network/live DB."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PHP = Path(os.environ.get('ROLLSBAR_PHP', ROOT / 'qa/.runtime/php/php.exe'))
RESULTS = ROOT / 'qa/visual-results/s1-r2f'
BASE = '37b3de35c347b81c75a7668fa07c496e0765c0ac'
NAMES = ['repair-staging-shrimp-options.php', 'verify-staging-s1-r2.php']


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    records = []

    def check(label, path, expected=0, contains='FUNCTION_SCOPE_PASS writes=0', mode=''):
        result = subprocess.run(
            [str(PHP), '-d', 'display_errors=stderr', str(ROOT / 'qa/repair/eval-file-scope.php'), str(path), mode],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30)
        output = result.stdout + result.stderr
        assert result.returncode == expected and contains in output, (label, output)
        if expected == 0 or mode:
            assert not re.search(r'(?:Warning|Fatal error|Deprecated|Parse error):', output), output
        if expected:
            assert 'FUNCTION_SCOPE_PASS' not in output, output
        records.append(dict(case=label, exit_code=result.returncode, output=output.strip(), pass_=True))
        print('PASS ' + label)

    # Copies preserve the real entrypoint's relative library/catalog paths.
    # No production source is altered for baseline or binding-removal mutants.
    with tempfile.TemporaryDirectory(prefix='scope-', dir=RESULTS) as folder:
        project = Path(folder)
        deploy = project / 'deploy'
        deploy.mkdir()
        (project / 'data').mkdir()
        # Adapter already loaded the real class; avoid declaring it a second time
        # under a temporary pathname. The shim still resolves to unchanged code.
        library = (ROOT / 'wordpress/deploy/shrimp-options-repair.php').as_posix()
        (deploy / 'shrimp-options-repair.php').write_text('<?php require_once ' + json.dumps(library) + ';\n', encoding='utf-8')
        shutil.copyfile(ROOT / 'wordpress/data/catalog.json', project / 'data/catalog.json')
        for name in NAMES:
            path = ROOT / 'wordpress/deploy' / name
            baseline = subprocess.check_output(['git', 'show', f'{BASE}:wordpress/deploy/{name}'], cwd=ROOT)
            copy = deploy / name
            copy.write_bytes(baseline)
            check('pre-fix:' + name, copy, 1, 'Undefined variable $wpdb')
            assert 'prepare() on null' in records[-1]['output'] if name == NAMES[0] else 'get_col() on null' in records[-1]['output']
            check('function-scope:' + name, path)
            source = path.read_text(encoding='utf-8')
            mutant, count = re.subn(r'^\s*global \$wpdb;\s*$', '', source, flags=re.M)
            assert count == 1, 'Mutation must remove exactly one DB binding'
            copy.write_text(mutant, encoding='utf-8')
            check('removed-binding:' + name, copy, 1, 'REFUSE: usable WordPress database handle required.')
            for mode in ['missing', 'invalid']:
                check(mode + '-global:' + name, path, 1, 'REFUSE: usable WordPress database handle required.', mode)
        for path in [ROOT / 'qa/repair/eval-file-scope.php', ROOT / 'qa/repair/shrimp-contract.php',
                     *(ROOT / 'wordpress/deploy' / name for name in NAMES)]:
            result = subprocess.run([str(PHP), '-l', str(path)], capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr
    (RESULTS / 'results.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'S1-R2F FUNCTION SCOPE PASS: {len(records)} behavioral cases; fixture only')


if __name__ == '__main__':
    main()

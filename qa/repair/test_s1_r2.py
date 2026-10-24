"""No-network release gates; real shell backup code with isolated command adapters."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'wordpress/deploy'))
from catalog_browser_contract import verify_catalog

BASH = os.environ.get('ROLLSBAR_BASH', r'C:\programm\Git\bin\bash.exe' if os.name == 'nt' else 'bash')
PHP = ROOT / 'qa/.runtime/php/php.exe' if os.name == 'nt' else Path('php')
RESULTS = ROOT / 'qa/visual-results/s1-r2'
RESULTS.mkdir(parents=True, exist_ok=True)


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], cwd=ROOT, text=True, encoding='utf-8', capture_output=True, timeout=90, **kwargs)


def must(result, label):
    assert result.returncode == 0, label + '\n' + result.stdout + result.stderr
    print('PASS ' + label)


canonical = [p['id'] for p in json.loads((ROOT / 'wordpress/data/catalog.json').read_text(encoding='utf-8'))['products']]
hits = canonical[:8]
verify_catalog(canonical, hits, canonical + hits, canonical)
for main, hit_rows, reps in [(canonical[:-1], hits, canonical[:-1]+hits), (canonical, hits[:-1], canonical+hits[:-1]), (canonical, hits, canonical+hits+['unexpected']), (canonical[:-1]+[canonical[0]], hits, canonical+hits)]:
    try:
        verify_catalog(main, hit_rows, reps, canonical)
    except AssertionError:
        pass
    else:
        raise AssertionError('Deliberate catalog mismatch was accepted')
print('PASS current 118/126/8/118 contract and four deliberate mismatches')
gate = (ROOT / 'wordpress/deploy/gate_b_browser.py').read_text(encoding='utf-8')
assert '== 5' not in gate and '5 smoke' not in gate
assert "'/wc/store/v1/checkout'" in gate and 'route.abort()' in gate
assert 'wc-ajax=checkout' in gate and "control.select_option('сырный')" in gate

for path in (ROOT / 'wordpress/deploy').glob('*.py'):
    ast.parse(path.read_text(encoding='utf-8-sig'))
for path in (ROOT / 'qa/repair').glob('*.py'):
    ast.parse(path.read_text(encoding='utf-8-sig'))
print('PASS Python syntax')
for name in ['backup-staging.sh', 'prepare-s1-r2-backup.sh', 'repair-s1-r2.sh', 'bootstrap-staging.sh']:
    must(run([BASH, '-n', ROOT / 'wordpress/deploy' / name]), 'shell syntax ' + name)
must(run([PHP, '-l', ROOT / 'wordpress/deploy/verify-staging-s1-r2.php']), 'live verifier PHP lint')
must(run(['node', 'qa/repair/workflow-sanity.cjs']), 'all workflow YAML + repair push isolation')

deploy = (ROOT / 'wordpress/deploy/deploy_staging_wordpress.py').read_text(encoding='utf-8')
assert deploy.index('prepare-s1-r2-backup.sh') < deploy.index('bash "$PROJECT_ROOT/wordpress/deploy/preflight.sh"') < deploy.index('bash "$PROJECT_ROOT/wordpress/deploy/bootstrap-staging.sh"') < deploy.index('repair-s1-r2.sh')
assert '"ROLLSBAR_IMPORT_SMOKE": "0"' in deploy
assert 'backup_skipped_fresh_install' not in deploy
workflow = (ROOT / '.github/workflows/deploy-reg-ru-staging-wordpress.yml').read_text(encoding='utf-8')
assert workflow.index('deploy_staging_wordpress.py') < workflow.index('run: python3 wordpress/deploy/provision_staging_seo.py') < workflow.index('run: python3 wordpress/deploy/harden_staging_http.py') < workflow.index('run: python3 wordpress/deploy/audit_staging_seo.py') < workflow.index('run: python3 wordpress/deploy/mark_staging_deployed_sha.py')
print('PASS backup/bootstrap/repair/SEO/hardening/audit/marker order and no import')

for case in ['success', 'missing-old', 'corrupt-old', 'retention-risk', 'export-fail', 'wrong-version']:
    with tempfile.TemporaryDirectory(prefix='backup-', dir=RESULTS) as folder:
        base = Path(folder)
        project = base / 'project/wordpress/deploy'
        project.mkdir(parents=True)
        # Test-only HOME substitution keeps the actual user HOME untouched.
        for name in ['prepare-s1-r2-backup.sh', 'backup-staging.sh']:
            content = (ROOT / 'wordpress/deploy' / name).read_text(encoding='utf-8').replace('$HOME', '$TEST_HOME')
            (project / name).write_text(content, encoding='utf-8', newline='\n')
        mock = base / 'bin'
        mock.mkdir()
        (mock / 'wp').write_text('''#!/usr/bin/env bash
set -eu
shift
case "$*" in
  'option get home'|'option get siteurl') echo https://staging.rollsbar.ru ;;
  'option get blog_public') echo 0 ;;
  'core version') [[ "$CASE" != wrong-version ]] || { echo 7.0; exit; }; echo 7.1.3 ;;
  'plugin get woocommerce --field=version') echo 11.1.2 ;;
  'eval echo wp_get_environment_type();') echo staging ;;
  'post list --post_type=product --post_status=publish --format=count') echo 118 ;;
  'db export '* ) echo export >>"$TEST_HOME/calls"; [[ "$CASE" != export-fail ]] || exit 1; echo 'CREATE TABLE local_fixture (id INT);' ;;
  *) echo unexpected_mock_wp_command >&2; exit 9 ;;
esac
''', encoding='utf-8', newline='\n')
        # Windows does not expose POSIX file mode 600; only adapt that stat call.
        (mock / 'stat').write_text('''#!/usr/bin/env bash
if [[ "$1" == -c && "$2" == %a && "$3" == *deployed-sha ]]; then echo 600; else /usr/bin/stat "$@"; fi
''', encoding='utf-8', newline='\n')
        harness = '''set -euo pipefail
export TEST_HOME="$PWD/home" CASE
export PATH="$PWD/bin:$PATH"
export PROJECT_ROOT="$PWD/project" WP_PATH="$TEST_HOME/www/staging.rollsbar.ru"
mkdir -p "$WP_PATH/wp-content/uploads" "$TEST_HOME/rollsbar-backups/staging/20261023T215945Z"
touch "$WP_PATH/wp-load.php"
printf '%040d\n' 1 >"$TEST_HOME/.rollsbar-staging-deployed-sha"
old="$TEST_HOME/rollsbar-backups/staging/20261023T215945Z"
printf 'SQL fixture\n' | gzip >"$old/database.sql.gz"
tar -C "$WP_PATH/wp-content" -czf "$old/uploads.tar.gz" uploads
printf 'site_url=https://staging.rollsbar.ru\ndatabase_archive=database.sql.gz\nuploads_archive=uploads.tar.gz\n' >"$old/manifest.txt"
(cd "$old"; sha256sum database.sql.gz uploads.tar.gz manifest.txt >SHA256SUMS)
if [[ "$CASE" == missing-old ]]; then mv "$old" "$old-absent"; fi
if [[ "$CASE" == corrupt-old ]]; then echo broken >>"$old/database.sql.gz"; fi
if [[ "$CASE" == retention-risk ]]; then for n in 1 2 3 4; do mkdir "$TEST_HOME/rollsbar-backups/staging/20261024T00000${n}Z"; done; fi
source "$PROJECT_ROOT/wordpress/deploy/prepare-s1-r2-backup.sh"
[[ "$ROLLSBAR_FRESH_BACKUP_VERIFIED" == YES ]]
echo ACCEPTED_BEFORE_BOOTSTRAP
'''
        (base / 'harness.sh').write_text(harness, encoding='utf-8', newline='\n')
        result = subprocess.run([BASH, 'harness.sh'], cwd=base, env={**os.environ, 'CASE':case}, capture_output=True, text=True, encoding='utf-8', timeout=45)
        (RESULTS / (case + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        assert (result.returncode == 0) == (case == 'success'), (case, result.stdout, result.stderr)
        assert ('ACCEPTED_BEFORE_BOOTSTRAP' in result.stdout) == (case == 'success')
        if case not in ['success','export-fail']:
            assert not (base / 'home/calls').exists(), 'refusal must precede DB export'
        if case != 'missing-old':
            assert (base / 'home/rollsbar-backups/staging/20261023T215945Z').is_dir()
        print('PASS actual backup gate ' + case)

for case in ['pending', 'canonical', 'conflict', 'apply-fail', 'post-fail', 'runtime-fail']:
    with tempfile.TemporaryDirectory(prefix='repair-', dir=RESULTS) as folder:
        base = Path(folder)
        mock = base / 'bin'
        mock.mkdir()
        (mock / 'wp').write_text('''#!/usr/bin/env bash
set -eu
echo "$* mode=${ROLLSBAR_SHRIMP_REPAIR_MODE:-runtime}" >>calls
if [[ "$*" == *repair-staging-shrimp-options.php ]]; then
  if [[ "$ROLLSBAR_SHRIMP_REPAIR_MODE" == apply ]]; then
    [[ "$CASE" != apply-fail ]] || exit 1
    [[ "$ROLLSBAR_CONFIRM_SHRIMP_OPTIONS" == staging:shrimp-tempura:options-only ]]
    [[ "$ROLLSBAR_FRESH_BACKUP_VERIFIED" == YES ]]
    touch applied
    echo '{"writes":1,"status":"REPAIRED"}'
  else
    [[ "$CASE" != conflict ]] || exit 1
    state=pending
    if [[ "$CASE" == canonical || -f applied ]]; then state=canonical; fi
    if [[ "$CASE" == post-fail && -f applied ]]; then state=pending; fi
    printf '{"source_id":"shrimp-tempura","writes":0,"before_state":"%s"}\n' "$state"
  fi
else
  [[ "$CASE" != runtime-fail ]] || exit 1
  echo 'fixture runtime pass'
fi
''', encoding='utf-8', newline='\n')
        (base / 'harness.sh').write_text('''set -euo pipefail
export PATH="$PWD/bin:$PHP_BIN:$PATH"
export WP_PATH="$PWD/fake-wordpress" PROJECT_ROOT="$REPO_ROOT"
export ROLLSBAR_FRESH_BACKUP_VERIFIED=YES ROLLSBAR_FRESH_BACKUP_SNAPSHOT=20261024T000000Z
bash "$PROJECT_ROOT/wordpress/deploy/repair-s1-r2.sh"
echo ACCEPTANCE_READY
''', encoding='utf-8', newline='\n')
        # MSYS accepts forward-slash drive paths in exported paths.
        def posix(path):
            value = str(path).replace('\\', '/')
            return '/' + value[0].lower() + value[2:] if os.name == 'nt' else value
        result = subprocess.run([BASH, 'harness.sh'], cwd=base, env={**os.environ, 'CASE':case, 'PHP_BIN':posix(PHP.parent.resolve()), 'REPO_ROOT':posix(ROOT)}, capture_output=True, text=True, encoding='utf-8', timeout=45)
        (RESULTS / ('repair-' + case + '.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        assert (result.returncode == 0) == (case in ['pending','canonical']), (case,result.stdout,result.stderr)
        calls = (base / 'calls').read_text(encoding='utf-8')
        if case in ['canonical','conflict']:
            assert 'mode=apply' not in calls
        if case in ['conflict','apply-fail','post-fail']:
            assert 'verify-staging-s1-r2.php' not in calls
        print('PASS actual repair sequencing ' + case)

must(run([sys.executable, '-X', 'utf8', 'qa/repair/test_eval_file_scope.py']), 'both eval-file entrypoints under function scope')
must(run([sys.executable, '-X', 'utf8', 'qa/repair/test_s1_r1.py', '--s1-r2']), 'S1-R1 suite including extended shrimp rollback states')
must(run(['git', 'diff', '--check']), 'diff check')
print('S1-R2 LOCAL PRE-PUSH PASS')

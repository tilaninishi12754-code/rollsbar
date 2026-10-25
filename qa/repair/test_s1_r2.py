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

backup_cases = ['success', 'old-capacity-proof', 'current-capacity', 'repeat-rotation', 'missing-old',
                'corrupt-old', 'export-fail', 'wrong-version', 'wrong-woocommerce',
                'wrong-home', 'wrong-siteurl', 'wrong-environment', 'public-site',
                'missing-wp', 'missing-cli', 'missing-marker', 'invalid-marker',
                'marker-mode', 'retention-one', 'retention-zero', 'retention-invalid',
                'retention-huge', 'unprotected-one',
                'archive-fail', 'manifest-fail', 'checksum-fail', 'unprotected',
                'lock-busy', 'concurrent-start', 'fresh-not-newest', 'tmp-collision']
if '--case' in sys.argv:
    selected = sys.argv[sys.argv.index('--case') + 1]
    assert selected in backup_cases, selected
    backup_cases = [selected]
backup_evidence = {}
for case in backup_cases:
    with tempfile.TemporaryDirectory(prefix='backup-', dir=RESULTS) as folder:
        base = Path(folder)
        project = base / 'project/wordpress/deploy'
        project.mkdir(parents=True)
        # Test-only HOME substitution keeps the actual user HOME untouched.
        for name in ['prepare-s1-r2-backup.sh', 'backup-staging.sh']:
            if case == 'old-capacity-proof' and name == 'backup-staging.sh':
                content = subprocess.check_output(['git', 'show', '21abd16e4e970e535b9f22971ee9c4464f0cea24:wordpress/deploy/' + name], cwd=ROOT).decode('utf-8')
            else:
                content = (ROOT / 'wordpress/deploy' / name).read_text(encoding='utf-8')
            content = content.replace('$HOME', '$TEST_HOME')
            (project / name).write_text(content, encoding='utf-8', newline='\n')
        mock = base / 'bin'
        mock.mkdir()
        (mock / 'wp').write_text('''#!/usr/bin/env bash
set -eu
shift
case "$*" in
  'option get home') [[ "$CASE" != wrong-home ]] || { echo https://fixture.invalid; exit; }; echo https://staging.rollsbar.ru ;;
  'option get siteurl') [[ "$CASE" != wrong-siteurl ]] || { echo https://fixture.invalid; exit; }; echo https://staging.rollsbar.ru ;;
  'option get blog_public') [[ "$CASE" != public-site ]] || { echo 1; exit; }; echo 0 ;;
  'core version')
    [[ "$CASE" != manifest-fail || ! -f "$TEST_HOME/calls" ]] || exit 8
    [[ "$CASE" != wrong-version ]] || { echo 7.0; exit; }; echo 7.1.3 ;;
  'plugin get woocommerce --field=version') [[ "$CASE" != wrong-woocommerce ]] || { echo 11.0; exit; }; echo 11.1.2 ;;
  'eval echo wp_get_environment_type();') [[ "$CASE" != wrong-environment ]] || { echo production; exit; }; echo staging ;;
  'post list --post_type=product --post_status=publish --format=count') echo 118 ;;
  'db export '* )
    echo export >>"$TEST_HOME/calls"
    [[ "$CASE" != export-fail ]] || exit 1
    if [[ "$CASE" == concurrent-start ]]; then
      if CASE=success bash "$PROJECT_ROOT/wordpress/deploy/backup-staging.sh" >"$TEST_HOME/concurrent.log" 2>&1; then exit 77; fi
      grep -q 'backup already running' "$TEST_HOME/concurrent.log"
    fi
    echo 'CREATE TABLE local_fixture (id INT);' ;;
  *) echo unexpected_mock_wp_command >&2; exit 9 ;;
esac
''', encoding='utf-8', newline='\n')
        # Windows does not expose POSIX file mode 600; only adapt that stat call.
        (mock / 'stat').write_text('''#!/usr/bin/env bash
if [[ "$1" == -c && "$2" == %a && "$3" == *deployed-sha ]]; then
  if [[ "$CASE" == marker-mode ]]; then echo 644; else echo 600; fi
else /usr/bin/stat "$@"; fi
''', encoding='utf-8', newline='\n')
        (mock / 'date').write_text('''#!/usr/bin/env bash
set -eu
if [[ "$*" == '-u +%Y%m%dT%H%M%SZ' ]]; then
  n=0; [[ ! -f "$TEST_HOME/clock" ]] || read -r n <"$TEST_HOME/clock"
  n=$((n+1)); echo "$n" >"$TEST_HOME/clock"
  stamp="$(printf '20261025T1600%02dZ' "$n")"
  if [[ "$CASE" == tmp-collision ]]; then
    abandoned="$TEST_HOME/rollsbar-backups/staging/.tmp-$stamp-$PPID"
    mkdir "$abandoned"; echo untouched >"$abandoned/sentinel"
  fi
  printf '%s\n' "$stamp"
else /usr/bin/date "$@"; fi
''', encoding='utf-8', newline='\n')
        (mock / 'tar').write_text('''#!/usr/bin/env bash
set -eu
if [[ "$CASE" == archive-fail && "$*" == *-czf* && "$*" == *'.tmp-'* ]]; then
  while [[ "$1" != -czf ]]; do shift; done
  printf 'invalid tar archive\n' >"$2"
else /usr/bin/tar "$@"; fi
''', encoding='utf-8', newline='\n')
        (mock / 'sha256sum').write_text('''#!/usr/bin/env bash
set -eu
if [[ "$CASE" == checksum-fail && "$PWD" == *'.tmp-'* && "$1" == -c ]]; then exit 9; fi
/usr/bin/sha256sum "$@"
''', encoding='utf-8', newline='\n')
        harness = '''set -euo pipefail
export TEST_HOME="$PWD/home" CASE
export PATH="$PWD/bin:$PATH"
export PROJECT_ROOT="$PWD/project" WP_PATH="$TEST_HOME/www/staging.rollsbar.ru"
mkdir -p "$WP_PATH/wp-content/uploads" "$TEST_HOME/rollsbar-backups/staging/20261023T215945Z"
touch "$WP_PATH/wp-load.php"
printf '%040d\n' 1 >"$TEST_HOME/.rollsbar-staging-deployed-sha"
old="$TEST_HOME/rollsbar-backups/staging/20261023T215945Z"
fixture_snapshot(){
  mkdir -p "$1"
  printf 'SQL fixture\n' | gzip >"$1/database.sql.gz"
  tar -C "$WP_PATH/wp-content" -czf "$1/uploads.tar.gz" uploads
  printf 'site_url=https://staging.rollsbar.ru\ndatabase_archive=database.sql.gz\nuploads_archive=uploads.tar.gz\n' >"$1/manifest.txt"
  (cd "$1"; sha256sum database.sql.gz uploads.tar.gz manifest.txt >SHA256SUMS)
}
fixture_snapshot "$old"
if [[ "$CASE" != success ]]; then
  for n in 1 2 3 4 5; do fixture_snapshot "$TEST_HOME/rollsbar-backups/staging/20261024T00000${n}Z"; done
fi
# Unknown/incomplete directories and state outside BACKUP_ROOT must survive.
mkdir -p "$TEST_HOME/rollsbar-backups/staging/.tmp-existing" "$TEST_HOME/rollsbar-backups/staging/2000000AT000000Z" "$TEST_HOME/rollsbar-backups/staging/20261022T000000Z" "$TEST_HOME/outside/20261024T000001Z"
for dir in "$TEST_HOME/rollsbar-backups/staging/.tmp-existing" "$TEST_HOME/rollsbar-backups/staging/2000000AT000000Z" "$TEST_HOME/rollsbar-backups/staging/20261022T000000Z" "$TEST_HOME/outside/20261024T000001Z"; do echo untouched >"$dir/sentinel"; done
if [[ "$CASE" == missing-old ]]; then mv "$old" "$old-absent"; fi
if [[ "$CASE" == corrupt-old ]]; then echo broken >>"$old/database.sql.gz"; fi
if [[ "$CASE" == missing-wp ]]; then rm "$WP_PATH/wp-load.php"; fi
if [[ "$CASE" == missing-cli ]]; then mv "$PWD/bin/wp" "$PWD/bin/wp-disabled"; fi
if [[ "$CASE" == missing-marker ]]; then rm "$TEST_HOME/.rollsbar-staging-deployed-sha"; fi
if [[ "$CASE" == invalid-marker ]]; then echo invalid >"$TEST_HOME/.rollsbar-staging-deployed-sha"; fi
if [[ "$CASE" == lock-busy ]]; then mkdir "$TEST_HOME/rollsbar-backups/staging/.backup-staging.lock"; echo other-owner >"$TEST_HOME/rollsbar-backups/staging/.backup-staging.lock/owner"; fi
if [[ "$CASE" == fresh-not-newest ]]; then
  for n in 1 2 3 4 5; do mv "$TEST_HOME/rollsbar-backups/staging/20261024T00000${n}Z" "$TEST_HOME/rollsbar-backups/staging/20261026T00000${n}Z"; done
fi
if [[ "$CASE" != missing-old ]]; then
  mkdir "$TEST_HOME/protected-before"
  cp "$old"/{database.sql.gz,uploads.tar.gz,manifest.txt,SHA256SUMS} "$TEST_HOME/protected-before/"
fi
(cd "$TEST_HOME/rollsbar-backups/staging"; find . -type f ! -path './.backup-staging.lock/*' -exec sha256sum {} + | sort) >"$TEST_HOME/before.sha"
if [[ "$CASE" == old-capacity-proof || "$CASE" == current-capacity ]]; then
  newer="$(find "$TEST_HOME/rollsbar-backups/staging" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -printf '%f\\n' | awk '$0 > "20261023T215945Z" {n++} END {print n+0}')"
  [[ "$newer" == 5 ]]
  echo 'fixture_newer_snapshots=5'
fi
case "$CASE" in
  retention-one|retention-zero|retention-invalid|retention-huge|unprotected|unprotected-one|missing-cli)
    export ROLLSBAR_BACKUP_ROOT="$TEST_HOME/rollsbar-backups/staging"
    export ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT=20261023T215945Z ROLLSBAR_BACKUP_RETENTION=6
    case "$CASE" in
      retention-one) export ROLLSBAR_BACKUP_RETENTION=1 ;;
      retention-zero) export ROLLSBAR_BACKUP_RETENTION=0 ;;
      retention-invalid) export ROLLSBAR_BACKUP_RETENTION=bad ;;
      retention-huge) export ROLLSBAR_BACKUP_RETENTION=99999999999999999999999999999999999 ;;
      unprotected) export ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT='' ROLLSBAR_BACKUP_RETENTION=3 ;;
      unprotected-one) export ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT='' ROLLSBAR_BACKUP_RETENTION=1 ;;
    esac
    bash "$PROJECT_ROOT/wordpress/deploy/backup-staging.sh" ;;
  *)
    runs=1; [[ "$CASE" != repeat-rotation ]] || runs=12
    for ((iteration=0; iteration<runs; iteration++)); do
      source "$PROJECT_ROOT/wordpress/deploy/prepare-s1-r2-backup.sh"
      [[ "$ROLLSBAR_FRESH_BACKUP_VERIFIED" == YES ]]
    done ;;
esac
echo ACCEPTED_BEFORE_BOOTSTRAP
'''
        (base / 'harness.sh').write_text(harness, encoding='utf-8', newline='\n')
        result = subprocess.run([BASH, 'harness.sh'], cwd=base, env={**os.environ, 'CASE':case}, capture_output=True, text=True, encoding='utf-8', timeout=45)
        (RESULTS / (case + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        succeeds = case in ['success', 'current-capacity', 'repeat-rotation', 'unprotected', 'unprotected-one', 'concurrent-start']
        assert (result.returncode == 0) == succeeds, (case, result.stdout, result.stderr)
        assert ('ACCEPTED_BEFORE_BOOTSTRAP' in result.stdout) == succeeds
        if case == 'old-capacity-proof':
            assert 'next retention would evict protected snapshot' in result.stdout
            assert 'fixture_newer_snapshots=5' in result.stdout
        exported = (base / 'home/calls').read_text().splitlines() if (base / 'home/calls').exists() else []
        if case not in ['success', 'current-capacity', 'repeat-rotation', 'unprotected', 'unprotected-one', 'concurrent-start', 'export-fail', 'archive-fail', 'manifest-fail', 'checksum-fail', 'fresh-not-newest']:
            assert not (base / 'home/calls').exists(), 'refusal must precede DB export'
        backups = base / 'home/rollsbar-backups/staging'
        complete = sorted(p.name for p in backups.iterdir() if p.is_dir() and (p / 'SHA256SUMS').is_file())
        if succeeds:
            fresh = sorted(p.name for p in backups.iterdir() if p.name.startswith('20261025T1600'))
            assert fresh and all((backups / name / 'database.sql.gz').stat().st_size > 0 for name in fresh)
            assert len(complete) == (2 if case == 'success' else 3 if case == 'unprotected' else 1 if case == 'unprotected-one' else 6), complete
            assert len(exported) == (12 if case == 'repeat-rotation' else 1), exported
            if case not in ['unprotected', 'unprotected-one']:
                assert '20261023T215945Z' in complete
                if case != 'success':assert '20261024T000001Z' not in complete
                protected_files = list((base / 'home/protected-before').iterdir())
                assert len(protected_files) == 4
                for original in protected_files:
                    assert (backups / '20261023T215945Z' / original.name).read_bytes() == original.read_bytes(), 'protected recovery bytes changed'
            else:
                expected = ['20261024T000004Z','20261024T000005Z','20261025T160001Z'] if case == 'unprotected' else ['20261025T160001Z']
                assert complete == expected, complete
            if case in ['current-capacity', 'concurrent-start']:
                assert complete == ['20261023T215945Z', '20261024T000002Z', '20261024T000003Z', '20261024T000004Z', '20261024T000005Z', '20261025T160001Z'], complete
            if case == 'repeat-rotation':
                assert complete == ['20261023T215945Z'] + [f'20261025T1600{n:02d}Z' for n in range(8,13)], complete
                assert result.stdout.count('retained_snapshots=6\n') == 12
            must(subprocess.run([BASH, '-c', 'for d in home/rollsbar-backups/staging/20261025T1600*; do (cd "$d"; sha256sum -c SHA256SUMS; gzip -t database.sql.gz; tar -tzf uploads.tar.gz >/dev/null); done'], cwd=base, capture_output=True, text=True), 'fresh archives/checksums ' + case)
        else:
            # Verify every pre-existing file, not just its directory name.
            must(subprocess.run([BASH, '-c', 'cd home/rollsbar-backups/staging; sha256sum -c "$OLD_HASHES"'], cwd=base, env={**os.environ, 'OLD_HASHES':str((base / 'home/before.sha').resolve()).replace('\\','/')}, capture_output=True, text=True), 'failure preserves every existing file ' + case)
            if case != 'fresh-not-newest':assert not any(p.name.startswith('20261025T1600') for p in backups.iterdir()), 'invalid backup was published'
        for directory in ['.tmp-existing', '2000000AT000000Z', '20261022T000000Z']:
            assert (backups / directory / 'sentinel').read_text().strip() == 'untouched'
        assert (base / 'home/outside/20261024T000001Z/sentinel').read_text().strip() == 'untouched'
        if case == 'fresh-not-newest':assert (backups / '20261025T160001Z/database.sql.gz').is_file()
        if case == 'tmp-collision':
            abandoned = list(backups.glob('.tmp-20261025T160001Z-*/sentinel'))
            assert len(abandoned) == 1 and abandoned[0].read_text().strip() == 'untouched'
        if case == 'lock-busy':assert (backups / '.backup-staging.lock/owner').read_text().strip() == 'other-owner'
        else:assert not (backups / '.backup-staging.lock').exists()
        if case == 'concurrent-start':assert 'backup already running' in (base / 'home/concurrent.log').read_text()
        backup_evidence[case] = {'exit':result.returncode, 'exports':len(exported), 'complete_after':complete,
                                 'rotated':[line.split('=',1)[1] for line in result.stdout.splitlines() if line.startswith('rotated_snapshot=')]}
        if case == 'current-capacity':
            backup_evidence[case].update(protected='20261023T215945Z', protected_bytes_unchanged=True,
                                        ordinary_before=5, ordinary_after=len(complete)-1,
                                        total_after=len(complete), fresh_created=fresh,
                                        fresh_archive_bytes={name:{f:(backups/name/f).stat().st_size for f in ['database.sql.gz','uploads.tar.gz']} for name in fresh})
        print('PASS actual backup gate ' + case)

(RESULTS / 'backup-rotation-evidence.json').write_text(json.dumps(backup_evidence,indent=2),encoding='utf-8')
if '--backup-only' in sys.argv:
    print('BACKUP ROTATION FOCUSED PASS');sys.exit(0)

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
must(run([sys.executable, '-X', 'utf8', 'qa/repair/test_s1_r1.py', '--s1-r2', '--backup-rotation']), 'S1-R1 backup-scope suite including extended shrimp rollback states')
must(run(['git', 'diff', '--check']), 'diff check')
print('S1-R2 LOCAL PRE-PUSH PASS')

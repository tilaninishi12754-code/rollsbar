"""Offline proof of partial-release gates, SEO contract wiring and workflow isolation."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import provision_staging_seo as seo
import mark_staging_deployed_sha as marker
import resume_staging_release as resume
from test_staging_forensics import fixture_report

ROOT = resume.ROOT
BASH = r'C:/programm/Git/bin/bash.exe' if os.name == 'nt' else 'bash'


def catalog():
    return json.loads(next(r['stdout'] for r in fixture_report()['probes'] if r['name'] == 'catalog_audit'))


def values_fixture(final=False):
    values = {r['name']: r['stdout'] for r in fixture_report()['probes']}
    values.update(resume.EXPECTED)
    values.update(resume.expected_hashes())
    values.update({'http_' + name: value for name, value in resume.expected_hashes().items()})
    values.update(marker_value=resume.RELEASE if final else resume.OLD, woocommerce_status='active')
    audit = catalog()
    audit['deployed_sha'] = values['marker_value']
    values['catalog_audit'] = json.dumps(audit)
    for name in (resume.FRESH, resume.PROTECTED):
        values['snapshot_' + name] = 'complete\nverified'
    values['fresh_manifest'] = '\n'.join(f'{k}={v}' for k, v in dict(
        created_utc=resume.FRESH, project_code_commit=resume.OLD,
        site_url='https://staging.rollsbar.ru', wordpress_version='7.1.3',
        woocommerce_version='11.1.2', published_products='121', blog_public='0').items())
    return values


def fixture_runner(values, failed=None, truncated=None):
    def run(name, command):
        return dict(status='FAIL' if name == failed else 'PASS',
                    exit_code=1 if name == failed else 0, stdout=values[name],
                    truncated=name == truncated, exception_type=None)
    return run


class SEOContract(unittest.TestCase):
    def test_old_failure_new_identity_contract_and_post_read(self):
        accepted = catalog()
        self.assertEqual(accepted['published_total'], 121)
        old = subprocess.check_output(['git', 'show', resume.RELEASE +
            ':wordpress/deploy/provision_staging_seo.py'], cwd=ROOT, text=True)
        self.assertIn('EXPECTED_PRODUCTS = "118"', old)
        self.assertNotEqual(accepted['published_total'], 118)
        with patch.object(seo, 'run_remote', side_effect=[json.dumps(accepted),
                'STAGING SEO PROVISION PASS', json.dumps(accepted)]) as remote:
            seo.execute(Mock(), resume.RELEASE, 'YES')
        self.assertEqual(remote.call_count, 3)
        self.assertIn(seo.AUDIT_PHP, remote.call_args_list[0].args[1].replace("'\"'\"'", "'"))
        self.assertIn('stage=install_pinned_seopress', remote.call_args_list[1].args[1])
        self.assertEqual(remote.call_args_list[0].args[1], remote.call_args_list[2].args[1])

    def test_all_negative_preconditions_block_seo_mutation(self):
        cases = dict(canonical_missing=1, canonical_duplicates=1, variation_mismatches=1,
            blank_variation_attributes=1, upsell_count=2, upsell_identity_mismatches=1,
            wrong_upsell_visibility=1, wrong_upsell_status=1, canonical_wrong_status=1,
            missing_provisional_provenance=1, unexpected_published_products=1,
            published_total=120, host='rollsbar.ru', environment='production')
        payloads = [dict(catalog(), **{k: v}) for k, v in cases.items()]
        payloads += [dict(catalog(), upsell_count=4), dict(catalog(), upsell_source_ids=['random']*3)]
        for audit in payloads:
            with self.subTest(audit=audit), patch.object(seo, 'run_remote', return_value=json.dumps(audit)) as remote:
                with self.assertRaises(RuntimeError):
                    seo.execute(Mock(), resume.RELEASE, 'YES')
                remote.assert_called_once()  # Only read-only catalog audit, no SEO script.

    def test_post_catalog_failure_blocks_marker(self):
        bad = dict(catalog(), canonical_missing=1)
        tool = Mock(side_effect=lambda name, env: seo.execute(Mock(), resume.RELEASE, 'YES'))
        with patch.object(seo, 'run_remote', side_effect=[json.dumps(catalog()),
                'STAGING SEO PROVISION PASS', json.dumps(bad)]):
            with self.assertRaises(RuntimeError):
                resume.run_resume(resume.RELEASE, resume.BRANCH, verifier=Mock(return_value=catalog()), tool=tool)
        self.assertEqual([c.args[0] for c in tool.call_args_list], ['provision_staging_seo'])

    def test_short_exec_no_retry_no_stderr_disclosure(self):
        client = Mock()
        out, err = Mock(), Mock()
        out.read.return_value = b''
        err.read.return_value = b'DB_PASSWORD=PRIVATE'
        out.channel.recv_exit_status.return_value = 1
        client.exec_command.return_value = (Mock(), out, err)
        with self.assertRaises(RuntimeError) as caught:
            seo.run_remote(client, 'fixed body')
        self.assertNotIn('PRIVATE', str(caught.exception))
        client.exec_command.assert_called_once_with("bash -lc 'exec bash -s'", timeout=900)

    def test_marker_uses_shared_catalog_before_write(self):
        with patch.object(marker, 'run_remote', return_value=json.dumps(dict(catalog(), upsell_count=2))) as remote:
            with self.assertRaises(RuntimeError):
                marker.execute(Mock(), resume.RELEASE)
            remote.assert_called_once()
        self.assertNotIn("'118'", marker.marker_script(resume.RELEASE))


class ResumeGates(unittest.TestCase):
    def test_accepted_and_final_state(self):
        for final in (False, True):
            resume.verify_state(final=final, runner=fixture_runner(values_fixture(final)))
        self.assertEqual(resume.expected_hashes(), {
            'checkout_css': '91cc7c13e28f546ed1048fd77d5101874aef57b5d3dde4383698186e8a814299',
            'checkout_js': '5906d5aedede20909483d09281395a56e9119c168bd17b6187023245f38b7ed6'})

    def test_every_mismatch_prevents_seo_call(self):
        cases = dict(marker_value='f'*40, repo_head='f'*40, repo_status=' M app.php',
            checkout_css='0'*64, checkout_js='0'*64,
            http_checkout_css='0'*64, http_checkout_js='0'*64, wordpress_version='wrong',
            woocommerce_version='wrong', theme_status='inactive', rollsbar_core_status='inactive',
            woocommerce_status='inactive', blog_public='1', environment='production',
            home='https://rollsbar.ru', siteurl='https://rollsbar.ru', backup_lock='directory|700|0',
            backup_tmp_dirs='.tmp-abandoned', runtime_object='regular|600|99',
            marker_object='symlink|600|41', backup_root='symlink|700|1',
            catalog_audit=json.dumps(dict(catalog(), variation_mismatches=1)),
            fresh_manifest=values_fixture()['fresh_manifest'].replace(resume.OLD, 'f'*40))
        for name in (resume.FRESH, resume.PROTECTED):
            cases['snapshot_' + name] = 'complete'  # Missing/corrupt verification.
        for name, value in cases.items():
            values = dict(values_fixture(), **{name: value})
            tool = Mock()
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                resume.run_resume(resume.RELEASE, resume.BRANCH,
                    verifier=lambda: resume.verify_state(runner=fixture_runner(values)), tool=tool)
            tool.assert_not_called()
        # Missing objects, command failures, timeouts/truncation never grant a pass.
        for name, _ in resume.probes():
            for mode in ('failed', 'truncated'):
                tool = Mock()
                with self.subTest(name=name, mode=mode), self.assertRaises(RuntimeError):
                    resume.run_resume(resume.RELEASE, resume.BRANCH,
                        verifier=lambda: resume.verify_state(runner=fixture_runner(values_fixture(), **{mode: name})), tool=tool)
                tool.assert_not_called()

    def test_strict_input_before_any_probe(self):
        for sha, branch in [('22aeb217',resume.BRANCH), ('f'*40,resume.BRANCH),
                (resume.RELEASE.upper(),resume.BRANCH), (resume.RELEASE+';id',resume.BRANCH),
                (resume.RELEASE,'main'), ('',resume.BRANCH)]:
            verifier, tool = Mock(), Mock()
            with self.assertRaises(ValueError):
                resume.run_resume(sha, branch, verifier=verifier, tool=tool)
            verifier.assert_not_called()
            tool.assert_not_called()

    def test_order_marker_application_sha_and_fail_closed(self):
        steps = ['provision_staging_seo', 'harden_staging_http', 'audit_staging_seo', 'mark_staging_deployed_sha']
        def verifier(**kwargs):
            return dict(catalog(), deployed_sha=resume.RELEASE if kwargs else resume.OLD)
        tool = Mock()
        with patch.dict(os.environ, GITHUB_SHA='f'*40):
            resume.run_resume(resume.RELEASE, resume.BRANCH, verifier=verifier, tool=tool)
        self.assertEqual([c.args[0] for c in tool.call_args_list], steps)
        for call in tool.call_args_list:
            self.assertEqual(call.args[1]['ROLLSBAR_DEPLOY_SHA'], resume.RELEASE)
            self.assertEqual(call.args[1]['ROLLSBAR_SEO_BACKUP_ALREADY_VERIFIED'], 'YES')
        for failure in steps[:3]:
            called = []
            def failing_tool(name, env):
                called.append(name)
                if name == failure:
                    raise RuntimeError('fixed failure')
            with self.subTest(failure=failure), self.assertRaises(RuntimeError):
                resume.run_resume(resume.RELEASE, resume.BRANCH, verifier=verifier, tool=failing_tool)
            self.assertNotIn(steps[-1], called)
        for index in (1, 2):  # Post-SEO and immediately before marker.
            checks = [catalog(), catalog(), catalog()]
            checks[index] = dict(catalog(), upsell_count=2)
            tool = Mock()
            with self.assertRaises(RuntimeError):
                resume.run_resume(resume.RELEASE, resume.BRANCH, verifier=Mock(side_effect=checks), tool=tool)
            self.assertNotIn(steps[-1], [c.args[0] for c in tool.call_args_list])
        tool = Mock()
        checks = [catalog()]*3 + [RuntimeError('final read failed')]
        with self.assertRaises(RuntimeError):
            resume.run_resume(resume.RELEASE, resume.BRANCH, verifier=Mock(side_effect=checks), tool=tool)
        self.assertEqual(tool.call_count, 4)

    def test_shell_syntax_and_snapshot_integrity(self):
        scripts = [seo.mutation_script(resume.RELEASE, 'YES'), marker.marker_script(resume.RELEASE)]
        scripts += [cmd for _, cmd in resume.probes()]
        for script in scripts:
            result = subprocess.run([BASH, '-n'], input=script, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        # Exercise the real fixed backup verifier against local archives.
        with tempfile.TemporaryDirectory() as home:
            folder = Path(home)/'rollsbar-backups/staging'/resume.FRESH
            folder.mkdir(parents=True)
            (folder/'database.sql.gz').write_bytes(gzip.compress(b'fixture SQL'))
            with tarfile.open(folder/'uploads.tar.gz', 'w:gz') as archive:
                info = tarfile.TarInfo('uploads/fixture'); info.size = 1
                archive.addfile(info, io.BytesIO(b'x'))
            (folder/'manifest.txt').write_text('fixture manifest')
            sums = ''.join(hashlib.sha256((folder/name).read_bytes()).hexdigest()+'  '+name+'\n'
                           for name in ['database.sql.gz','uploads.tar.gz','manifest.txt'])
            (folder/'SHA256SUMS').write_text(sums, newline='\n')
            import shlex
            prefix = 'HOME="$(cd '+shlex.quote(Path(home).as_posix())+' && pwd)"\n'
            def check():
                result = subprocess.run([BASH], input=prefix+resume.verified_snapshot(resume.FRESH),
                                      text=True, capture_output=True)
                return result.returncode
            self.assertEqual(check(), 0)
            (folder/'SHA256SUMS').write_text(sums.splitlines()[0]+'\n', newline='\n')
            self.assertNotEqual(check(), 0)
            (folder/'SHA256SUMS').write_text(sums, newline='\n')
            (folder/'database.sql.gz').write_bytes(b'corrupted')
            self.assertNotEqual(check(), 0)
            (folder/'manifest.txt').unlink()
            self.assertNotEqual(check(), 0)

    def test_workflow_conditions_and_unchanged_forensics_product_backup(self):
        source = (ROOT/'.github/workflows/deploy-reg-ru-staging-wordpress.yml').read_text()
        import re
        conditions = dict(re.findall(r'^  ([\w-]+):\n    if: (.+)$', source, re.M))
        for event in ('push', 'workflow_dispatch'):
            for operation in ('deploy','release-resume','release-inspect','catalog-maintenance'):
                for branch in (resume.BRANCH,'main'):
                    for job, condition in conditions.items():
                        expr = condition.replace('&&',' and ').replace('||',' or ')
                        for name, value in {'github.event_name':event,'inputs.operation':operation,'github.ref_name':branch}.items():
                            expr = expr.replace(name, repr(value))
                        actual = eval(expr, {'__builtins__': {}})
                        expected = (event=='push' or operation=='deploy') if job=='deploy' else (
                            event=='workflow_dispatch' and operation==job and branch==resume.BRANCH)
                        self.assertEqual(actual, expected)
        push = source.split('  push:',1)[1].split('  workflow_dispatch:',1)[0]
        self.assertNotIn(resume.BRANCH, push)
        block = source.split('\n  release-resume:',1)[1]
        self.assertNotIn('${{ github.sha }}', block)
        self.assertNotIn('if: always()', block)
        self.assertIn('ROLLSBAR_RELEASE_SHA: ${{ inputs.release_sha }}', block)
        self.assertIn('fetch-depth: 0', block)
        for path in ['wordpress/deploy/inspect_staging_release.py','wordpress/deploy/backup-staging.sh',
                     'wordpress/deploy/prepare-s1-r2-backup.sh','wordpress/deploy/bootstrap-staging.sh',
                     'wordpress/deploy/deploy_staging_wordpress.py','wordpress/data/catalog.json',
                     *['wordpress/wp-content/plugins/rollsbar-core/assets/'+asset for asset in resume.ASSETS.values()]]:
            self.assertEqual((ROOT/path).read_bytes().replace(b'\r\n',b'\n'),
                             subprocess.check_output(['git','show',resume.RELEASE+':'+path],cwd=ROOT))
        self.assertNotIn('git checkout', seo.mutation_script(resume.RELEASE,'YES'))
        self.assertNotIn('git clone', seo.mutation_script(resume.RELEASE,'YES'))


if __name__ == '__main__':
    unittest.main(verbosity=2)

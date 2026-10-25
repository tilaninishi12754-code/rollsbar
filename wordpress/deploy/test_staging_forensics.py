"""Deterministic atomic forensic evidence, redaction, and retry-safety tests."""
from contextlib import redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import inspect_staging_release as recovery


def fixture_report(head=None, marker=None, asset=None, fresh=False, partial=''):
    hashes={recovery.OLD:{'css/checkout.css':'a'*64,'js/checkout.js':'b'*64},recovery.INCOMING:{'css/checkout.css':'c'*64,'js/checkout.js':'d'*64}}
    hashes[recovery.TOOLING]=dict(hashes[recovery.INCOMING])
    marker=marker or recovery.OLD
    values={'ssh_exec':'SSH_EXEC_OK','marker_object':'regular|600|41','marker_value':marker,'marker_mode':'600',
            'repo_exists':'present','repo_head':head or recovery.OLD,'repo_status':'','wp_exists':'present',
            'home':'https://staging.rollsbar.ru','siteurl':'https://staging.rollsbar.ru','environment':'staging',
            'wordpress_version':'7.1.3','woocommerce_version':'11.1.2','theme_status':'active',
            'rollsbar_core_status':'active','blog_public':'0','backup_root':'directory|700|4096',
            'backup_names':recovery.PROTECTED+'\n'+recovery.KNOWN_LATEST,'protected_snapshot':'complete\ndatabase.sql.gz: OK\nuploads.tar.gz: OK\nmanifest.txt: OK',
            'new_snapshot_candidates':'','backup_lock':'absent','backup_tmp_dirs':partial,'runtime_object':'absent'}
    for key,a in [('checkout_css','css/checkout.css'),('checkout_js','js/checkout.js')]:values[key]=hashes[asset or recovery.OLD][a]
    catalog={'host':'staging.rollsbar.ru','environment':'staging','deployed_sha':marker,
             'canonical_count':118,'canonical_missing':0,'canonical_duplicates':0,'canonical_marked_upsell':0,
             'canonical_wrong_status':0,'variable_parents':13,'variations':26,'actual_variation_posts':26,
             'variation_mismatches':0,'blank_variation_attributes':0,'upsell_count':3,'upsell_duplicates':0,
             'upsell_identity_mismatches':0,'wrong_upsell_type':0,'wrong_upsell_visibility':0,
             'wrong_upsell_status':0,'missing_provisional_provenance':0,'published_total':121,
             'unexpected_published_products':0,'upsell_source_ids':['upsell-soy-sauce','upsell-ginger','upsell-wasabi']}
    values['catalog_audit']=json.dumps(catalog)
    if fresh:
        values['backup_names']+='\n20261025T200050Z'
        values['new_snapshot_candidates']='20261025T200050Z'
    for name in values['backup_names'].splitlines():
        values['snapshot_complete_'+name]='complete'
        values['snapshot_verify_'+name]='complete\ndatabase.sql.gz: OK\nuploads.tar.gz: OK\nmanifest.txt: OK'
        values['snapshot_manifest_'+name]='created_utc='+name+'\nproject_code_commit='+recovery.OLD+'\nsite_url=https://staging.rollsbar.ru\nwordpress_version=7.1.3\nwoocommerce_version=11.1.2\npublished_products=121'
    cleanup=[{'name':recovery.RUNTIME_FILE,'before':{'exists':False},'after':{'exists':False}}]
    values['runtime_cleanup']=json.dumps(cleanup)
    return {'probes':[{'name':name,'status':'PASS','exit_code':0,'stdout':value,'stderr':'','exception_type':None,'truncated':False} for name,value in values.items()],
            'runtime_cleanup':cleanup,'expected_hashes':hashes}


class AtomicForensics(unittest.TestCase):
    def test_independent_failures_preserve_labels_and_collect_every_later_probe(self):
        cases={'marker_object':['repo_head','home','checkout_css','backup_names','catalog_audit'],
               'repo_head':['home','checkout_css','backup_names','catalog_audit'],
               'home':['checkout_css','backup_names','catalog_audit'],
               'checkout_css':['backup_names','catalog_audit']}
        for failure,later in cases.items():
            called=[]
            def runner(name,cmd):
                called.append(name)
                return {'name':name,'status':'FAIL' if name==failure else 'PASS','exit_code':17 if name==failure else 0,
                        'stdout':'','stderr':'exact diagnostic' if name==failure else '', 'exception_type':None}
            with redirect_stdout(io.StringIO()):report=recovery.collect(runner,cleanup=lambda:fixture_report()['runtime_cleanup'])
            for name in later:self.assertGreater(called.index(name),called.index(failure))
            row=next(r for r in report['probes'] if r['name']==failure)
            self.assertEqual((row['status'],row['exit_code'],row['stderr']),('FAIL',17,'exact diagnostic'))
            self.assertNotIn('classification',report)

    def test_execute_preserves_nonzero_stdout_stderr_exit_and_fresh_transport(self):
        client=Mock();out=Mock();err=Mock()
        out.read.return_value=b'partial fact\n';err.read.return_value=b'fatal: not a git repository\n'
        out.channel.recv_exit_status.return_value=128
        client.exec_command.return_value=(Mock(),out,err)
        factory=Mock(return_value=client)
        row=recovery.execute('repo_head','git fixed read-only fixture',factory)
        self.assertEqual(row['status'],'FAIL');self.assertEqual(row['name'],'repo_head')
        self.assertEqual(row['exit_code'],128)
        self.assertIn('not a git repository',row['stderr'])
        self.assertEqual(row['stdout'],'partial fact')
        client.open_sftp.assert_not_called();client.close.assert_called_once();factory.assert_called_once()

    def test_stderr_bounded_and_secret_patterns_redacted_before_truncation(self):
        client=Mock();out=Mock();err=Mock()
        out.read.return_value=b'normal fact'
        err.read.return_value=('password=VERY_PRIVATE\napi key: HIDDEN\nDB_USER=OWNER\nTelegram HIDDEN\nDaData HIDDEN\nsecret token HIDDEN\n'+('safe diagnostic\n'*900)).encode()
        out.channel.recv_exit_status.return_value=1
        client.exec_command.return_value=(Mock(),out,err)
        row=recovery.execute('home','fixed',lambda:client)
        self.assertLessEqual(len(row['stderr']),recovery.LIMIT)
        self.assertTrue(row['truncated']);self.assertEqual(row['status'],'FAIL')
        self.assertNotIn('VERY_PRIVATE',row['stderr']);self.assertNotIn('HIDDEN',row['stderr'])
        self.assertNotIn('OWNER',row['stderr']);self.assertIn('safe diagnostic',row['stderr'])

    def test_environment_values_and_exception_messages_redacted(self):
        client=Mock();client.exec_command.side_effect=EOFError('sensitive-value')
        with patch.dict(os.environ,{'ISP_MANAGER_PASSWORD':'sensitive-value'}):row=recovery.execute('marker_value','fixed',lambda:client)
        self.assertEqual(row['exception_type'],'EOFError');self.assertEqual(row['name'],'marker_value')
        self.assertNotIn('sensitive-value',json.dumps(row))

    def test_no_validation_before_collection_and_classification(self):
        sequence=[]
        fixture=fixture_report()
        rows={r['name']:r for r in fixture['probes']}
        def runner(name,cmd):sequence.append(name);return copy.deepcopy(rows[name])
        with redirect_stdout(io.StringIO()), patch.object(recovery,'normalize_validate_classify',side_effect=AssertionError('too early')):
            report=recovery.collect(runner,cleanup=lambda:fixture['runtime_cleanup'])
        self.assertIn('catalog_audit',sequence)
        report['expected_hashes']=fixture['expected_hashes']
        self.assertEqual(recovery.normalize_validate_classify(report)['SAFE_FOR_NEW_DEPLOY_RETRY'],'YES')

    def test_missing_failed_or_truncated_probe_cannot_be_safe(self):
        for name in ['marker_value','repo_head','home','checkout_css','backup_names','catalog_audit','protected_snapshot','runtime_cleanup']:
            for change in ['missing','failed','truncated']:
                report=fixture_report()
                row=next(r for r in report['probes'] if r['name']==name)
                if change=='missing':report['probes'].remove(row)
                elif change=='failed':row['status']='FAIL'
                else:row['truncated']=True
                self.assertEqual(recovery.normalize_validate_classify(report)['SAFE_FOR_NEW_DEPLOY_RETRY'],'NO',(name,change))

    def test_mixed_css_js_and_marker_disagreement_block(self):
        report=fixture_report()
        next(r for r in report['probes'] if r['name']=='checkout_js')['stdout']='d'*64
        result=recovery.normalize_validate_classify(report)
        self.assertEqual(result['classification'],'MIXED_ASSET_STATE');self.assertEqual(result['SAFE_FOR_NEW_DEPLOY_RETRY'],'NO')
        report=fixture_report();next(r for r in report['probes'] if r['name']=='marker_value')['stdout']=recovery.INCOMING
        result=recovery.normalize_validate_classify(report)
        self.assertIn('marker changed between independent reads',result['validation_issues'])

    def test_runtime_absent_confirmed_and_cleanup_error_blocks(self):
        result=recovery.normalize_validate_classify(fixture_report())
        self.assertEqual(result['result'],'PASS');self.assertEqual(result['runtime_cleanup'][0]['before'],{'exists':False})
        with redirect_stdout(io.StringIO()):
            report=recovery.collect(lambda name,cmd:{'name':name,'status':'FAIL','exit_code':None,'stdout':'','stderr':'','exception_type':'EOFError'},cleanup=Mock(side_effect=ValueError('unsafe object')))
        row=next(r for r in report['probes'] if r['name']=='runtime_cleanup')
        self.assertEqual(row['status'],'FAIL');self.assertEqual(row['exception_type'],'ValueError')

    def test_known_hashes_include_infrastructure_revision_same_product(self):
        hashes=recovery.expected_hashes()
        self.assertEqual(hashes[recovery.INCOMING],hashes[recovery.TOOLING])
        self.assertNotEqual(hashes[recovery.OLD],hashes[recovery.INCOMING])

    def test_full_probe_session_uses_one_new_client_per_fact(self):
        clients=[]
        def connector():
            client=Mock();out=Mock();err=Mock()
            out.read.return_value=b'fact';err.read.return_value=b''
            out.channel.recv_exit_status.return_value=0
            client.exec_command.return_value=(Mock(),out,err)
            clients.append(client)
            return client
        recovery.execute('home','fixed home fixture',connector)
        recovery.execute('siteurl','fixed siteurl fixture',connector)
        self.assertEqual(len(clients),2)
        self.assertIsNot(clients[0],clients[1])
        for client in clients:
            client.open_sftp.assert_not_called();client.exec_command.assert_called_once();client.close.assert_called_once()

    def test_large_fixed_catalog_command_flushes_stdin(self):
        client=Mock();stdin=Mock();out=Mock();err=Mock()
        out.read.return_value=b'{}';err.read.return_value=b''
        out.channel.recv_exit_status.return_value=0
        client.exec_command.return_value=(stdin,out,err)
        result=recovery.execute('catalog_audit','x'*4096,lambda:client)
        self.assertEqual(result['status'],'PASS')
        request=client.exec_command.call_args.args[0]
        self.assertEqual(request,"bash -lc 'exec bash -s'")
        self.assertNotIn(recovery.AUDIT_PHP,request)
        self.assertGreater(len(recovery.PREFIX+recovery.AUDIT_PHP+'\n'),2048)
        stdin.write.assert_called_once();stdin.flush.assert_called_once();stdin.channel.shutdown_write.assert_called_once()

    def test_login_path_bug_reproduction_and_fixed_large_probe(self):
        bash='C:/programm/Git/bin/bash.exe' if os.name=='nt' else 'bash'
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); bindir=home/'login-bin';bindir.mkdir()
            wp=bindir/'wp'
            wp.write_text('#!/usr/bin/env bash\nprintf "FAKE_WP_PATH\\n"\n',encoding='utf-8')
            if os.name=='nt':
                converted=subprocess.check_output(['C:/programm/Git/usr/bin/cygpath.exe','-u',str(bindir)],text=True).strip()
            else:converted=str(bindir)
            profile=home/'.bash_profile'
            profile.write_text('export PATH='+shlex.quote(converted)+':$PATH\n',encoding='utf-8')
            env={**os.environ,'HOME':str(home)}
            small=subprocess.run([bash,'-lc','command -v wp'],env=env,text=True,capture_output=True,timeout=10)
            self.assertEqual(small.returncode,0,small.stderr)
            self.assertEqual(Path(small.stdout.strip()).name,'wp')
            old=subprocess.run([bash,'-s'],input='command -v wp\n',env=env,text=True,capture_output=True,timeout=10)
            self.assertNotEqual(old.returncode,0)
            self.assertEqual(old.stdout,'')
            fixed=subprocess.run([bash,'-lc','exec bash -s'],input='command -v wp\n',env=env,text=True,capture_output=True,timeout=10)
            self.assertEqual(fixed.returncode,0,fixed.stderr)
            self.assertEqual(Path(fixed.stdout.strip()).name,'wp')
            self.assertEqual(Path(small.stdout.strip()),Path(fixed.stdout.strip()))

    def test_large_execution_request_does_not_embed_audit_and_preserves_diagnostics(self):
        client=Mock();stdin=Mock();out=Mock();err=Mock()
        out.read.return_value=b'wp-path\n';err.read.return_value=b'controlled stderr\n'
        out.channel.recv_exit_status.return_value=7
        client.exec_command.return_value=(stdin,out,err)
        result=recovery.execute('catalog_audit',recovery.AUDIT_PHP,lambda:client)
        request=client.exec_command.call_args.args[0]
        self.assertEqual(request,"bash -lc 'exec bash -s'")
        self.assertNotIn(recovery.AUDIT_PHP,request)
        stdin.write.assert_called_once_with(recovery.PREFIX+recovery.AUDIT_PHP+'\n')
        stdin.flush.assert_called_once();stdin.channel.shutdown_write.assert_called_once()
        self.assertEqual((result['status'],result['exit_code'],result['stdout'],result['stderr']),
                         ('FAIL',7,'wp-path','controlled stderr'))
        client.close.assert_called_once()

    def test_atomic_commands_are_individually_named_and_read_only(self):
        probes=recovery.base_probes()
        names=[n for n,_ in probes]
        self.assertEqual(len(names),len(set(names)))
        self.assertGreaterEqual(len(names),26)
        for name,cmd in probes:
            self.assertNotRegex(cmd,r'\b(?:rm|mv|cp|chmod|chown|mkdir|touch)\b')
        self.assertIn('marker_value',names);self.assertIn('checkout_js',names);self.assertIn('catalog_audit',names)


if __name__=='__main__':unittest.main(verbosity=2)

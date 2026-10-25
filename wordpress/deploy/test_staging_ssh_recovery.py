"""Offline SSH lifecycle, recovery scope, and no-retry failure contracts."""
import ast
from contextlib import redirect_stdout
import importlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import staging_ssh as ssh
import inspect_staging_release as recovery
with patch.dict(sys.modules, {'paramiko': SimpleNamespace(SSHException=type('SSHException', (Exception,), {}))}):
    deploy = importlib.import_module('deploy_staging_wordpress')


class FakeSFTP:
    def __init__(self, files, events):
        self.files, self.events = files, events
    def normalize(self, path):
        return '/home/fixture'
    def lstat(self, path):
        if path not in self.files: raise FileNotFoundError(path)
        mode, body = self.files[path]
        return SimpleNamespace(st_mode=mode, st_size=len(body))
    def open(self, path, mode):
        self.events.append(('open', path, mode))
        if mode != 'wx': raise AssertionError('Secret contents must never be read in cleanup')
        if path in self.files: raise FileExistsError(path)
        self.files[path] = (stat.S_IFREG | 0o600, b'')
        owner = self
        class Stream:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def write(self, body): owner.files[path] = (owner.files[path][0], body)
        return Stream()
    def chmod(self, path, mode): self.files[path] = (stat.S_IFREG | mode, self.files[path][1])
    def remove(self, path):
        self.events.append(('remove', path)); del self.files[path]
    def close(self): self.events.append(('sftp_close',))


class Client:
    def __init__(self, name, files, events, error=None):
        self.name, self.files, self.events, self.error = name, files, events, error
    def open_sftp(self):
        self.events.append(('sftp', self.name)); return FakeSFTP(self.files, self.events)
    def close(self): self.events.append(('close', self.name))
    def get_transport(self): return SimpleNamespace(is_active=lambda: True)
    def exec_command(self, command, timeout):
        self.events.append(('exec', self.name, command))
        if self.error: raise self.error
        out = Mock(); out.read.return_value = b'{}'; out.channel.recv_exit_status.return_value = 0
        err = Mock(); err.read.return_value = b''
        return Mock(), out, err


class TransportContracts(unittest.TestCase):
    def setUp(self):
        self.files, self.events = {}, []

    def run_deploy(self, error=None, cleanup_error=None):
        a = Client('A', self.files, self.events)
        b = Client('B', self.files, self.events, error)
        c = Client('C', self.files, self.events)
        factory = Mock(side_effect=[a, b, cleanup_error if cleanup_error else c])
        data = {'db_name':'fixture-db','db_user':'fixture-user','db_password':'PRIVATE_DB_FIXTURE',
                'db_host':'localhost','wp_admin_password':'PRIVATE_ADMIN_FIXTURE'}
        buf = io.StringIO()
        with patch.object(deploy, 'read_secrets', return_value=data), patch.object(deploy, 'mask_dynamic_secrets'), patch.object(deploy, 'validate_catalog_audit'), patch.object(deploy, 'DEPLOY_SHA', 'a'*40), redirect_stdout(buf):
            result = deploy.run_deploy(factory)
        return result, buf.getvalue(), factory

    def test_three_transports_short_exec_and_independent_cleanup(self):
        result, output, factory = self.run_deploy()
        self.assertEqual(result, 0)
        self.assertEqual(factory.call_count, 3)
        calls = [e for e in self.events if e[0]=='exec']
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 'B')
        self.assertLess(len(calls[0][2]), 160)
        self.assertTrue(calls[0][2].startswith('bash /home/fixture/.rollsbar-staging-deploy-'))
        self.assertLess(self.events.index(('close','A')), self.events.index(calls[0]))
        self.assertNotIn(('sftp','B'), self.events)
        self.assertIn(('sftp','C'), self.events)
        self.assertEqual(self.files, {})
        self.assertIn('"exists": false', output)

    def test_ambiguous_eof_sanitized_no_retry_and_both_files_cleaned(self):
        result, output, factory = self.run_deploy(EOFError('PRIVATE_DB_FIXTURE'))
        self.assertEqual(result, 1)
        self.assertIn('stage=exec_request type=EOFError state_ambiguous=true', output)
        self.assertIn('mutating_exec_retry=no', output)
        self.assertNotIn('PRIVATE_DB_FIXTURE', output)
        self.assertEqual(len([e for e in self.events if e[0]=='exec']), 1)
        removed = [e[1] for e in self.events if e[0]=='remove']
        self.assertEqual(len(removed), 2)
        self.assertIn('/home/fixture/'+ssh.RUNTIME_FILE, removed)
        self.assertEqual(self.files, {})
        self.assertEqual(factory.call_count,3)

    def test_other_transport_errors_fail_closed_without_retry(self):
        for error in [deploy.paramiko.SSHException('PRIVATE_DB_FIXTURE'), OSError('PRIVATE_DB_FIXTURE')]:
            self.setUp()
            result, output, _ = self.run_deploy(error)
            self.assertEqual(result,1)
            self.assertNotIn('PRIVATE_DB_FIXTURE',output)
            self.assertEqual(len([e for e in self.events if e[0]=='exec']),1)

    def test_cleanup_failure_is_structured_not_swallowed(self):
        result, output, factory = self.run_deploy(EOFError(), OSError('PRIVATE_DB_FIXTURE'))
        self.assertEqual(result,1)
        self.assertIn('stage=cleanup type=OSError',output)
        self.assertNotIn('PRIVATE_DB_FIXTURE',output)
        self.assertEqual(factory.call_count,3)

    def test_cleanup_refuses_symlink_directory_and_bad_modes(self):
        for mode in [stat.S_IFLNK|0o600,stat.S_IFDIR|0o600,stat.S_IFREG|0o644,stat.S_IFREG|0o777]:
            self.setUp()
            path='/home/fixture/'+ssh.RUNTIME_FILE
            self.files[path]=(mode,b'PRIVATE_BODY')
            connector=Mock(return_value=Client('C',self.files,self.events))
            with redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError): ssh.cleanup_files([ssh.RUNTIME_FILE],connector)
            self.assertIn(path,self.files)
            self.assertFalse(any(e[0] in ('open','remove') for e in self.events))

    def test_cleanup_regular_600_metadata_only_and_exact_scope(self):
        path='/home/fixture/'+ssh.RUNTIME_FILE
        self.files[path]=(stat.S_IFREG|0o600,b'PRIVATE_BODY')
        self.files['/home/fixture/other']=(stat.S_IFREG|0o600,b'keep')
        connector=Mock(return_value=Client('C',self.files,self.events))
        with redirect_stdout(io.StringIO()) as buf: rows=ssh.cleanup_files([ssh.RUNTIME_FILE],connector)
        self.assertFalse(rows[0]['after']['exists'])
        self.assertEqual(rows[0]['before']['mode'],'0o600')
        self.assertNotIn('PRIVATE_BODY',buf.getvalue())
        self.assertIn('/home/fixture/other',self.files)
        self.assertFalse(any(e[0]=='open' for e in self.events))
        for name in ['../'+ssh.RUNTIME_FILE,'/tmp/'+ssh.RUNTIME_FILE,'unknown','x.sh']:
            with self.assertRaises(ValueError): ssh.safe_path(FakeSFTP(self.files,self.events),name)

    def test_exclusive_prepare_never_overwrites_stale_secret(self):
        path='/home/fixture/'+ssh.RUNTIME_FILE
        self.files[path]=(stat.S_IFREG|0o600,b'old')
        created=[]
        with self.assertRaises(FileExistsError): ssh.write_new(FakeSFTP(self.files,self.events),ssh.RUNTIME_FILE,b'new',0o600,created)
        self.assertEqual(created,[])
        self.assertEqual(self.files[path][1],b'old')

    def test_script_contains_no_runtime_credentials_and_preserves_shell_order(self):
        with patch.object(deploy,'DEPLOY_SHA','a'*40), patch.object(deploy,'DADATA_API_KEY','PRIVATE_API_FIXTURE'), patch.object(deploy,'PASSWORD','PRIVATE_PASSWORD_FIXTURE'):
            script=deploy.build_remote_script()
        for secret in ['PRIVATE_API_FIXTURE','PRIVATE_PASSWORD_FIXTURE','PRIVATE_DB_FIXTURE','PRIVATE_ADMIN_FIXTURE']:
            self.assertNotIn(secret,script)
        self.assertIn('"$RUNTIME" "$0"',script)
        self.assertIn('trap cleanup EXIT',script)
        self.assertIn('a'*40,script)
        self.assertLess(script.index('prepare-s1-r2-backup.sh'),script.index('bootstrap-staging.sh'))
        scripts=[script,recovery.IDENTITY,recovery.ASSETS,recovery.BACKUPS,recovery.PREFIX+'wp --path="$WP_PATH" eval '+__import__('shlex').quote(recovery.AUDIT_PHP)]
        for body in scripts:
            bash='C:/programm/Git/bin/bash.exe' if os.name=='nt' else 'bash'
            result=subprocess.run([bash,'-n'],input=body,text=True,encoding='utf-8',capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_probe_uses_fresh_exec_only_and_stops_on_eof(self):
        client=Client('probe',self.files,self.events,EOFError())
        with self.assertRaises(EOFError):ssh.probe(lambda:client)
        self.assertEqual(self.events[0],('exec','probe',"printf 'SSH_EXEC_OK\\n'"))
        self.assertNotIn(('sftp','probe'),self.events)
        self.assertEqual(self.events[-1],('close','probe'))

    def test_inspection_exec_uses_stdin_and_no_sftp(self):
        client=Client('inspect',self.files,self.events)
        self.assertEqual(recovery.execute('read-only fixture',lambda:client),'{}')
        self.assertIn(('exec','inspect','bash -s'),self.events)
        self.assertNotIn(('sftp','inspect'),self.events)

    def test_probe_failure_prevents_inspection_and_cleanup(self):
        with patch.dict(os.environ,{'GITHUB_REF_NAME':recovery.BRANCH}), patch.object(recovery,'probe',side_effect=EOFError('PRIVATE')), patch.object(recovery,'execute') as execute, patch.object(recovery,'cleanup_files') as cleanup, redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(recovery.main(),1)
        execute.assert_not_called();cleanup.assert_not_called()
        self.assertIn('stage=exec_probe type=EOFError',buf.getvalue())
        self.assertNotIn('PRIVATE',buf.getvalue())

    def test_inspection_is_nonmutating_and_runtime_only_cleanup(self):
        scripts=recovery.IDENTITY+recovery.ASSETS+recovery.BACKUPS
        self.assertNotRegex(scripts,r'\b(?:rm|mv|cp|chmod|chown|mkdir|touch)\b')
        self.assertNotRegex(scripts,r'git[^\n]*(?:fetch|checkout|reset)')
        self.assertNotRegex(scripts,r'wp[^\n]*(?:update|import|repair|delete)')
        source=Path(recovery.__file__).read_text(encoding='utf-8-sig')
        self.assertIn('cleanup_files([RUNTIME_FILE])',source)
        self.assertNotIn('write_runtime_env',source)
        self.assertNotIn('db export',source)
        self.assertNotIn('.open(',source)

    def test_protected_product_backup_catalog_marker_unchanged(self):
        paths=['wordpress/wp-content','wordpress/data','wordpress/deploy/backup-staging.sh',
               'wordpress/deploy/prepare-s1-r2-backup.sh','wordpress/deploy/staging_catalog_audit.py',
               'wordpress/deploy/mark_staging_deployed_sha.py']
        result=subprocess.run(['git','diff','--exit-code',recovery.INCOMING,'--',*paths],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout)

    def test_workflow_modes_exclusive_branch_pinned_marker_later(self):
        source=(ROOT/'.github/workflows/deploy-reg-ru-staging-wordpress.yml').read_text()
        self.assertIn("inputs.operation == 'deploy')",source)
        self.assertIn("inputs.operation == 'catalog-maintenance' &&",source)
        self.assertIn("inputs.operation == 'release-inspect' && github.ref_name == '"+recovery.BRANCH+"'",source)
        recovery_job=source.split('\n  release-inspect:\n',1)[1]
        self.assertIn('name: staging',recovery_job)
        self.assertNotIn('run: python3 wordpress/deploy/deploy_staging_wordpress.py',recovery_job)
        self.assertNotIn('maintain_staging_catalog.py',recovery_job)
        self.assertNotIn('ROLLSBAR_DADATA_API_KEY',recovery_job)
        order=[source.index('run: python3 wordpress/deploy/'+n+'.py') for n in ['deploy_staging_wordpress','provision_staging_seo','harden_staging_http','audit_staging_seo','mark_staging_deployed_sha']]
        self.assertEqual(order,sorted(order))
        conditions=dict(re.findall(r"(?m)^  ([a-z-]+):\n    if: (.+)$",source))
        for branch in [recovery.BRANCH,'other']:
            for job,condition in conditions.items():
                expr=condition.replace('github.event_name',repr('workflow_dispatch')).replace('inputs.operation',repr('release-inspect')).replace('github.ref_name',repr(branch)).replace('||',' or ').replace('&&',' and ')
                enabled=eval(expr,{'__builtins__':{}})
                self.assertEqual(enabled,job=='release-inspect' and branch==recovery.BRANCH)


    def forensic(self, head=None, marker=None, asset=None, fresh=False, partial=''):
        head=head or recovery.OLD
        marker=marker or recovery.OLD
        identity='marker='+marker+'\nrepo_head='+head+'\nrepo_status_begin\nrepo_status_end\n'
        identity+='home=https://staging.rollsbar.ru\nsiteurl=https://staging.rollsbar.ru\nenvironment=staging\nwordpress=7.1.3\nwoocommerce=11.1.2\ntheme=active\nplugin=active\nblog_public=0\n'
        expected={recovery.OLD:{'css/checkout.css':'a'*64,'js/checkout.js':'b'*64},recovery.INCOMING:{'css/checkout.css':'c'*64,'js/checkout.js':'d'*64}}
        assets=''.join('asset='+a+' sha256='+h+'\n' for a,h in expected[asset or recovery.OLD].items())
        stamp='20261025T200050Z'
        backups='backup_names_begin\n'+recovery.PROTECTED+'\n20261025T151212Z\n'+(stamp+'\n' if fresh else '')+'backup_names_end\nbackup_partial_names_begin\n'+partial+'backup_partial_names_end\n'
        backups+='snapshot_verified='+recovery.PROTECTED+'\n'
        if fresh:backups+='snapshot_begin='+stamp+'\nproject_code_commit='+recovery.OLD+'\nsnapshot_verified='+stamp+'\nsnapshot_end='+stamp+'\n'
        return {'identity':identity,'assets':assets,'backups':backups,'expected_hashes':expected}

    def test_classification_uses_marker_repo_assets_and_backup_together(self):
        self.assertEqual(recovery.classify(self.forensic()),'EXEC_NOT_OBSERVED')
        self.assertEqual(recovery.classify(self.forensic(head=recovery.INCOMING)),'PRE_BACKUP_PARTIAL')
        self.assertEqual(recovery.classify(self.forensic(head=recovery.INCOMING,fresh=True)),'BACKUP_COMPLETED_PRE_BOOTSTRAP')
        self.assertEqual(recovery.classify(self.forensic(marker=recovery.INCOMING,asset=recovery.INCOMING)),'UNKNOWN_PARTIAL_STATE')
        self.assertEqual(recovery.classify(self.forensic(asset=recovery.INCOMING)),'UNKNOWN_PARTIAL_STATE')
        self.assertEqual(recovery.classify(self.forensic(head='f'*40)),'UNKNOWN_PARTIAL_STATE')

    def test_lock_temp_corrupt_backup_and_wrong_identity_block(self):
        for partial in ['.backup-staging.lock\n','.tmp-20261025T200050Z-12\n']:
            with self.assertRaises(ValueError):recovery.classify(self.forensic(partial=partial))
        row=self.forensic();row['backups']=row['backups'].replace('snapshot_verified=','missing=')
        with self.assertRaises(ValueError):recovery.classify(row)
        row=self.forensic();row['identity']=row['identity'].replace('environment=staging','environment=production')
        with self.assertRaises(ValueError):recovery.classify(row)
        row=self.forensic();row['assets']=row['assets'].replace('a'*64,'e'*64)
        self.assertEqual(recovery.classify(row),'UNKNOWN_PARTIAL_STATE')

    def test_remote_stdout_eof_reports_remote_execution_no_retry(self):
        original=Client.exec_command
        def remote_eof(client,command,timeout):
            stdin,out,err=original(client,command,timeout)
            out.read.side_effect=EOFError('PRIVATE_DB_FIXTURE')
            return stdin,out,err
        with patch.object(Client,'exec_command',remote_eof):
            result,output,factory=self.run_deploy()
        self.assertEqual(result,1)
        self.assertIn('stage=remote_execution type=EOFError state_ambiguous=true',output)
        self.assertNotIn('PRIVATE_DB_FIXTURE',output)
        self.assertEqual(factory.call_count,3)
        self.assertEqual(len([e for e in self.events if e[0]=='exec']),1)


if __name__=='__main__':unittest.main(verbosity=2)

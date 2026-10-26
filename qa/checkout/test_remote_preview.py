"""Focused offline contracts for the existing workflow's shadow-preview extension."""
import ast
from pathlib import Path
import re
import unittest
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
from release_gate import (AssetIdentity, ASSETS, FEATURE, dispatch_policy, install_asset_routes, release_assets)

ROOT=Path(__file__).resolve().parents[2]
tree=ast.parse((ROOT/'qa/repair/s1_r3q_release_read.py').read_text(encoding='utf-8'))
# Exercise the real command builder without importing SSH dependencies locally.
builder=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='marker_command')
namespace={'re':re}
exec(compile(ast.Module(body=[builder],type_ignores=[]),'marker_command','exec'),namespace)
marker_command=namespace['marker_command']


class RemotePreviewContracts(unittest.TestCase):
    def test_marker_override_is_literal_sha_and_read_only(self):
        for sha in ['88826907fc7ffe805a7c47f36c35a74c0049e08e','e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea']:
            command=marker_command(sha)
            self.assertIn('test "$marker" = '+sha,command)
            self.assertIn('cat "$HOME/.rollsbar-staging-deployed-sha"',command)
            self.assertNotIn('wp ',command)
            self.assertNotRegex(command,r'\b(?:rm|cp|mv|mkdir|tee)\b|>>?')
        for bad in ['', '8882690', 'A'*40, 'a'*40+';echo injection', 'a'*40+'\n']:
            with self.subTest(value=bad),self.assertRaises(ValueError):marker_command(bad)

    def test_workflow_keeps_gate_and_always_marker_and_artifacts(self):
        source=(ROOT/'.github/workflows/gate-b-browser.yml').read_text(encoding='utf-8')
        self.assertEqual(source.count('run: python3 wordpress/deploy/gate_b_browser.py'),1)
        self.assertEqual(source.count('run: python3 qa/repair/s1_r3q_release_read.py'),2)
        self.assertIn("if: always() && env.ROLLSBAR_QA_EXPECTED_MARKER != ''",source)
        self.assertIn('uses: actions/upload-artifact@v4',source)
        self.assertIn('set -o pipefail',source)
        self.assertIn('python3 qa/checkout/shadow_preview.py',source)
        self.assertNotRegex(source,r'(?m)^  (?:push|schedule|workflow_run):')
        self.assertIn('deployment: false',source)


class LiveModeContracts(unittest.TestCase):
    SHA='a'*40
    BASE='https://staging.rollsbar.ru'

    def identity(self, changes=None, omit=None):
        expected={a:('release '+a).encode() for a in ASSETS}
        identity=AssetIdentity(expected,self.BASE)
        for a,body in expected.items():
            if a == omit: continue
            actual=(changes or {}).get(a,body)
            identity.observe(SimpleNamespace(url=self.BASE+'/wp-content/plugins/rollsbar-core/assets/'+a+'?ver=actual-customer-version',status=200,body=lambda b=actual:b))
        return identity

    def test_actual_served_bodies_match_both_git_assets(self):
        identity=self.identity()
        identity.verify([])
        self.assertEqual(len(identity.records),2)
        for row in identity.records:
            self.assertEqual(row['sha256'],row['expected_sha256'])
            self.assertGreater(row['bytes'],0)
            self.assertEqual(row['identity'],'PASS')

    def test_exact_targets_without_query_pass(self):
        expected={a:('release '+a).encode() for a in ASSETS}
        identity=AssetIdentity(expected,self.BASE)
        for asset,body in expected.items():
            identity.observe(SimpleNamespace(url=self.BASE+
                '/wp-content/plugins/rollsbar-core/assets/'+asset,
                status=200,body=lambda b=body:b))
        identity.verify([])

    def test_run_40274957719_woo_stylesheet_is_unrelated(self):
        identity=self.identity()
        body=Mock(return_value=b'normal WooCommerce checkout stylesheet')
        identity.observe(SimpleNamespace(url=self.BASE+
            '/wp-content/plugins/woocommerce/assets/client/blocks/checkout.css?ver=wc-11.1.2',
            status=200,body=body))
        identity.verify([])
        body.assert_not_called()
        self.assertEqual(len(identity.records),2)

    def test_theme_and_other_plugin_namesakes_are_ignored(self):
        for path in ('/theme/foo/checkout.css', '/other-plugin/checkout.js',
                     '/wp-content/plugins/rollsbar-core-other/assets/css/checkout.css'):
            identity=self.identity()
            body=Mock(side_effect=AssertionError('Unrelated response must not be read'))
            identity.observe(SimpleNamespace(url=self.BASE+path,status=200,body=body))
            identity.verify([])
            body.assert_not_called()

    def test_stale_css_and_js_fail(self):
        for a in ASSETS:
            with self.subTest(asset=a),self.assertRaises(AssertionError):
                self.identity({a:b'stale'}).verify([])

    def test_missing_css_and_js_fail(self):
        for a in ASSETS:
            with self.subTest(asset=a),self.assertRaises(AssertionError):
                self.identity(omit=a).verify([])

    def test_duplicate_wrong_origin_path_and_status_fail(self):
        for asset in ASSETS:
            for change in ('duplicate','origin','path','status'):
                identity=self.identity()
                row=next(row for row in identity.records if row['asset']==asset)
                url=row['url']
                if change=='origin': url=url.replace('staging.rollsbar.ru','wrong.test')
                if change=='path': url=url.replace('/assets/','/assets/wrong/')
                if change!='duplicate':
                    identity.records=[r for r in identity.records if r['asset']!=asset]
                identity.observe(SimpleNamespace(url=url,status=500 if change=='status' else 200,
                    body=lambda b=identity.expected[asset]:b))
                with self.subTest(asset=asset,change=change),self.assertRaises(AssertionError): identity.verify([])

    def test_response_body_error_fails(self):
        identity=self.identity()
        identity.observe(SimpleNamespace(url=identity.records[0]['url'],body=Mock(side_effect=RuntimeError('unreadable'))))
        with self.assertRaises(AssertionError): identity.verify([])

    def test_live_does_not_install_asset_routes_and_rejects_interception(self):
        page=Mock()
        substitute=Mock()
        install_asset_routes(page,True,substitute)
        page.route.assert_not_called()
        substitute.assert_not_called()
        with self.assertRaises(AssertionError): self.identity().verify([{'asset':'css/checkout.css'}])

    def test_shadow_installs_and_substitutes_both_assets(self):
        page=Mock()
        substitute=Mock()
        install_asset_routes(page,False,substitute)
        self.assertEqual(page.route.call_count,2)
        for call in page.route.call_args_list:
            route=Mock()
            call.args[1](route)
        self.assertEqual({call.args[1] for call in substitute.call_args_list},set(ASSETS))
        source=(ROOT/'qa/checkout/shadow_preview.py').read_text(encoding='utf-8')
        self.assertIn('CANDIDATE SHADOW PREVIEW — NOT DEPLOYED',source)
        self.assertIn("require(not live,'LIVE DEPLOYED forbids checkout asset substitution')",source)
        self.assertIn('route.fulfill(status=200,content_type=mime,body=body)',source)

    def test_explicit_marker_required_and_validated(self):
        for mode in ('shadow','live'):
            for bad in ('','main','a'*7,'A'*40,'a'*40+'\n','a'*40+';id','${SHA}'):
                with self.subTest(mode=mode,bad=bad),self.assertRaises(ValueError):
                    dispatch_policy(mode,bad,FEATURE)
        with self.assertRaises(ValueError): dispatch_policy('live','b'*40,FEATURE)
        with self.assertRaises(ValueError): dispatch_policy('oops',self.SHA,FEATURE)

    def test_explicit_live_uses_release_marker_not_historical(self):
        head=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        policy=dispatch_policy('live',head,FEATURE)
        self.assertEqual(policy['ROLLSBAR_QA_EXPECTED_MARKER'],head)
        self.assertEqual(policy['CHECKOUT_MODE'],'live')
        self.assertEqual(policy['ROLLSBAR_QA_VERIFY_HISTORICAL'],'0')
        with self.assertRaises(ValueError): release_assets('bad')
        with self.assertRaises(ValueError): release_assets(self.SHA)
        assets=release_assets(head)
        self.assertEqual(set(assets),set(ASSETS))
        for asset,body in assets.items():
            self.assertEqual(body,__import__('subprocess').check_output(['git','show',head+':wordpress/wp-content/plugins/rollsbar-core/assets/'+asset],cwd=ROOT))

    def test_historical_behavior_preserved(self):
        policy=dispatch_policy('historical','',FEATURE)
        self.assertEqual(policy['CHECKOUT_MODE'],'shadow')
        self.assertEqual(policy['ROLLSBAR_QA_EXPECTED_MARKER'],'88826907fc7ffe805a7c47f36c35a74c0049e08e')
        policy=dispatch_policy('historical','','refs/heads/other')
        self.assertEqual(policy['CHECKOUT_MODE'],'historical')
        self.assertEqual(policy['ROLLSBAR_QA_VERIFY_HISTORICAL'],'1')
        self.assertEqual(policy['ROLLSBAR_QA_EXPECTED_MARKER'],'e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea')
        with self.assertRaises(ValueError): dispatch_policy('historical',self.SHA,FEATURE)

    def test_workflow_marker_before_after_and_fail_closed(self):
        source=(ROOT/'.github/workflows/gate-b-browser.yml').read_text(encoding='utf-8')
        validation=source.index('run: python3 qa/checkout/release_gate.py')
        before=source.index('run: python3 qa/repair/s1_r3q_release_read.py')
        acceptance=source.index('run: python3 wordpress/deploy/gate_b_browser.py')
        live=source.index('python3 qa/checkout/shadow_preview.py --live-deployed')
        after=source.rindex('run: python3 qa/repair/s1_r3q_release_read.py')
        self.assertTrue(validation<before<acceptance<live<after)
        self.assertEqual(source.count('DISPATCH_MARKER: ${{ inputs.expected_marker }}'),1)
        self.assertNotIn('${{ inputs.expected_marker }}',source.split('run: python3 qa/checkout/release_gate.py')[1])
        self.assertIn('checkout-live-${{ github.run_id }}-${{ github.run_attempt }}',source)
        # Both reads execute the same immutable env and same validated command.
        command=marker_command(self.SHA)
        self.assertIn('test "$marker" = '+self.SHA,command)
        for phase in ('before','after'):
            for observed in (self.SHA,'b'*40):
                # Execute the actual reader entrypoint with a fake read-only SSH client.
                import importlib.util
                spec=importlib.util.spec_from_file_location('marker_reader',ROOT/'qa/repair/s1_r3q_release_read.py')
                reader=importlib.util.module_from_spec(spec)
                env={'ROLLSBAR_QA_EXPECTED_MARKER':self.SHA,'ISP_MANAGER_PASSWORD':'fixture','ISP_MANAGER_URL':'https://fixture.test','ISP_MANAGER_USER':'fixture'}
                with patch.dict('os.environ',env,clear=True), patch.dict(sys.modules,{'paramiko':Mock()}):
                    spec.loader.exec_module(reader)
                    client=Mock()
                    stdout=Mock()
                    stdout.read.return_value=('deployed_marker='+observed).encode()
                    stdout.channel.recv_exit_status.return_value=0 if observed==self.SHA else 1
                    stderr=Mock();stderr.read.return_value=b''
                    client.exec_command.return_value=(None,stdout,stderr)
                    with patch.object(reader.paramiko,'SSHClient',return_value=client):
                        if observed==self.SHA: reader.main()
                        else:
                            with self.assertRaises(RuntimeError):reader.main()
                    self.assertIn(self.SHA,client.exec_command.call_args.args[0])
                    client.close.assert_called_once()

    def test_accepted_product_backup_catalog_and_deploy_untouched(self):
        import subprocess
        result=subprocess.run(['git','diff','--exit-code','1ada44e5ee3df0eb708ad4575f6e3b2edfb4cd6a','--','wordpress','.github/workflows',':(exclude).github/workflows/gate-b-browser.yml'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_shared_assertions_cleanup_and_product_protection(self):
        source=(ROOT/'qa/checkout/shadow_preview.py').read_text(encoding='utf-8')
        gate=(ROOT/'wordpress/deploy/gate_b_browser.py').read_text(encoding='utf-8')
        self.assertIn('with isolated_browser_page(',source)
        self.assertIn('clean_test_cart(page)',gate)
        self.assertIn("ctx.route('**/*', lambda route: route.abort()",gate)
        self.assertIn('cta.click(trial=True)',source)
        self.assertIn('for width in [1440,1024,701,700,390,320]:',source)
        self.assertIn("if live: identity.verify(report['asset_substitutions'])",source)
        self.assertIn("live preserves the accepted 18 native controls",source)
        self.assertIn("live preserves eight required controls",source)
        self.assertIn('Live acceptance cannot skip checks with --map-only',source)


if __name__=='__main__':unittest.main()

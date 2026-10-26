"""Deterministic local Git histories; no browser, hosting or application mutation."""
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_gate as gate

START = '1ada44e5ee3df0eb708ad4575f6e3b2edfb4cd6a'
APPLICATION = '22aeb21783a79f8cb670a3371486fa0d17647b0b'
ROOT = gate.ROOT


class ReleaseHistory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git('init', '-q')
        self.expected = {asset: ('deployed '+asset+'\n').encode() for asset in gate.ASSETS}
        for asset, body in self.expected.items():
            path = self.repo / gate.ASSET_ROOT / asset
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        self.commit('application release')
        self.marker = self.git('rev-parse', 'HEAD').strip()
        self.root_patch = patch.object(gate, 'ROOT', self.repo)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'user.name=QA Fixture', '-c',
            'user.email=fixture@example.invalid', *args], cwd=self.repo, text=True,
            stderr=subprocess.PIPE)

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-qm', message)

    def test_equal_head_and_descendant_tooling_accept_fixed_application(self):
        for descendant in (False, True):
            if descendant:
                (self.repo/'qa.txt').write_text('new QA tooling')
                self.commit('tooling only')
                self.assertNotEqual(self.git('rev-parse','HEAD').strip(), self.marker)
            with self.subTest(descendant=descendant):
                policy = gate.dispatch_policy('live', self.marker, gate.FEATURE)
                self.assertEqual(policy['ROLLSBAR_QA_EXPECTED_MARKER'], self.marker)
                self.assertEqual(policy['CHECKOUT_MODE'], 'live')
                self.assertEqual(gate.release_assets(self.marker), self.expected)

    def test_head_product_change_cannot_redefine_application_truth(self):
        for asset in gate.ASSETS:
            (self.repo/gate.ASSET_ROOT/asset).write_bytes(b'different tooling checkout bytes')
        self.commit('fixture changed assets after application release')
        self.assertEqual(gate.release_assets(self.marker), self.expected)
        for asset, body in gate.release_assets(self.marker).items():
            self.assertNotEqual(body, (self.repo/gate.ASSET_ROOT/asset).read_bytes())

    def test_unrelated_and_future_commits_rejected(self):
        self.git('checkout', '-q', '--orphan', 'unrelated')
        (self.repo/'unrelated.txt').write_text('unrelated history')
        self.commit('unrelated root')
        unrelated = self.git('rev-parse', 'HEAD').strip()
        self.git('checkout', '-q', '--detach', self.marker)
        with self.assertRaises(ValueError): gate.dispatch_policy('live',unrelated,gate.FEATURE)
        with self.assertRaises(ValueError): gate.release_assets(unrelated)
        (self.repo/'future.txt').write_text('future')
        self.commit('future tooling')
        future = self.git('rev-parse','HEAD').strip()
        self.git('checkout','-q','--detach',self.marker)
        with self.assertRaises(ValueError): gate.release_assets(future)

    def test_invalid_unknown_and_noncommit_objects_rejected(self):
        tree = self.git('rev-parse','HEAD^{tree}').strip()
        for marker in ('', 'main', self.marker[:7], self.marker.upper(),
                       self.marker+'\n', self.marker+';id', 'f'*40, tree):
            with self.subTest(marker=marker):
                with self.assertRaises(ValueError): gate.dispatch_policy('live',marker,gate.FEATURE)
                with self.assertRaises(ValueError): gate.release_assets(marker)

    def test_shadow_does_not_gain_live_ancestry_constraint(self):
        policy = gate.dispatch_policy('shadow','f'*40,gate.FEATURE)
        self.assertEqual(policy['CHECKOUT_MODE'],'shadow')


class ActualReleaseContracts(unittest.TestCase):
    def test_baseline_reproduces_exact_woo_false_failure(self):
        source = subprocess.check_output(['git','show',START+':qa/checkout/release_gate.py'],
                                         cwd=ROOT,text=True)
        namespace = {'__name__':'baseline_gate','__file__':str(ROOT/'qa/checkout/release_gate.py')}
        exec(compile(source,'baseline_gate','exec'),namespace)
        identity = namespace['AssetIdentity']({asset:b'release' for asset in gate.ASSETS},
                                              'https://staging.rollsbar.ru')
        woo = 'https://staging.rollsbar.ru/wp-content/plugins/woocommerce/assets/client/blocks/checkout.css?ver=wc-11.1.2'
        identity.observe(SimpleNamespace(url=woo,status=200,body=lambda:b'normal Woo stylesheet'))
        with self.assertRaisesRegex(AssertionError,'Wrong checkout asset origin/path:'):
            identity.verify([])

    def test_feature_tooling_accepts_deployed_release_without_tag(self):
        policy = gate.dispatch_policy('live',APPLICATION,gate.FEATURE)
        self.assertEqual(policy['ROLLSBAR_QA_EXPECTED_MARKER'],APPLICATION)
        self.assertEqual(policy['ROLLSBAR_QA_VERIFY_HISTORICAL'],'0')
        for asset, body in gate.release_assets(APPLICATION).items():
            self.assertEqual(body,subprocess.check_output(['git','show',APPLICATION+':'+gate.ASSET_ROOT+asset],cwd=ROOT))

    def test_workflow_and_visual_harness_protected(self):
        source = (ROOT/'.github/workflows/gate-b-browser.yml').read_text()
        self.assertIn('uses: actions/checkout@v4\n        with:\n          fetch-depth: 0',source)
        self.assertIn('contents: read',source)
        self.assertIn('name: staging\n      deployment: false',source)
        self.assertNotIn('staging-checkout-v2-22aeb217',source)
        self.assertNotRegex(source,r'(?m)^  (push|schedule|workflow_run):')
        self.assertNotRegex(source,r'run:.*(?:deploy_staging|bootstrap|mark_staging|resume_staging)')
        for path in ['qa/checkout/shadow_preview.py','qa/repair/s1_r3q_release_read.py',
                     'wordpress/deploy/gate_b_browser.py']:
            self.assertEqual((ROOT/path).read_bytes().replace(b'\r\n',b'\n'),
                             subprocess.check_output(['git','show',START+':'+path],cwd=ROOT))


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Deterministic local PHP enqueue/hash contracts; no server or browser requests."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'qa/visual-results/asset-cache-busting'
BASE='5c5310070ef43d31b58d4e3c5973f0e1242ff52e'
THEME='wordpress/wp-content/themes/rollsbar-theme/'
PLUGIN='wordpress/wp-content/plugins/rollsbar-core/'
TARGETS={
 ('style','rollsbar-theme'):THEME+'style.css',
 ('style','rollsbar-app'):THEME+'assets/css/app.css',
 ('style','rollsbar-legal'):THEME+'assets/css/legal.css',
 ('script','rollsbar-app'):THEME+'assets/js/app.js',
 ('style','rollsbar-checkout'):PLUGIN+'assets/css/checkout.css',
 ('script','rollsbar-checkout'):PLUGIN+'assets/js/checkout.js',
 ('style','rollsbar-analytics-consent'):PLUGIN+'assets/css/analytics-consent.css',
 ('script','rollsbar-analytics'):PLUGIN+'assets/js/analytics.js',
}


def checkout_bytes(name):
    # Respect the repository's existing CRLF checkout filter on Windows.
    # No CSS/JS file is rewritten or normalized by this test.
    return subprocess.check_output(['git','cat-file','--filters',BASE+':'+name],cwd=ROOT)


class AssetVersions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True)
        cls.old={}
        for key,path in [('theme_source',THEME+'functions.php'),('checkout_source',PLUGIN+'includes/class-rollsbar-checkout.php'),('analytics_source',PLUGIN+'includes/class-rollsbar-analytics.php')]:
            target=OUT/('baseline-'+Path(path).name)
            target.write_bytes(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT))
            cls.old[key]=str(target)

    def php(self,**payload):
        p=subprocess.run([str(ROOT/'qa/.runtime/php/php.exe'),str(ROOT/'qa/checkout/asset_version_fixture.php')],
                         input=json.dumps(payload),cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertEqual(p.stderr,'')
        return json.loads(p.stdout)

    def test_known_bytes_repeat_and_equal_files(self):
        with tempfile.TemporaryDirectory(dir=OUT) as folder:
            a=Path(folder)/'a.css';b=Path(folder)/'b.js';c=Path(folder)/'c.css'
            a.write_bytes(b'abc');b.write_bytes(b'abc');c.write_bytes(b'abd')
            result=self.php(mode='helpers',items=[{'path':str(p),'fallback':'release'} for p in [a,a,b,c]])
            self.assertEqual(result[0],{'theme':'ba7816bf8f01cfea','plugin':'ba7816bf8f01cfea'})
            self.assertEqual(result[0],result[1]);self.assertEqual(result[0],result[2]);self.assertNotEqual(result[0],result[3])

    def test_changed_fixture_changes_only_its_version(self):
        with tempfile.TemporaryDirectory(dir=OUT) as folder:
            a=Path(folder)/'a.css';b=Path(folder)/'b.js'
            a.write_bytes(b'original css');b.write_bytes(b'original js')
            items=[{'path':str(p),'fallback':'release'} for p in [a,b]]
            before=self.php(mode='helpers',items=items)
            a.write_bytes(b'changed css')
            after=self.php(mode='helpers',items=items)
            self.assertNotEqual(before[0],after[0]);self.assertEqual(before[1],after[1])

    def test_per_request_memoization(self):
        with tempfile.TemporaryDirectory(dir=OUT) as folder:
            a=Path(folder)/'memo.css';a.write_bytes(b'first bytes')
            result=self.php(mode='helpers',items=[{'path':str(a),'fallback':'release'}],rewrite='new bytes',fixture_directory=folder)
            self.assertEqual(result[0],result[1])
            fresh=self.php(mode='helpers',items=[{'path':str(a),'fallback':'release'}])
            self.assertNotEqual(result[0],fresh[0])

    def test_missing_directory_and_nonlocal_fallback(self):
        with tempfile.TemporaryDirectory(dir=OUT) as folder:
            paths=[str(Path(folder)/'missing.css'),str(Path(folder)),'relative.css','https://fixture.invalid/file.css','php://memory']
            items=[{'path':p,'fallback':'release-one'} for p in paths]+[{'path':paths[0],'fallback':'release-two'}]
            result=self.php(mode='helpers',items=items)
            self.assertTrue(all(r=={'theme':'release-one','plugin':'release-one'} for r in result[:-1]))
            self.assertEqual(result[-1],{'theme':'release-two','plugin':'release-two'})
            blocked=self.php(mode='helpers',read_scope=folder,items=[{'path':str(ROOT/(THEME+'style.css')),'fallback':'restricted-fallback'}])
            self.assertEqual(blocked,[{'theme':'restricted-fallback','plugin':'restricted-fallback'}])

    def test_actual_enqueues_versions_and_unchanged_other_arguments(self):
        before=self.php(**self.old);after=self.php()
        self.assertNotIn(str(ROOT),json.dumps(after))
        self.assertEqual(len(before),len(after))
        evidence=[]
        for (kind,old),(new_kind,new) in zip(before,after):
            self.assertEqual(kind,new_kind)
            if kind=='inline':self.assertEqual(old,new);continue
            asset=TARGETS[(kind,new[0])]
            expected=hashlib.sha256((ROOT/asset).read_bytes()).hexdigest()[:16]
            self.assertEqual(old[3],'0.1.0' if asset.startswith(THEME) else '0.1.8')
            self.assertEqual(new[3],expected)
            self.assertRegex(new[3],r'^[0-9a-f]{16}$')
            self.assertEqual(old[:3]+old[4:],new[:3]+new[4:])
            evidence.append({'asset':asset,'before':old[3],'after':new[3],'effective_url':new[1]+'?ver='+new[3]})
        self.assertEqual(len(evidence),8)
        self.assertEqual(len({r['after'] for r in evidence}),8)
        (OUT/'enqueue-versions.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')

    def test_theme_and_plugin_independent_and_conditions_preserved(self):
        theme=self.php(component='theme');plugin=self.php(component='plugin')
        self.assertEqual(len([c for c in theme if c[0]!='inline']),4)
        self.assertEqual(len([c for c in plugin if c[0]!='inline']),4)
        calls=self.php(legal=False,checkout=False,analytics=False)
        self.assertEqual([c[1][0] for c in calls],['rollsbar-theme','rollsbar-app','rollsbar-app'])

    def test_source_no_time_random_or_semantic_version_bump(self):
        theme=(ROOT/(THEME+'functions.php')).read_text(encoding='utf-8')
        helper=theme.split('function rollsbar_theme_asset_version',1)[1].split('\nadd_action(',1)[0]
        plugin=(ROOT/(PLUGIN+'includes/class-rollsbar-asset-version.php')).read_text(encoding='utf-8')
        for source in [helper,plugin]:
            self.assertNotRegex(source,r'\b(?:time|microtime|rand|mt_rand|random_bytes|uniqid|filemtime)\s*\(')
            self.assertIn("hash_file( 'sha256'",source)
            self.assertIn('is_readable(',source);self.assertIn('is_file(',source)
        for name in [THEME+'style.css',PLUGIN+'rollsbar-core.php']:
            self.assertEqual((ROOT/name).read_bytes(),checkout_bytes(name))

    def test_all_frontend_bytes_identical_to_start(self):
        manifest={}
        # Check every theme/plugin CSS/JS, including the out-of-scope admin asset.
        for component in [THEME,PLUGIN]:
            for path in (ROOT/component).rglob('*'):
                if path.suffix not in ['.css','.js']:continue
                name=path.relative_to(ROOT).as_posix()
                baseline=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT)
                self.assertEqual(path.read_bytes(),checkout_bytes(name),name)
                blob=subprocess.check_output(['git','rev-parse',BASE+':'+name],cwd=ROOT,text=True).strip()
                current=subprocess.check_output(['git','hash-object','--path='+name,name],cwd=ROOT,text=True).strip()
                self.assertEqual(current,blob,name)
                manifest[name]={'git_blob_unchanged':blob,'canonical_sha256':hashlib.sha256(baseline).hexdigest(),
                                'working_checkout_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        (OUT/'byte-preservation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

    def test_checkout_business_and_theme_catalog_code_unchanged(self):
        name=PLUGIN+'includes/class-rollsbar-checkout.php'
        before=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT).decode('utf-8')
        after=(ROOT/name).read_text(encoding='utf-8')
        start='public static function register_additional_fields';end='public static function enqueue_checkout_assets'
        self.assertEqual(before.split(start,1)[1].split(end,1)[0],after.split(start,1)[1].split(end,1)[0])
        self.assertEqual(before.split('$address_suggestions_enabled =',1)[1],after.split('$address_suggestions_enabled =',1)[1])
        name=THEME+'functions.php'
        before=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT).decode('utf-8')
        after=(ROOT/name).read_text(encoding='utf-8')
        marker='/** Compact catalog price;'
        self.assertEqual(before.split(marker,1)[1],after.split(marker,1)[1])


if __name__=='__main__':unittest.main()

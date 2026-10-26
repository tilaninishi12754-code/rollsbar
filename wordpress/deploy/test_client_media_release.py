"""Deterministic deployment guards, without credentials or network."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import apply_client_media_staging as media


class Release(unittest.TestCase):
    def test_backup_and_identity_gates_precede_media_writes(self):
        sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=media.ROOT,text=True).strip()
        script=media.PREFIX+media.apply_script(sha)
        self.assertLess(script.index('backup_verified_before_site_mutation'),script.index('cp -a'))
        self.assertLess(script.index('backup_verified_before_site_mutation'),script.index('install -m'))
        self.assertLess(script.index('wp_get_environment_type'),script.index('backup_verified_before_site_mutation'))
        self.assertIn('ROLLSBAR_FRESH_BACKUP_VERIFIED',script)
        self.assertIn('business_after" == "$business_before',script)
        self.assertIn('checkout_unchanged=PASS',script)
        self.assertNotIn('catalog import',script)
        self.assertNotIn('bootstrap-staging.sh',script)
        self.assertEqual(script.count('wp_cmd rollsbar media sync --confirm-staging'),2)
        if shutil.which('bash'):
            with tempfile.NamedTemporaryFile(mode='w',suffix='.sh',delete=False) as f:
                f.write(script);path=Path(f.name)
            try: subprocess.run(['bash','-n',str(path)],check=True)
            finally: path.unlink()

    def test_only_four_media_php_paths_can_change(self):
        self.assertEqual(len(media.CHANGED),4)
        self.assertFalse(any('checkout' in p.lower() for p in media.CHANGED))
        self.assertTrue(all(p.endswith('.php') for p in media.CHANGED))

    def test_canon_in_bootstrap_and_package(self):
        bootstrap=(media.ROOT/'wordpress/deploy/bootstrap-staging.sh').read_text(encoding='utf-8')
        package=(media.ROOT/'.github/workflows/build-wordpress-staging-package.yml').read_text(encoding='utf-8')
        self.assertIn('data/product-media',bootstrap)
        self.assertIn('data/product-media',package)
        self.assertLess(bootstrap.index('rollsbar catalog import'),bootstrap.index('rollsbar media sync'))


if __name__=='__main__': unittest.main()

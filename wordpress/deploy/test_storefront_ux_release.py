import unittest
from unittest.mock import patch
import tempfile
import json
import apply_storefront_ux_staging as release

class ReleaseTest(unittest.TestCase):
 def test_narrow_backup_first(self):
  script=release.apply_script(release.BASE)
  self.assertEqual(len(release.CHANGED),5)
  self.assertLess(script.index('ROLLSBAR_FRESH_BACKUP_VERIFIED'),script.index('install -m 0644'))
  self.assertNotIn('bootstrap-staging.sh',script)
  self.assertNotIn('rollsbar media sync',script)
  self.assertIn('business_before',script)
  self.assertIn('count($canonicalIds)!==118',script)
  self.assertIn('UX_MEDIA_BEGIN',script)
  self.assertNotIn('staging-deployed-sha.ux-new',script)
  # Unchanged application files, including all checkout assets, are hash guarded.
  self.assertIn('checkout.css',script)
  self.assertIn('checkout.js',script)
  self.assertIn('class-rollsbar-checkout.php',script)
 def test_finalize_requires_browser_and_exact_release(self):
  source=release.Path(release.__file__).read_text()
  self.assertIn("proof.get('status')!='PASS'",source)
  self.assertIn("proof.get('release_sha')!=sha",source)
  script=release.finalize_script(release.BASE)
  self.assertIn('phase=backend_verified',script)
  self.assertIn('phase=browser_verified',script)
  self.assertIn('staging-deployed-sha.ux-new',script)
 def test_interaction_scope(self):
  with patch.object(release,'BASE',release.BASE),patch.object(release,'CHANGED',release.CHANGED):
   release.require_interaction_delta()
   self.assertEqual(release.BASE,'7e584a25285cbee82322c37bc7ea40187c0cd4a7')
   self.assertEqual(len(release.CHANGED),3)
   self.assertTrue(all(p.endswith(('app.js','app.css','class-rollsbar-cart-actions.php')) for p in release.CHANGED))
 def test_interaction_proof_rejects_missing_width_and_wrong_release(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(release,'OUT',release.Path(folder)):
   path=release.OUT/'interaction/browser.json';path.parent.mkdir()
   proof={'status':'PASS','release_sha':'candidate','checks':[{'engine':'chromium','width':w} for w in [320,390,430,701,900,1440]]}
   path.write_text(json.dumps(proof));release.verify_interaction_proof('candidate')
   with self.assertRaises(ValueError):release.verify_interaction_proof('other')
   proof['checks'].pop();path.write_text(json.dumps(proof))
   with self.assertRaises(ValueError):release.verify_interaction_proof('candidate')
 def test_transport_pins_staging(self):
  for guard in ['https://staging.rollsbar.ru',"== 'staging'",'blog_public']:
   self.assertIn(guard,release.transport.PREFIX)

if __name__=='__main__':unittest.main()

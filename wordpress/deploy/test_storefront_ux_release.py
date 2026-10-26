import unittest
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
 def test_transport_pins_staging(self):
  for guard in ['https://staging.rollsbar.ru',"== 'staging'",'blog_public']:
   self.assertIn(guard,release.transport.PREFIX)

if __name__=='__main__':unittest.main()

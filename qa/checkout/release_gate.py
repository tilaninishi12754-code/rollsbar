"""Offline-testable dispatch policy and observed checkout response identity."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
FEATURE = 'refs/heads/wordpress/checkout-visual-parity-2026-10-25'
ASSET_ROOT = 'wordpress/wp-content/plugins/rollsbar-core/assets/'
ASSETS = {'css/checkout.css': 'text/css', 'js/checkout.js': 'application/javascript'}


def validate_marker(value):
    if not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('Expected deployed marker must be a full lowercase commit SHA')
    return value


def dispatch_policy(mode, marker, ref, head):
    if mode not in ('historical', 'shadow', 'live'):
        raise ValueError('Unknown checkout mode')
    explicit = mode != 'historical'
    if explicit:
        validate_marker(marker)
        if mode == 'live' and marker != head:
            raise ValueError('Live release marker must equal checked-out HEAD')
    else:
        if marker:
            raise ValueError('Select shadow or live to override the historical marker')
        marker = ('88826907fc7ffe805a7c47f36c35a74c0049e08e' if ref == FEATURE
                  else 'e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea')
        mode = 'shadow' if ref == FEATURE else 'historical'
    return {'ROLLSBAR_QA_EXPECTED_MARKER': marker, 'CHECKOUT_MODE': mode,
            'ROLLSBAR_QA_VERIFY_HISTORICAL': '1' if not explicit and ref != FEATURE else '0'}


class AssetIdentity:
    def __init__(self, expected, base):
        self.expected = expected
        self.origin = urlsplit(base)
        self.records = []
        self.errors = []

    def observe(self, response):
        url = urlsplit(response.url)
        # Also retain wrong-origin/path lookalikes, rather than silently ignoring them.
        if url.path.rsplit('/', 1)[-1] not in ('checkout.css', 'checkout.js'):
            return
        try:
            relative = next((a for a in ASSETS if url.path == '/wp-content/plugins/rollsbar-core/assets/' + a), None)
            body = response.body()
            record = {'url': response.url, 'asset': relative, 'status': response.status,
                      'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
            if relative in self.expected:
                record['expected_sha256'] = hashlib.sha256(self.expected[relative]).hexdigest()
            self.records.append(record)
            if (url.scheme, url.netloc) != (self.origin.scheme, self.origin.netloc) or relative is None:
                self.errors.append('Wrong checkout asset origin/path: ' + response.url)
        except Exception as exc:
            self.errors.append('Cannot read checkout response: ' + str(exc))

    def verify(self, substitutions):
        if substitutions:
            raise AssertionError('LIVE DEPLOYED cannot use asset substitutions')
        if self.errors:
            raise AssertionError('; '.join(self.errors))
        for asset, body in self.expected.items():
            rows = [r for r in self.records if r['asset'] == asset]
            expected_hash = hashlib.sha256(body).hexdigest()
            if len(rows) != 1 or rows[0]['status'] != 200 or rows[0]['sha256'] != expected_hash:
                raise AssertionError('Served asset identity mismatch/missing/duplicate: ' + asset)
            rows[0]['expected_sha256'] = expected_hash
            rows[0]['identity'] = 'PASS'


def release_assets(marker):
    validate_marker(marker)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if marker != head:
        raise ValueError('Live release marker must equal checked-out HEAD')
    return {a: subprocess.check_output(['git', 'show', marker + ':' + ASSET_ROOT + a], cwd=ROOT) for a in ASSETS}


def install_asset_routes(page, live, substitute):
    if live:
        return
    for asset, mime in ASSETS.items():
        page.route('**/rollsbar-core/assets/' + asset + '*',
                   lambda route, a=asset, m=mime: substitute(route, a, m))


if __name__ == '__main__':
    policy = dispatch_policy(os.environ['DISPATCH_MODE'], os.environ.get('DISPATCH_MARKER', ''),
                             os.environ['GITHUB_REF'],
                             subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as stream:
        for key, value in policy.items():
            stream.write(key + '=' + value + '\n')

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
ASSET_URL_ROOT = '/wp-content/plugins/rollsbar-core/assets/'
ASSETS = {'css/checkout.css': 'text/css', 'js/checkout.js': 'application/javascript'}


def validate_marker(value):
    if not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('Expected deployed marker must be a full lowercase commit SHA')
    return value


def validate_live_release(marker):
    """Application truth is an existing commit ancestral to current QA tooling."""
    validate_marker(marker)
    try:
        kind = subprocess.check_output(['git', 'cat-file', '-t', marker], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).strip()
        if kind != b'commit':
            raise ValueError('Expected deployed marker must identify a commit')
        subprocess.run(['git', 'merge-base', '--is-ancestor', marker, 'HEAD'],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        raise ValueError('Deployed release must exist and be an ancestor of tooling HEAD') from exc
    return marker


def dispatch_policy(mode, marker, ref):
    if mode not in ('historical', 'shadow', 'live'):
        raise ValueError('Unknown checkout mode')
    explicit = mode != 'historical'
    if explicit:
        validate_marker(marker)
        if mode == 'live':
            validate_live_release(marker)
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
        # WooCommerce/themes may legitimately have the same basename. Only our
        # exact targets and checkout lookalikes within our namespace are relevant.
        relative = next((a for a in ASSETS if url.path == ASSET_URL_ROOT + a), None)
        lookalike = (url.path.startswith(ASSET_URL_ROOT)
                     and url.path.rsplit('/', 1)[-1] in ('checkout.css', 'checkout.js'))
        if relative is None and not lookalike:
            return
        try:
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
    validate_live_release(marker)
    return {a: subprocess.check_output(['git', 'show', marker + ':' + ASSET_ROOT + a], cwd=ROOT) for a in ASSETS}


def install_asset_routes(page, live, substitute):
    if live:
        return
    for asset, mime in ASSETS.items():
        page.route('**/rollsbar-core/assets/' + asset + '*',
                   lambda route, a=asset, m=mime: substitute(route, a, m))


if __name__ == '__main__':
    policy = dispatch_policy(os.environ['DISPATCH_MODE'], os.environ.get('DISPATCH_MARKER', ''),
                             os.environ['GITHUB_REF'])
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as stream:
        for key, value in policy.items():
            stream.write(key + '=' + value + '\n')

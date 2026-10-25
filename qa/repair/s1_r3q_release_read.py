"""Fixed read-only staging evidence; no deployment, backup creation or restore."""
import os
import re
import shlex
from urllib.parse import urlsplit

import paramiko

EXPECTED = os.environ.get('ROLLSBAR_QA_EXPECTED_MARKER', 'e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea')


def marker_command(expected):
    if not re.fullmatch(r'[0-9a-f]{40}', expected):
        raise ValueError('Expected deployed marker must be a full lowercase commit SHA')
    return r'''set -eu
marker=$(cat "$HOME/.rollsbar-staging-deployed-sha")
printf 'deployed_marker=%s\n' "$marker"
test "$marker" = ''' + expected + '\n'


COMMAND = marker_command(EXPECTED)
HISTORICAL = r'''
cd "$HOME/rollsbar-backups/staging/20261024T153707Z"
sha256sum -c SHA256SUMS
gzip -t database.sql.gz
tar -tzf uploads.tar.gz >/dev/null
echo 'historical_snapshot=20261024T153707Z integrity=PASS mutation=NO'
'''
PICKUP = r'''
$settings = get_option('woocommerce_pickup_location_settings', array());
$locations = get_option('pickup_location_pickup_locations', array());
$zones = WC_Shipping_Zones::get_zones();
$zones[] = array('id'=>0);
$methods = array();
foreach ($zones as $zone) {
    $z = new WC_Shipping_Zone($zone['zone_id'] ?? $zone['id']);
    foreach ($z->get_shipping_methods(true) as $method) {
        $methods[] = array('zone'=>$z->get_id(), 'id'=>$method->id, 'enabled'=>$method->enabled);
    }
}
echo wp_json_encode(array('native_pickup_enabled'=>$settings['enabled'] ?? 'no',
    'enabled_pickup_locations'=>count(array_filter($locations, static fn($x)=>!empty($x['enabled']))),
    'enabled_zone_methods'=>$methods), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
'''


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    password = os.environ['ISP_MANAGER_PASSWORD']
    try:
        client.connect(hostname=urlsplit(os.environ['ISP_MANAGER_URL']).hostname,
                       username=os.environ['ISP_MANAGER_USER'], password=password,
                       timeout=15, auth_timeout=15, banner_timeout=15,
                       look_for_keys=False, allow_agent=False)
        command = COMMAND
        if os.environ.get('ROLLSBAR_QA_VERIFY_HISTORICAL') == '1':
            command += HISTORICAL
            command += '\nexport PATH="$HOME/.local/bin:$PATH"\n'
            command += 'wp --path="$HOME/www/staging.rollsbar.ru" eval ' + shlex.quote(PICKUP)
        _, stdout, stderr = client.exec_command('bash -lc ' + shlex.quote(command), timeout=180)
        out = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        status = stdout.channel.recv_exit_status()
        print(out.strip())
        if status:
            raise RuntimeError(f'read-only verification exit={status}; {error.replace(password, "***")}')
        assert f'deployed_marker={EXPECTED}' in out
    finally:
        client.close()


if __name__ == '__main__':
    main()

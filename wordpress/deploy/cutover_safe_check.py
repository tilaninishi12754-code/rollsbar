"""Keep all private hosting inventory in runner memory; emit only check booleans."""
import pathlib,hashlib,json
import recovery_drill as core
from precutover_backup import PinnedHostKey
import paramiko

def main():
    sid=core.auth()
    sites=core.rows(core.api_call({'out':'xml','func':'webdomain','auth':sid}))
    print('staging_site_present='+str(any(r.get('name')=='staging.rollsbar.ru' for r in sites)).lower())
    print('production_site_present='+str(any(r.get('name')=='rollsbar.ru' for r in sites)).lower())
    try:
        zones=core.rows(core.api_call({'out':'xml','func':'domain','auth':sid}))
        print('production_dns_zone_accessible_from_hosting='+str(any(r.get('name','').rstrip('.')=='rollsbar.ru' for r in zones)).lower())
    except Exception:print('production_dns_zone_accessible_from_hosting=false')
    client=paramiko.SSHClient();client.set_missing_host_key_policy(PinnedHostKey())
    client.connect(core.urlsplit(core.BASE).hostname,username=core.USER,password=core.PASSWORD,look_for_keys=False,allow_agent=False,timeout=20)
    try:
        command=r'''set -euo pipefail
cd "$HOME/www/staging.rollsbar.ru"
find wp-content/themes/rollsbar-theme wp-content/plugins/rollsbar-core -type f -print0 | sort -z | xargs -0 sha256sum
'''
        status,out,err=core.remote(client,command,timeout=180)
        if status:raise RuntimeError('Remote project hash check failed')
        actual={line.split(maxsplit=1)[1]:line.split(maxsplit=1)[0] for line in out.splitlines()}
        expected={}
        for folder in ('wordpress/wp-content/themes/rollsbar-theme','wordpress/wp-content/plugins/rollsbar-core'):
            for p in pathlib.Path(folder).rglob('*'):
                if p.is_file():expected[str(p).removeprefix('wordpress/')]=hashlib.sha256(p.read_bytes()).hexdigest()
        print('project_tracked_code_matches_release='+str(all(v==actual.get(p) for p,v in expected.items())).lower())
        print('project_has_extra_runtime_files='+str(bool(set(actual)-set(expected))).lower())
        print('read_only_checks_completed=true')
    finally:client.close()

if __name__=='__main__':
    try:main()
    except Exception as exc: print('check_failed=true; type='+type(exc).__name__);raise SystemExit(1)

import json
import os
import shlex
import socket
import pathlib
import hashlib
import base64
import secrets
from urllib.parse import urlsplit
import paramiko

HOST_FINGERPRINT = 'USxyLBp+ya1El/PT7cq9PKmpOUHd+uLBF1uCGvXnv94='

class PinnedHostKey(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        actual = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode()
        if actual != HOST_FINGERPRINT:
            raise RuntimeError('SSH host key differs from verified inventory')

def backup(client):
    # The existing format-3 snapshot also enables the established isolated DB restore drill.
    canonical = pathlib.Path('wordpress/deploy/backup-staging.sh').read_text()
    print(remote(client, 'export PATH="$HOME/.local/bin:$PATH"\nexport WP_PATH="$HOME/www/staging.rollsbar.ru"\nexport ROLLSBAR_BACKUP_RETENTION=9999\n' + canonical,timeout=900))
    command=r'''set -euo pipefail
umask 077
export PATH="$HOME/.local/bin:$PATH"
site="$(realpath "$HOME/www/staging.rollsbar.ru")"
[[ "$site" == "$HOME/www/staging.rollsbar.ru" ]] || exit 21
[[ -f "$site/wp-config.php" && -f "$site/wp-load.php" ]] || exit 22
actual_home="$(wp --path="$site" --skip-plugins --skip-themes option get home)"
[[ "$actual_home" == 'https://staging.rollsbar.ru' ]] || exit 23
root="$HOME/rollsbar-backups/precutover"
mkdir -p "$root"
[[ ! -L "$root" && "$(realpath "$root")" == "$root" ]] || exit 24
chmod 700 "$root"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
snapshot="$root/$stamp"
[[ ! -e "$snapshot" ]] || exit 25
mkdir "$snapshot"
wp --path="$site" --skip-plugins --skip-themes db export - --single-transaction --quick --skip-lock-tables 2>"$snapshot/db-export.stderr" | gzip -9 > "$snapshot/database.sql.gz"
gzip -t "$snapshot/database.sql.gz"
tar -C "$site" -czf "$snapshot/site-files.tar.gz" .
tar -tzf "$snapshot/site-files.tar.gz" >/dev/null
{
 echo 'backup_format=full-precutover-v1'
 echo "created_utc=$stamp"
 echo "site_url=$actual_home"
 echo 'contains_secrets=yes; keep private'
 echo 'production_root=absent_in_this_account'
 echo 'restore_database_to_isolated_database_only=yes'
 printf 'wp_version='; wp --path="$site" core version
 printf 'deployed_sha='; cat "$HOME/.rollsbar-staging-deployed-sha"
 echo
 echo 'plugins:'; wp --path="$site" --skip-plugins --skip-themes plugin list --format=json
 echo 'themes:'; wp --path="$site" --skip-plugins --skip-themes theme list --format=json
} > "$snapshot/manifest.txt"
rm -- "$snapshot/db-export.stderr"
(cd "$snapshot"; sha256sum database.sql.gz site-files.tar.gz manifest.txt > SHA256SUMS; sha256sum -c SHA256SUMS >/dev/null)
chmod 600 "$snapshot"/*
printf 'snapshot_path=%s\n' "$snapshot"
printf 'full_backup_integrity=PASS\n'
'''
    result=remote(client,command,timeout=1200)
    snapshot=next(x.split('=',1)[1] for x in result.splitlines() if x.startswith('snapshot_path='))
    print('full_backup_integrity=PASS')
    print('full_backup_timestamp='+snapshot.rsplit('/',1)[1])
    folder=pathlib.Path('precutover-output');folder.mkdir(mode=0o700,exist_ok=True)
    receipt={'timestamp':snapshot.rsplit('/',1)[1], 'server_directory':'$HOME/rollsbar-backups/precutover/'+snapshot.rsplit('/',1)[1], 'source':'https://staging.rollsbar.ru', 'full_backup_integrity':'PASS', 'offsite_copy':'NOT_CREATED_PENDING_OWNER_DESTINATION_APPROVAL', 'site_modified':False, 'production_modified':False}
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
    print('backup_payload_location=hosting_only; no payload exported')

def remote(client, command, timeout=120):
    _, out, err = client.exec_command('bash -lc ' + shlex.quote(command), timeout=timeout)
    body = out.read().decode('utf-8', 'replace')
    errors = err.read()
    status = out.channel.recv_exit_status()
    if status:
        raise RuntimeError(f'remote_exit={status}; stderr_present={bool(errors)}')
    return body

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(PinnedHostKey())
    client.connect(urlsplit(os.environ['ISP_MANAGER_URL']).hostname,
        username=os.environ['ISP_MANAGER_USER'], password=os.environ['ISP_MANAGER_PASSWORD'],
        look_for_keys=False, allow_agent=False, timeout=20, auth_timeout=20, banner_timeout=20)
    try:
        key = client.get_transport().get_remote_server_key()
        print('ssh_host_key_sha256=' + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode())
        if os.environ.get('PRECUTOVER_MODE') == 'backup':
            backup(client)
            return
        print(remote(client, r'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
printf 'disk_available_bytes='; df -PB1 "$HOME" | awk 'NR==2{print $4}'
for domain in rollsbar.ru www.rollsbar.ru staging.rollsbar.ru; do
 p="$HOME/www/$domain"
 echo "domain=$domain"
 if [[ -d "$p" ]]; then
   printf 'realpath='; realpath "$p"
   printf 'bytes='; du -sb "$p" | cut -f1
   printf 'wordpress='; if [[ -f "$p/wp-config.php" && -f "$p/wp-load.php" ]]; then echo yes; else echo no; fi
   printf 'root_entries='; find "$p" -mindepth 1 -maxdepth 1 -printf '%f,'; echo
   if [[ -f "$p/wp-load.php" ]]; then
     printf 'home='; wp --path="$p" --skip-plugins --skip-themes option get home
     printf 'wp_version='; wp --path="$p" core version
   fi
 else echo 'document_root=absent'; fi
done
echo 'account_web_roots:'
find "$HOME/www" -mindepth 1 -maxdepth 1 -type d -printf '%f\n'
echo 'deployed_marker:'
if [[ -f "$HOME/.rollsbar-staging-deployed-sha" ]]; then cat "$HOME/.rollsbar-staging-deployed-sha"; fi
'''))
        for domain in ('rollsbar.ru', 'www.rollsbar.ru', 'staging.rollsbar.ru'):
            print('dns=' + domain + ':' + ','.join(sorted({x[4][0] for x in socket.getaddrinfo(domain,443)})))
    finally:
        client.close()

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('operation_failed=' + type(exc).__name__)
        raise SystemExit(1)

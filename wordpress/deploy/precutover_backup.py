import json
import os
import shlex
import socket
from urllib.parse import urlsplit
import paramiko

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
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(urlsplit(os.environ['ISP_MANAGER_URL']).hostname,
        username=os.environ['ISP_MANAGER_USER'], password=os.environ['ISP_MANAGER_PASSWORD'],
        look_for_keys=False, allow_agent=False, timeout=20, auth_timeout=20, banner_timeout=20)
    try:
        key = client.get_transport().get_remote_server_key()
        import hashlib, base64
        print('ssh_host_key_sha256=' + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode())
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

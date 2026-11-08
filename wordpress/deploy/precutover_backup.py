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

def encrypted_copy(sftp, source, target, public_key):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    key, nonce = secrets.token_bytes(32), secrets.token_bytes(12)
    wrapped = public_key.encrypt(key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    header = (json.dumps({'format':'rollsbar-backup-aes256gcm-rsa3072-v1', 'key':base64.b64encode(wrapped).decode(), 'nonce':base64.b64encode(nonce).decode()},sort_keys=True)+'\n').encode()
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    cipher.authenticate_additional_data(header)
    plain_hash = hashlib.sha256()
    size = 0
    with sftp.open(source,'rb') as src, target.open('wb') as dst:
        dst.write(header)
        while chunk := src.read(1024*1024):
            size += len(chunk); plain_hash.update(chunk); dst.write(cipher.update(chunk))
        dst.write(cipher.finalize()); dst.write(cipher.tag)
    return {'file':target.name,'plaintext_sha256':plain_hash.hexdigest(),'plaintext_bytes':size,'encrypted_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}

def backup(client):
    snapshot=remote(client, r'printf "%s" "$HOME/rollsbar-backups/precutover/20261107T222121Z"').strip()
    remote(client, 'set -euo pipefail\nsnapshot='+shlex.quote(snapshot)+'\n[[ -d "$snapshot" && ! -L "$snapshot" && "$(realpath "$snapshot")" == "$snapshot" ]]\ncd "$snapshot"\nsha256sum -c SHA256SUMS >/dev/null\ngzip -t database.sql.gz\ntar -tzf site-files.tar.gz >/dev/null',timeout=300)
    print('existing_verified_snapshot=20261107T222121Z; server_integrity=PASS')
    from cryptography.hazmat.primitives import serialization
    public_key=serialization.load_pem_public_key(pathlib.Path('wordpress/deploy/precutover-backup-public.pem').read_bytes())
    folder=pathlib.Path('precutover-output');folder.mkdir(mode=0o700,exist_ok=True)
    sftp=client.open_sftp()
    try:
        with sftp.open(snapshot+'/SHA256SUMS') as fh:
            expected={line.split()[1]:line.split()[0] for line in fh.read().decode().splitlines()}
        receipts=[]
        for name in ('database.sql.gz','site-files.tar.gz','manifest.txt','SHA256SUMS'):
            receipt=encrypted_copy(sftp,snapshot+'/'+name,folder/(name+'.encrypted'),public_key)
            if name in expected and receipt['plaintext_sha256'] != expected[name]: raise RuntimeError('Transfer checksum mismatch')
            receipts.append(receipt)
        (folder/'receipt.json').write_text(json.dumps({'timestamp':snapshot.rsplit('/',1)[1],'server_directory':'$HOME/rollsbar-backups/precutover/'+snapshot.rsplit('/',1)[1],'source':'https://staging.rollsbar.ru','files':receipts,'site_modified':False,'production_modified':False},indent=2))
        print('encrypted_offsite_copy=PASS')
    finally: sftp.close()

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

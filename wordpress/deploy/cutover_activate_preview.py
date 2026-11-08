import json,pathlib,shlex
import recovery_drill as core
from cutover_prepare import run,connect,write_private,remove_private,SECRET,RELEASE
from cutover_tls import read_state,trusted_tls

def main():
    state=read_state()
    if state.get('phase') not in ('tls_ready_maintenance','preview_active') or state.get('release')!=RELEASE:raise RuntimeError('TLS/state gate')
    if not trusted_tls('rollsbar.ru') or not trusted_tls('www.rollsbar.ru'):raise RuntimeError('Trusted TLS required')
    client=connect();sftp=client.open_sftp()
    try:home=sftp.normalize('.')
    finally:sftp.close();client.close()
    run(None,'set -euo pipefail\nexport PATH="$HOME/.local/bin:$PATH"\nroot="$HOME/www/rollsbar.ru"\n[[ "$(wp --path="$root" --skip-plugins --skip-themes option get home)" == https://rollsbar.ru ]]\n[[ "$(wp --path="$root" --skip-plugins --skip-themes post list --post_type=product --post_status=publish --format=count)" == 121 ]]\n[[ "$(wp --path="$root" --skip-plugins --skip-themes option get blog_public)" == 0 ]]',timeout=120)
    # Build final routing while retaining noindex and disabled cron for browser QA.
    client=connect();sftp=client.open_sftp()
    try:
        with sftp.open('.rollsbar-production-final-htaccess') as fh:body=fh.read().decode()
    finally:sftp.close();client.close()
    body=body.replace('staging.rollsbar.ru','rollsbar.ru')
    body='\n'.join(line for line in body.splitlines() if not ('X-Robots-Tag' in line and 'noindex' in line))+'\n'
    prefix='''# Production canonical host; preserve ACME HTTP validation.
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule ^\\.well-known/acme-challenge/ - [L]
RewriteCond %{HTTP_HOST} ^www\\.rollsbar\\.ru$ [NC]
RewriteRule ^ https://rollsbar.ru%{REQUEST_URI} [R=301,L,NE]
RewriteCond %{HTTPS} !=on
RewriteRule ^ https://rollsbar.ru%{REQUEST_URI} [R=301,L,NE]
</IfModule>
'''
    write_private(None,home+'/www/rollsbar.ru/.htaccess',prefix+body)
    out=run(None,'set -euo pipefail\nexport PATH="$HOME/.local/bin:$PATH"\nroot="$HOME/www/rollsbar.ru"\nchmod 644 "$root/.htaccess"\nwp --path="$root" rewrite flush --hard >/dev/null\n[[ "$(wp --path="$root" --skip-plugins --skip-themes option get blog_public)" == 0 ]]\necho production_preview_routing=PASS',timeout=180)
    print(out,flush=True)
    state['phase']='preview_active';write_private(None,SECRET,json.dumps(state))

if __name__=='__main__':
    try:main()
    except Exception as exc:print('production_preview_activation_failed=true; type='+type(exc).__name__);raise SystemExit(1)

import pathlib,shlex
from cutover_prepare import connect,run,write_private,remove_private,RELEASE
from cutover_tls import read_state,trusted_tls

def main():
    state=read_state()
    if state.get('release')!=RELEASE or state.get('phase') not in ('prepared_maintenance','tls_ready_maintenance'):raise RuntimeError('Preview state required')
    if not trusted_tls('rollsbar.ru'):raise RuntimeError('Main trusted TLS required')
    client=connect();sftp=client.open_sftp()
    try:home=sftp.normalize('.')
    finally:sftp.close();client.close()
    path=home+'/.rollsbar-cutover-acceptance.php'
    write_private(None,path,pathlib.Path('wordpress/deploy/cutover_acceptance.php').read_text())
    try:
        out=run(None,'set -euo pipefail\nexport PATH="$HOME/.local/bin:$PATH"\nwp --path="$HOME/www/rollsbar.ru" eval-file '+shlex.quote(path),timeout=240)
        print(out,flush=True)
        if 'external_messages_sent=0' not in out or 'synthetic_order_and_application_cleanup=PASS' not in out:raise RuntimeError('Backend proof incomplete')
        write_private(None,'.rollsbar-production-backend-verified',RELEASE)
    finally:remove_private(path)

if __name__=='__main__':
    try:main()
    except Exception as exc:print('production_backend_check_failed=true; type='+type(exc).__name__);raise SystemExit(1)

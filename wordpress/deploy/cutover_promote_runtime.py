"""Narrow promotion of the accepted checkout runtime to its canonical live host."""
import pathlib,json,os,shlex,secrets
from cutover_prepare import connect,run,write_private,SECRET,RELEASE
from cutover_tls import read_state

def main():
    state=read_state()
    if state.get('release')!=RELEASE or state.get('phase')!='preview_active' or state.get('promoted_release'):raise RuntimeError('Preview-only one-time promotion gate')
    candidate=os.environ['GITHUB_SHA']
    manifest=json.loads(pathlib.Path('wordpress/deploy/runtime-promotion-manifest.json').read_text())
    if len(manifest)!=6:raise RuntimeError('Unexpected file scope')
    client=connect();sftp=client.open_sftp()
    try:home=sftp.normalize('.')
    finally:sftp.close();client.close()
    work=home+'/.rollsbar-runtime-promotion-'+secrets.token_hex(8)
    paths=[x['path'] for x in manifest]
    fixtures={'wordpress/deploy/verify-checkout-direct-port.php':'wordpress/deploy/verify-production-checkout.php','wordpress/deploy/verify-delivery-rules.php':'wordpress/deploy/verify-delivery-rules.php','wordpress/deploy/probe-delivery-cart.php':'wordpress/deploy/probe-delivery-cart.php','qa/checkout/geography-points.json':'qa/checkout/geography-points.json'}
    targets=['candidate/'+p for p in paths]+list(fixtures)
    dirs=sorted({str(pathlib.PurePosixPath(work+'/'+p).parent) for p in targets})
    run(None,'set -euo pipefail\numask 077\nmkdir -p '+ ' '.join(map(shlex.quote,dirs)))
    for item in manifest:
        write_private(None,work+'/candidate/'+item['path'],pathlib.Path('wordpress/'+item['path']).read_text())
    for dest,src in fixtures.items():write_private(None,work+'/'+dest,pathlib.Path(src).read_text())
    # Core helper must be installed before its consumers; rollback restores all originals.
    manifest.sort(key=lambda x:0 if x['path'].endswith('/class-rollsbar-core.php') else 1)
    lines=['set -euo pipefail','umask 077','export PATH="$HOME/.local/bin:$PATH"','root="$HOME/www/rollsbar.ru"','work='+shlex.quote(work),'backup="$HOME/rollsbar-backups/production-runtime-'+candidate+'"',
      '[[ "$(wp --path="$root" --skip-plugins --skip-themes option get blog_public)" == 0 ]]','[[ -f "$HOME/.rollsbar-production-backend-verified" ]]','[[ ! -e "$backup" ]]','mkdir -p "$backup/files"']
    for item in manifest:
        p=item['path'];lines+=['[[ "$(sha256sum "$root/'+p+'" | cut -d" " -f1)" == '+item['before']+' ]]','[[ "$(sha256sum "$work/candidate/'+p+'" | cut -d" " -f1)" == '+item['after']+' ]]','php -l "$work/candidate/'+p+'" >/dev/null','mkdir -p "$backup/files/'+str(pathlib.PurePosixPath(p).parent)+'"','cp -p "$root/'+p+'" "$backup/files/'+p+'"']
    lines+=['wp --path="$root" --skip-plugins --skip-themes db export "$backup/database.sql" --quiet >/dev/null','gzip "$backup/database.sql"']
    restore='; '.join('cp -p "$backup/files/'+i['path']+'" "$root/'+i['path']+'"' for i in reversed(manifest))+'; wp --path="$root" transient delete wc_shipping_method_count >/dev/null'
    lines+=['rollback() { '+restore+'; echo runtime_rollback=PASS; }',"trap 'rollback' ERR"]
    for item in manifest:lines+=['chmod 644 "$work/candidate/'+item['path']+'"','mv "$work/candidate/'+item['path']+'" "$root/'+item['path']+'"']
    lines+=['wp --path="$root" transient delete wc_shipping_method_count >/dev/null','wp --path="$root" eval-file "$work/wordpress/deploy/verify-delivery-rules.php" >"$backup/native-fixture.log" 2>&1','grep -q DELIVERY_GEOGRAPHY_NATIVE_PASS "$backup/native-fixture.log"','grep -q CHECKOUT_NOTE_NATIVE_FIXTURE_PASS_NO_ORDERS "$backup/native-fixture.log"','wp --path="$root" eval \'if (!RollsBar_Core::checkout_runtime_enabled()) { exit(1); } echo "production_runtime_gate=PASS\\n";\'','trap - ERR','echo native_checkout_delivery_regressions=PASS','printf "native_assertions="; grep -c "^PASS " "$backup/native-fixture.log"','echo production_code_promotion=PASS']
    print(run(None,'\n'.join(lines),timeout=300),flush=True)
    state['promoted_release']=candidate;write_private(None,SECRET,json.dumps(state))
    write_private(None,'.rollsbar-production-release-sha',candidate)

if __name__=='__main__':
    try:main()
    except Exception as exc:print('production_runtime_promotion_failed=true; type='+type(exc).__name__);raise SystemExit(1)

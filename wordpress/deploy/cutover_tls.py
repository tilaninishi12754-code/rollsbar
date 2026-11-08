"""Issue and verify trusted TLS for the prepared production domain and www alias."""
import json,socket,ssl,time,subprocess,re
import recovery_drill as core
from cutover_prepare import connect,write_private,SECRET,RELEASE

def read_state():
    client=connect();sftp=client.open_sftp()
    try:
        with sftp.open(SECRET) as fh:return json.loads(fh.read().decode())
    finally:sftp.close();client.close()

def trusted_tls(domain):
    try:
        with socket.create_connection(('37.140.192.67',443),timeout=8) as raw:
            with ssl.create_default_context().wrap_socket(raw,server_hostname=domain) as secure:
                secure.getpeercert()
                return True
    except (OSError,ssl.SSLError):return False

def form_values(root):return {n.tag:n.text for n in root.iter() if not list(n)}

def attach(sid,cert):
    values=form_values(core.api_call({'out':'xml','func':'webdomain.edit','auth':sid,'elid':'rollsbar.ru'}))
    if values.get('name')!='rollsbar.ru':raise RuntimeError('Unexpected target site')
    if values.get('secure')=='on' and values.get('ssl_cert')==cert:return
    params={'out':'xml','func':'webdomain.edit','auth':sid,'sok':'ok','elid':'rollsbar.ru','name':'rollsbar.ru','aliases':'www.rollsbar.ru','home':'www/rollsbar.ru','owner':core.USER,'ipaddrs':'37.140.192.67','email':values.get('email') or 'tilaninishi12754@gmail.com','charset':values.get('charset') or 'off','dirindex':'index.php index.html','php':'on','php_mode':values.get('php_mode') or 'php_mode_fcgi_apache','log_access':'on','log_error':'on','secure':'on','ssl_cert':cert,'comment':'Rolls Bar production'}
    core.api_call(params)

def main():
    state=read_state()
    if state.get('release')!=RELEASE or state.get('phase') not in ('prepared_maintenance','tls_ready_maintenance'):raise RuntimeError('Production not prepared')
    for ns in ('ns1.reg.ru','ns2.reg.ru'):
        for domain in ('rollsbar.ru','www.rollsbar.ru'):
            answer=subprocess.check_output(['dig','+short','@'+ns,domain,'A'],text=True,timeout=15).split()
            if answer!=['37.140.192.67']:raise RuntimeError('Authoritative DNS is not ready')
    print('authoritative_dns_both_nameservers=PASS',flush=True)
    sid=core.auth()
    if not state.get('tls_requested') and not (trusted_tls('rollsbar.ru') and trusted_tls('www.rollsbar.ru')):
        # This REG.RU form accepts one primary domain; its WWW aliases belong to
        # the prepared webdomain and are handled by the hosting integration.
        core.api_call({'out':'xml','func':'letsencrypt.generate','auth':sid,'sok':'ok','domain_name':'rollsbar.ru','domain':'rollsbar.ru','email':'tilaninishi12754@gmail.com','keylen':'2048','enable_cert':'on','wildcard':'off','dns_check':'off'})
        state['tls_requested']=True;write_private(None,SECRET,json.dumps(state))
        print('trusted_certificate_request_submitted=true',flush=True)
    deadline=time.monotonic()+480
    while time.monotonic()<deadline:
        if trusted_tls('rollsbar.ru') and trusted_tls('www.rollsbar.ru'):
            state['phase']='tls_ready_maintenance';write_private(None,SECRET,json.dumps(state))
            print('trusted_tls_main_and_www=PASS',flush=True);return
        rows=core.rows(core.api_call({'out':'xml','func':'sslcert','auth':sid}))
        candidates=[r for r in rows if (r.get('name','')=='rollsbar.ru' or r.get('name','').startswith('rollsbar.ru_')) and r.get('type') and r.get('type')!='ssl_selfsigned']
        if candidates:
            name=candidates[-1].get('name') or candidates[-1].get('key')
            if name:attach(sid,name)
        time.sleep(15)
    raise RuntimeError('Trusted certificate still pending; do not expose WordPress yet')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('production_tls_failed=true; type='+type(exc).__name__)
        for field in ('type','object','name','code'):
            match=re.search("'"+field+"': '([A-Za-z0-9_.-]+)'",str(exc))
            if match:print('certificate_error_'+field+'='+match.group(1))
        raise SystemExit(1)

"""REG.RU issues a certificate for one hostname per request; give www its own vhost.
Both vhosts use the same prepared content, with www redirecting to the canonical site.
"""
import json,time
import recovery_drill as core
from cutover_prepare import write_private,SECRET,RELEASE
from cutover_tls import read_state,trusted_tls,form_values

def main():
    state=read_state()
    if state.get('release')!=RELEASE or state.get('phase')!='prepared_maintenance' or not trusted_tls('rollsbar.ru'):raise RuntimeError('Main TLS gate')
    sid=core.auth()
    def edit(domain,aliases,secure,certificate):
        v=form_values(core.api_call({'out':'xml','func':'webdomain.edit','auth':sid,'elid':domain}))
        if v.get('name')!=domain:raise RuntimeError('Unexpected site edit target')
        params={'out':'xml','func':'webdomain.edit','auth':sid,'sok':'ok','elid':domain,'name':domain,'aliases':aliases,'home':'www/rollsbar.ru','owner':core.USER,'ipaddrs':'37.140.192.67','email':v.get('email') or 'tilaninishi12754@gmail.com','charset':v.get('charset') or 'off','dirindex':'index.php index.html','php':'on','php_mode':v.get('php_mode') or 'php_mode_fcgi_apache','log_access':'on','log_error':'on','secure':secure,'comment':'Rolls Bar production canonical/www'}
        if certificate:params['ssl_cert']=certificate
        core.api_call(params)
    main_form=form_values(core.api_call({'out':'xml','func':'webdomain.edit','auth':sid,'elid':'rollsbar.ru'}))
    if main_form.get('aliases','').strip():
        if main_form['aliases'].strip()!='www.rollsbar.ru':raise RuntimeError('Unexpected alias to preserve')
        edit('rollsbar.ru','','on',main_form.get('ssl_cert'))
    sites=core.rows(core.api_call({'out':'xml','func':'webdomain','auth':sid}))
    if not any(r.get('name')=='www.rollsbar.ru' for r in sites):
        core.api_call({'out':'xml','func':'webdomain.edit','auth':sid,'sok':'ok','name':'www.rollsbar.ru','aliases':'','home':'www/rollsbar.ru','owner':core.USER,'ipaddrs':'37.140.192.67','email':main_form.get('email') or 'tilaninishi12754@gmail.com','charset':'off','dirindex':'index.php index.html','php':'on','php_mode':main_form.get('php_mode') or 'php_mode_fcgi_apache','log_access':'on','log_error':'on','secure':'off','comment':'Rolls Bar www canonical redirect'})
    if not state.get('tls_www_requested') and not trusted_tls('www.rollsbar.ru'):
        core.api_call({'out':'xml','func':'letsencrypt.generate','auth':sid,'sok':'ok','domain_name':'www.rollsbar.ru','domain':'www.rollsbar.ru','email':'tilaninishi12754@gmail.com','keylen':'2048','enable_cert':'on','wildcard':'off','dns_check':'off'})
        state['tls_www_requested']=True;write_private(None,SECRET,json.dumps(state))
        print('www_certificate_request_submitted=true',flush=True)
    deadline=time.monotonic()+480
    while time.monotonic()<deadline:
        if trusted_tls('rollsbar.ru') and trusted_tls('www.rollsbar.ru'):
            state['phase']='tls_ready_maintenance';write_private(None,SECRET,json.dumps(state))
            print('trusted_tls_main_and_www=PASS',flush=True);return
        rows=core.rows(core.api_call({'out':'xml','func':'sslcert','auth':sid}))
        certs=[r for r in rows if (r.get('name','')=='www.rollsbar.ru' or r.get('name','').startswith('www.rollsbar.ru_')) and r.get('type') and r.get('type')!='ssl_selfsigned']
        if certs:edit('www.rollsbar.ru','','on',certs[-1].get('name') or certs[-1].get('key'))
        time.sleep(15)
    raise RuntimeError('WWW TLS pending')

if __name__=='__main__':
    try:main()
    except Exception as exc:print('www_tls_failed=true; type='+type(exc).__name__);raise SystemExit(1)

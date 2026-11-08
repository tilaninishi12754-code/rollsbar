import re
import recovery_drill as core
sid=core.auth()
rows=core.rows(core.api_call({'out':'xml','func':'sslcert','auth':sid}))
for domain in ('rollsbar.ru','www.rollsbar.ru'):
    selected=[r for r in rows if r.get('name','')==domain or r.get('name','').startswith(domain+'_')]
    print(('main' if domain=='rollsbar.ru' else 'www')+'_trusted_certificate_object='+str(any(r.get('type') and r.get('type')!='ssl_selfsigned' for r in selected)).lower())
    for r in selected:
        cert=r.get('name') or r.get('key')
        try:
            root=core.api_call({'out':'xml','func':'letsencrypt.logs','auth':sid,'elid':domain,'sslcert':cert})
            text=' '.join(root.itertext()).lower()
            label='main' if domain=='rollsbar.ru' else 'www'
            patterns={'http_404':r'\b404\b','http_403':r'\b403\b','http_503':r'\b503\b','rate_limit':r'rate.?limit|too many','dns_issue':r'nxdomain|dns problem|no valid ip|incorrect.*dns','timeout':r'timed out|timeout|время ожидания','invalid_response':r'invalid response|unauthorized','issued':r'successfully|успешно|certificate.*issued','pending':r'pending|ожидани|will.*retry|следующ'}
            for name,pattern in patterns.items():print(label+'_certificate_log_'+name+'='+str(bool(re.search(pattern,text))).lower())
        except Exception as exc:
            print(('main' if domain=='rollsbar.ru' else 'www')+'_certificate_log_unavailable=true')

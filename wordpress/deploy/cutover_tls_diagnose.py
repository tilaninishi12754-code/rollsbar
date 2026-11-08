import ast,re,json
import recovery_drill as core
from cutover_tls import form_values

sid=core.auth()
rows=core.rows(core.api_call({'out':'xml','func':'sslcert','auth':sid}))
matches=[r for r in rows if (r.get('name','')=='rollsbar.ru' or r.get('name','').startswith('rollsbar.ru_'))]
print('main_certificate_object_exists='+str(bool(matches)).lower())
print('main_certificate_trusted_type='+str(any(r.get('type') and r.get('type')!='ssl_selfsigned' for r in matches)).lower())
try:
    form=core.api_call({'out':'xml','func':'letsencrypt.generate','auth':sid,'domain':'rollsbar.ru'})
    v=form_values(form)
    fields=sorted({n.attrib['name'] for n in form.iter() if 'name' in n.attrib and re.fullmatch('[a-z_]+',n.attrib['name'])})
    print('certificate_form_field_names='+json.dumps(fields))
    print('default_names_include_main='+str('rollsbar.ru' in (v.get('domain_name') or '')).lower())
    print('default_names_include_www='+str('www.rollsbar.ru' in (v.get('domain_name') or '')).lower())
except Exception as exc:
    text=str(exc)
    for field in ('type','object','name','code'):
        m=re.search("'"+field+"': '([A-Za-z0-9_.-]+)'",text)
        if m:print('certificate_form_error_'+field+'='+m.group(1))

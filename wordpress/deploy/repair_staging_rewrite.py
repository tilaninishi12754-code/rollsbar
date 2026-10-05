#!/usr/bin/env python3
"""Repair missing WordPress .htaccess on the isolated REG.RU staging site."""
from __future__ import annotations
import os, shlex, socket, urllib.request, urllib.error
from urllib.parse import urlsplit
import paramiko
BASE=os.environ['ISP_MANAGER_URL'].strip(); USER=os.environ['ISP_MANAGER_USER'].strip(); PASSWORD=os.environ['ISP_MANAGER_PASSWORD'].strip(); DOMAIN='staging.rollsbar.ru'; CONFIRM=os.environ.get('ROLLSBAR_CONFIRM_REWRITE_REPAIR','')
RULES='''# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
'''
def connect():
    host=urlsplit(BASE).hostname or ''
    c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy()); c.connect(hostname=host,port=22,username=USER,password=PASSWORD,timeout=15,auth_timeout=15,banner_timeout=15,look_for_keys=False,allow_agent=False); return c
def status(url):
    try: return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'rollsbar-rewrite-repair/1.0'}),timeout=15).status
    except urllib.error.HTTPError as e: return e.code
if CONFIRM!='YES': raise SystemExit('Refusing mutation without confirmation')
c=None
try:
    c=connect(); sftp=c.open_sftp(); path=f'www/{DOMAIN}/.htaccess'
    try:
        with sftp.open(path,'r') as f: old=f.read().decode('utf-8','replace')
    except FileNotFoundError: old=''
    if old and 'RewriteEngine On' in old:
        print('rewrite_file=already_present mutation=skipped')
    else:
        if old:
            with sftp.open(path+'.pre-rollsbar-backup','w') as b: b.write(old.encode())
        with sftp.open(path,'w') as f: f.write(RULES.encode())
        sftp.chmod(path,0o644); print('rewrite_file=created')
    sftp.close()
    base='https://'+DOMAIN
    cart=status(base+'/cart/'); account=status(base+'/my-account/')
    print(f'cart_status={cart}'); print(f'myaccount_status={account}')
    if not (200 <= cart < 400 and 200 <= account < 400): raise RuntimeError('pretty permalink verification failed')
    print('STAGING REWRITE REPAIR PASS')
except Exception as exc:
    print(f'rewrite_repair=failed type={exc.__class__.__name__}'); raise
finally:
    if c: c.close()

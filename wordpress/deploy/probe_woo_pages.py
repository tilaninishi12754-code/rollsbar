#!/usr/bin/env python3
from __future__ import annotations
import os, shlex, socket, urllib.request, urllib.error
from urllib.parse import urlsplit
import paramiko
BASE=os.environ['ISP_MANAGER_URL'].strip(); USER=os.environ['ISP_MANAGER_USER'].strip(); PASSWORD=os.environ['ISP_MANAGER_PASSWORD'].strip(); DOMAIN='staging.rollsbar.ru'
def connect():
    host=urlsplit(BASE).hostname or ''
    c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(hostname=host,port=22,username=USER,password=PASSWORD,timeout=15,auth_timeout=15,banner_timeout=15,look_for_keys=False,allow_agent=False); return c
def run(c,cmd):
    _,o,e=c.exec_command('bash -lc '+shlex.quote(cmd),timeout=90); out=o.read().decode(); err=e.read().decode(); st=o.channel.recv_exit_status(); print(out,end='' if out.endswith('\n') else '\n');
    if st: print('stderr='+err[-1000:]); raise RuntimeError(st)
def http_status(url):
    try:
        r=urllib.request.urlopen(urllib.request.Request(url,method='GET',headers={'User-Agent':'rollsbar-probe/1.0'}),timeout=15); return r.status
    except urllib.error.HTTPError as e: return e.code
client=None
try:
    client=connect()
    php=r'''$keys=array("cart"=>"woocommerce_cart_page_id","checkout"=>"woocommerce_checkout_page_id","myaccount"=>"woocommerce_myaccount_page_id"); foreach($keys as $label=>$opt){$id=(int)get_option($opt);$p=$id?get_post($id):null;echo $label."_id=".$id."\n";echo $label."_slug=".($p?$p->post_name:"")."\n";echo $label."_url=".($id?get_permalink($id):"")."\n";} echo "wc_cart_url=".wc_get_cart_url()."\n"; echo "wc_checkout_url=".wc_get_checkout_url()."\n";'''
    cmd=f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
WP_PATH="$HOME/www/{DOMAIN}"
wp --path="$WP_PATH" eval {shlex.quote(php)}
printf 'htaccess_exists='; test -f "$WP_PATH/.htaccess" && echo yes || echo no
if test -f "$WP_PATH/.htaccess"; then printf 'htaccess_size='; wc -c < "$WP_PATH/.htaccess"; grep -q 'RewriteEngine On' "$WP_PATH/.htaccess" && echo 'htaccess_rewrite=yes' || echo 'htaccess_rewrite=no'; fi
printf 'rewrite_rule_count='; wp --path="$WP_PATH" rewrite list --format=count
printf 'mutation=not attempted\n'
'''
    run(client,cmd)
    base='https://'+DOMAIN
    for path in ['/cart/','/checkout/','/my-account/','/?page_id=6','/?page_id=7','/?page_id=8']:
        print(f'http_{path}={http_status(base+path)}')
    print('WOO PAGE ROUTING PROBE PASS')
except Exception as exc:
    print(f'woo_page_probe=failed type={exc.__class__.__name__}'); raise
finally:
    if client: client.close()

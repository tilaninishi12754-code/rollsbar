"""Prepare an isolated production site from a frozen application and sanitized content.
Private config and database content remain on the original hosting account.
"""
import os,json,pathlib,hashlib,shlex,time,secrets,stat
import paramiko
import recovery_drill as core
import recovery_drill_reg_ru as adapter
from precutover_backup import PinnedHostKey

RELEASE='d4b41c59f0a6101666450723c324d25a28585c35'
SECRET='.rollsbar-production-db.json'
STEP='preflight'

def run(client,script,timeout=600):
    status,out,err=core.remote(client,script,timeout=timeout)
    if status: raise RuntimeError('remote_failed_'+str(status))
    return out

def write_private(client,path,body):
    sftp=client.open_sftp()
    try:
        with sftp.open(path,'w') as fh:
            sftp.chmod(path,0o600);fh.write(body.encode())
    finally:sftp.close()

def check_release(client):
    out=run(client,'set -euo pipefail\ncd "$HOME/www/staging.rollsbar.ru"\nfind wp-content/themes/rollsbar-theme wp-content/plugins/rollsbar-core -type f -print0 | sort -z | xargs -0 sha256sum')
    actual={line.split(maxsplit=1)[1]:line.split(maxsplit=1)[0] for line in out.splitlines()}
    expected={}
    for folder in ('wordpress/wp-content/themes/rollsbar-theme','wordpress/wp-content/plugins/rollsbar-core'):
        for p in pathlib.Path(folder).rglob('*'):
            if p.is_file():expected[str(p).removeprefix('wordpress/')]=hashlib.sha256(p.read_bytes()).hexdigest()
    for p in pathlib.Path('wordpress/data/product-media').rglob('*'):
        if p.is_file():expected['wp-content/plugins/rollsbar-core/data/product-media/'+str(p.relative_to('wordpress/data/product-media'))]=hashlib.sha256(p.read_bytes()).hexdigest()
    expected['wp-content/plugins/rollsbar-core/data/catalog.json']=hashlib.sha256(pathlib.Path('wordpress/data/catalog.json').read_bytes()).hexdigest()
    if any(actual.get(p)!=digest for p,digest in expected.items() if p in actual or not p.startswith('wp-content/plugins/rollsbar-core/data/product-media/')):raise RuntimeError('Release byte mismatch')
    if any(p not in expected for p in actual):raise RuntimeError('Unrecognized runtime package files')
    print('release_and_runtime_package=PASS',flush=True)

def provision_db(client,sid):
    sftp=client.open_sftp()
    try:
        try:
            if stat.S_ISLNK(sftp.lstat(SECRET).st_mode):raise RuntimeError('Linked credentials')
            with sftp.open(SECRET) as fh: data=json.loads(fh.read().decode())
        except FileNotFoundError:data=None
    finally:sftp.close()
    target=adapter.list_target(sid,'rollsbar_prod')
    if target is not None and data is None:raise RuntimeError('Unowned production database exists')
    if data is None:
        data={'password':secrets.token_urlsafe(36),'release':RELEASE,'phase':'initializing'}
        core.mask(data['password']);write_private(client,SECRET,json.dumps(data))
    if data.get('release')!=RELEASE or data.get('phase')!='initializing':raise RuntimeError('Refusing to overwrite prepared or different release')
    core.mask(data['password'])
    if target is None:
        core.api_call({'out':'xml','func':'db.edit','auth':sid,'sok':'ok','name':'rollsbar_prod','owner':core.USER,'server':'MySQL8','charset':'utf8mb4','user':'*','username':'rollsbar_prod','password':data['password'],'confirm':data['password'],'remote_access':'off','comment':'RollsBar production, owner authorized 2026-11-08'})
    target=adapter.wait_until_ready(sid,'rollsbar_prod')
    if not target:raise RuntimeError('Production DB not provisioned')
    data.update({'database':target['name'],'user':adapter.find_actual_user(sid,'rollsbar_prod',target['pair']),'host':'localhost'})
    write_private(client,SECRET,json.dumps(data));return data

def main():
    global STEP
    sid=core.auth();client=paramiko.SSHClient();client.set_missing_host_key_policy(PinnedHostKey())
    client.connect(core.urlsplit(core.BASE).hostname,username=core.USER,password=core.PASSWORD,look_for_keys=False,allow_agent=False,timeout=20)
    temp_name='rbdrill_'+str(int(time.time())%100000000).zfill(8)
    temp_db=temp_user=temp_pair=temp_id='';temp_attempt=False
    temp_password=secrets.token_urlsafe(36);core.mask(temp_password)
    temp_cfg='.rollsbar-cutover-'+secrets.token_hex(6)+'.cnf'
    work=None
    try:
        check_release(client)
        # An existing prepared site is never overwritten by repeating this operation.
        run(client,'set -euo pipefail\n[[ ! -e "$HOME/www/rollsbar.ru/wp-config.php" ]]\n[[ -f "$HOME/rollsbar-backups/precutover/20261107T222121Z/SHA256SUMS" ]]\n(cd "$HOME/rollsbar-backups/precutover/20261107T222121Z";sha256sum -c SHA256SUMS >/dev/null)\necho source_rollback_gate=PASS')
        canonical=pathlib.Path('wordpress/deploy/backup-staging.sh').read_text()
        backup=run(client,'export PATH="$HOME/.local/bin:$PATH"\nexport WP_PATH="$HOME/www/staging.rollsbar.ru"\nexport ROLLSBAR_BACKUP_RETENTION=9999\n'+canonical,timeout=900)
        if 'BACKUP VERIFIED PASS' not in backup:raise RuntimeError('Fresh backup failed')
        snapshot=next(line.split('=',1)[1] for line in backup.splitlines() if line.startswith('backup_location='))
        print('fresh_source_backup=PASS',flush=True)
        STEP='create_closed_production_site'
        sites=core.rows(core.api_call({'out':'xml','func':'webdomain','auth':sid}))
        if not any(r.get('name')=='rollsbar.ru' for r in sites):
            root=core.api_call({'out':'xml','func':'webdomain.edit','auth':sid,'elid':'staging.rollsbar.ru'})
            values={n.tag:n.text for n in root.iter() if not list(n)}
            core.api_call({'out':'xml','func':'webdomain.edit','auth':sid,'sok':'ok','name':'rollsbar.ru','aliases':'www.rollsbar.ru','home':'www/rollsbar.ru','owner':core.USER,'ipaddrs':'37.140.192.67','email':values.get('email') or 'tilaninishi12754@gmail.com','charset':'off','dirindex':'index.php index.html','php':'on','php_mode':values.get('php_mode') or 'php_mode_fcgi_apache','log_access':'on','log_error':'on','secure':'off','comment':'Rolls Bar production'})
        run(client,'set -euo pipefail\numask 077\nroot="$HOME/www/rollsbar.ru"\n[[ -d "$root" && ! -L "$root" && "$(realpath "$root")" == "$root" ]]\nprintf "Require all denied\\n" > "$root/.htaccess"\nchmod 644 "$root/.htaccess"')
        prod=provision_db(client,sid)
        print('isolated_production_site_and_database=PASS',flush=True)
        STEP='prepare_temporary_migration_database';temp_attempt=True
        temp_db,temp_user,temp_pair,temp_id=adapter.create_temp_db(sid,temp_name,temp_password)
        core.write_client_config(client,temp_cfg,temp_user,temp_password)
        command=r'''set -euo pipefail
umask 077
export PATH="$HOME/.local/bin:$PATH"
work="$HOME/.rollsbar-cutover-work-20261108"
[[ ! -e "$work" ]]
mkdir "$work"
mkdir "$work/site"
tar -C "$HOME/www/staging.rollsbar.ru" --exclude='./wp-content/debug.log' --exclude='./debug.log' --exclude='./wp-content/cache' -cf - . | tar -C "$work/site" -xf -
printf '%s' "$work"
'''
        work=run(client,command).strip()
        wp='wp --path='+shlex.quote(work+'/site')+' --skip-plugins --skip-themes '
        cfg='$HOME/'+temp_cfg
        setup='set -euo pipefail\nexport PATH="$HOME/.local/bin:$PATH"\n'
        setup+='gzip -dc '+shlex.quote(snapshot+'/database.sql.gz')+' | mysql --defaults-extra-file="'+cfg+'" '+shlex.quote(temp_db)+' >/dev/null\n'
        for name,value in [('DB_NAME',temp_db),('DB_USER',temp_user),('DB_PASSWORD',temp_password),('DB_HOST','localhost'),('WP_ENVIRONMENT_TYPE','staging')]:setup+=wp+'config set '+name+' '+shlex.quote(value)+' >/dev/null\n'
        setup+=wp+'config set DISABLE_WP_CRON true --raw >/dev/null\n'
        setup+=wp+'config set WP_DEBUG false --raw >/dev/null\n'
        run(client,setup)
        write_private(client,work+'/sanitize.php',pathlib.Path('wordpress/deploy/cutover_sanitize.php').read_text())
        STEP='sanitize_and_transform_content'
        clean='set -euo pipefail\nexport PATH="$HOME/.local/bin:$PATH"\nexport CUTOVER_TEMP_DB='+shlex.quote(temp_db)+'\n'
        clean+=wp+'eval-file '+shlex.quote(work+'/sanitize.php')+'\n'
        clean+=wp+'search-replace https://staging.rollsbar.ru https://rollsbar.ru --all-tables-with-prefix --skip-columns=guid --precise --dry-run >/dev/null\n'
        clean+=wp+'search-replace https://staging.rollsbar.ru https://rollsbar.ru --all-tables-with-prefix --skip-columns=guid --precise >/dev/null\n'
        clean+=wp+'search-replace http://staging.rollsbar.ru https://rollsbar.ru --all-tables-with-prefix --skip-columns=guid --precise >/dev/null\n'
        clean+=wp+'option update home https://rollsbar.ru >/dev/null\n'+wp+'option update siteurl https://rollsbar.ru >/dev/null\n'
        clean+=wp+'db export - --single-transaction --quick --skip-lock-tables 2>/dev/null | gzip -9 > '+shlex.quote(work+'/production-content.sql.gz')+'\n'
        clean+='gzip -t '+shlex.quote(work+'/production-content.sql.gz')+'\n'
        out=run(client,clean);print('sanitized_content_and_url_transform=PASS',flush=True)
        STEP='install_isolated_production_content'
        prod_cfg='.rollsbar-production-import-'+secrets.token_hex(6)+'.cnf'
        core.write_client_config(client,prod_cfg,prod['user'],prod['password'])
        try:
            script='set -euo pipefail\numask 077\nexport PATH="$HOME/.local/bin:$PATH"\nroot="$HOME/www/rollsbar.ru"\n'
            script+='[[ ! -f "$root/wp-config.php" ]]\n'
            script+='tar -C '+shlex.quote(work+'/site')+' --exclude=./.htaccess --exclude=./wp-config.php -cf - . | tar -C "$root" -xf -\n'
            script+='cp '+shlex.quote(work+'/site/wp-config.php')+' "$root/wp-config.php"\nchmod 600 "$root/wp-config.php"\n'
            prodwp='wp --path="$root" --skip-plugins --skip-themes '
            for name,value in [('DB_NAME',prod['database']),('DB_USER',prod['user']),('DB_PASSWORD',prod['password']),('DB_HOST','localhost'),('WP_ENVIRONMENT_TYPE','production'),('WP_HOME','https://rollsbar.ru'),('WP_SITEURL','https://rollsbar.ru')]:script+=prodwp+'config set '+name+' '+shlex.quote(value)+' >/dev/null\n'
            script+=prodwp+'config set WP_DEBUG false --raw >/dev/null\n'+prodwp+'config set WP_DEBUG_DISPLAY false --raw >/dev/null\n'+prodwp+'config set DISABLE_WP_CRON true --raw >/dev/null\n'
            for salt in ('AUTH_KEY','SECURE_AUTH_KEY','LOGGED_IN_KEY','NONCE_KEY','AUTH_SALT','SECURE_AUTH_SALT','LOGGED_IN_SALT','NONCE_SALT'):
                script+=prodwp+'config set '+salt+' "$(openssl rand -base64 48)" >/dev/null\n'
            script+='gzip -dc '+shlex.quote(work+'/production-content.sql.gz')+' | mysql --defaults-extra-file="$HOME/'+prod_cfg+'" '+shlex.quote(prod['database'])+' >/dev/null\n'
            script+=prodwp+'core is-installed >/dev/null\n'
            script+='[[ "$('+prodwp+'option get home)" == https://rollsbar.ru ]]\n[[ "$('+prodwp+'option get blog_public)" == 0 ]]\n'
            script+='[[ "$('+prodwp+'post list --post_type=product --post_status=publish --format=count)" == 121 ]]\n'
            script+='cp '+shlex.quote(work+'/site/.htaccess')+' "$HOME/.rollsbar-production-final-htaccess"\n'
            script+='chmod 600 "$HOME/.rollsbar-production-final-htaccess"\n'
            script+='printf \'<!doctype html><html lang="ru"><meta charset="utf-8"><title>Rolls Bar</title><h1>Rolls Bar</h1><p>РЎР°Р№С‚ РѕР±РЅРѕРІР»СЏРµС‚СЃСЏ. РЎРєРѕСЂРѕ РІРµСЂРЅС‘РјСЃСЏ.</p></html>\' > "$root/cutover-maintenance.html"\n'
            script+='printf \'RewriteEngine On\\nRewriteCond %%{REQUEST_URI} !^/\\.well-known/acme-challenge/\\nRewriteCond %%{REQUEST_URI} !^/cutover-maintenance\\.html$\\nRewriteRule ^ - [R=503,L]\\nErrorDocument 503 /cutover-maintenance.html\\nHeader always set Retry-After "300"\\nHeader always set X-Robots-Tag "noindex, nofollow"\\n\' > "$root/.htaccess"\n'
            script+='chmod 640 "$root/wp-config.php"\nchmod 644 "$root/.htaccess"\n'
            script+='printf '+shlex.quote(RELEASE)+' > "$HOME/.rollsbar-production-release-sha"\nchmod 600 "$HOME/.rollsbar-production-release-sha"\n'
            script+='backup="$HOME/rollsbar-backups/production-initial-20261108"\n[[ ! -e "$backup" ]]\nmkdir "$backup"\n'
            script+=prodwp+'db export - --single-transaction --quick --skip-lock-tables 2>/dev/null | gzip -9 > "$backup/database.sql.gz"\n'
            script+='cp "$root/wp-config.php" "$root/.htaccess" "$backup/"\n(cd "$backup"; sha256sum database.sql.gz wp-config.php .htaccess > SHA256SUMS;sha256sum -c SHA256SUMS >/dev/null)\nchmod 600 "$backup"/*\n'
            run(client,script,timeout=900)
        finally:
            sftp=client.open_sftp()
            try:sftp.remove(prod_cfg)
            finally:sftp.close()
        check_release(client)
        prod['phase']='prepared_maintenance';write_private(client,SECRET,json.dumps(prod))
        print('production_prepared_in_maintenance=PASS',flush=True)
        print('production_catalog_and_urls=PASS',flush=True)
        print('staging_application_unchanged=PASS',flush=True)
    finally:
        if work:
            run(client,'set -euo pipefail\nwork='+shlex.quote(work)+'\n[[ "$work" == "$HOME/.rollsbar-cutover-work-20261108" && "$(realpath "$work")" == "$work" ]]\nrm -rf -- "$work"')
        sftp=client.open_sftp()
        try:
            try:sftp.remove(temp_cfg)
            except FileNotFoundError:pass
        finally:sftp.close()
        if temp_attempt:
            errors=adapter.cleanup_temp_db(sid,temp_name,temp_user,temp_pair,temp_id)
            print('temporary_migration_database_cleanup='+('PASS' if not errors else 'FAIL'),flush=True)
            if errors:raise RuntimeError('Temporary cleanup failed')
        client.close()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('cutover_prepare_failed=true; stage='+STEP+'; type='+type(exc).__name__,flush=True)
        if isinstance(exc,paramiko.SSHException):
            known=next((r for r in ('Channel closed','SSH session not active','Unable to open channel','Timeout') if r.lower() in str(exc).lower()),'other_ssh_error')
            print('connection_failure_class='+known,flush=True)
        raise SystemExit(1)

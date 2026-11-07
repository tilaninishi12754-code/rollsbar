"""Restore the exact full snapshot into isolated resources on the same host only."""
import shlex
import recovery_drill as core
import recovery_drill_reg_ru  # installs the proven REG.RU create/cleanup adapters
from precutover_backup import PinnedHostKey
import paramiko

def pinned_connect():
    client=paramiko.SSHClient();client.set_missing_host_key_policy(PinnedHostKey())
    client.connect(core.urlsplit(core.BASE).hostname,username=core.USER,password=core.PASSWORD,
                   timeout=20,auth_timeout=20,banner_timeout=20,look_for_keys=False,allow_agent=False)
    return client

def restore_full(client, actual_db, config_relpath):
    if not actual_db.endswith(core.current_requested):
        raise RuntimeError('Temporary database identity mismatch')
    script=r'''set -euo pipefail
umask 077
snapshot="$HOME/rollsbar-backups/precutover/20261107T222121Z"
[[ -d "$snapshot" && ! -L "$snapshot" && "$(realpath "$snapshot")" == "$snapshot" ]] || exit 21
(cd "$snapshot"; sha256sum -c SHA256SUMS >/dev/null)
echo 'full_snapshot_checksums=PASS'
gzip -t "$snapshot/database.sql.gz"
tar -tzf "$snapshot/site-files.tar.gz" >/dev/null
work="$snapshot/restore-proof-$$"
[[ ! -e "$work" ]] || exit 22
mkdir "$work"
cleanup(){
 [[ "$work" == "$snapshot"/restore-proof-* && "$(realpath "$work")" == "$work" ]] && rm -rf -- "$work"
}
trap cleanup EXIT
tar -xzf "$snapshot/site-files.tar.gz" -C "$work" --same-permissions --no-same-owner
tar -dzf "$snapshot/site-files.tar.gz" -C "$work" >/dev/null
[[ -s "$work/wp-config.php" && -f "$work/wp-load.php" && -d "$work/wp-content/uploads" ]]
php -l "$work/wp-config.php" >/dev/null
php -l "$work/wp-content/plugins/rollsbar-core/rollsbar-core.php" >/dev/null
echo 'full_files_restore_and_compare=PASS'
echo 'restored_php_syntax=PASS'
printf 'restored_files='; find "$work" -type f | wc -l
mysql_bin="$(command -v mysql || command -v mariadb)"
''' + f'cfg="$HOME/"{shlex.quote(config_relpath)}\ndb={shlex.quote(actual_db)}\n' + r'''
[[ "$db" == *rbdrill_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9] ]] || exit 23
gzip -dc "$snapshot/database.sql.gz" | "$mysql_bin" --defaults-extra-file="$cfg" "$db"
echo 'full_database_import_to_isolated_temp=PASS'
query(){ "$mysql_bin" --defaults-extra-file="$cfg" -N -B "$db" -e "$1"; }
options="$(query 'SHOW TABLES;' | grep '_options$' | head -n1)"
[[ "$options" =~ ^[A-Za-z0-9_]+_options$ ]] || exit 24
prefix="${options%options}"
home="$(query "SELECT option_value FROM ${options} WHERE option_name='home' LIMIT 1")"
public="$(query "SELECT option_value FROM ${options} WHERE option_name='blog_public' LIMIT 1")"
products="$(query "SELECT COUNT(*) FROM ${prefix}posts WHERE post_type='product' AND post_status='publish'")"
printf 'restored_home=%s\nrestored_blog_public=%s\nrestored_products=%s\n' "$home" "$public" "$products"
reference="$HOME/rollsbar-backups/staging/20261107T222110Z/manifest.txt"
expected_products="$(awk -F= '$1=="published_products"{print $2}' "$reference")"
expected_public="$(awk -F= '$1=="blog_public"{print $2}' "$reference")"
[[ "$expected_products" =~ ^[0-9]+$ && "$expected_public" =~ ^[01]$ ]] || exit 26
printf 'snapshot_reference_products=%s\nsnapshot_reference_blog_public=%s\n' "$expected_products" "$expected_public"
[[ "$home" == 'https://staging.rollsbar.ru' && "$public" == "$expected_public" && "$products" == "$expected_products" ]] || exit 25
printf 'restored_products=%s\n' "$products"
printf 'restored_tables='; query 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()'
printf 'restored_private_career_applications='; query "SELECT COUNT(*) FROM ${prefix}posts WHERE post_type='rb_job_application' AND post_status='private'"
echo 'full_database_content_invariants=PASS'
'''
    status,out,err=core.remote(client,script,timeout=900)
    if status:
        print(out)
        print('restore_stderr_present='+str(bool(err)))
        raise RuntimeError('Full snapshot restore failed, exit='+str(status))
    return out

original_create=core.create_temp_db
def create_temp_db(sid,requested,password):
    core.current_requested=requested
    return original_create(sid,requested,password)
core.create_temp_db=create_temp_db
core.restore_and_verify=restore_full
core.connect_ssh=pinned_connect
if __name__=='__main__': raise SystemExit(core.main())

"""Backed-up career recipient change and intercepted integration; no real email."""
import shlex
import apply_client_media_staging as t

BASE = 'cab31f46ba19904bbe98df4541c9c186fb3fce02'
FILE = t.PLUGIN + 'includes/class-rollsbar-vacancy-page.php'

sha = t.release_sha()
probe = r'''foreach(['Exception','SMTP','PHPMailer'] as $c)require_once ABSPATH.WPINC.'/PHPMailer/'.$c.'.php';$m=new \PHPMailer\PHPMailer\PHPMailer(true);do_action('phpmailer_init',$m);$m->Timeout=12;$m->getSMTPInstance()->Timelimit=12;$ok=false;try{if($m->Mailer==='smtp')$ok=$m->smtpConnect();}catch(\Throwable $e){}$error=$m->getSMTPInstance()->getError();$m->smtpClose();echo wp_json_encode(['primary'=>RollsBar_Vacancy_Page::RECIPIENT,'copy'=>RollsBar_Vacancy_Page::COPY_RECIPIENT,'smtp_authenticated'=>$ok,'smtp_code'=>$error['smtp_code']??'','messages_sent'=>0]);'''
t.execute(f'''
[[ -z "$(git -C "$PROJECT_ROOT" status --porcelain)" ]]
{t.code_hash_guard(sha, before=True, changed=[FILE], base=BASE)}
git -C "$PROJECT_ROOT" fetch --depth=1 origin {sha}
git -C "$PROJECT_ROOT" checkout --detach {sha}
export WP_PATH PROJECT_ROOT
source "$PROJECT_ROOT/wordpress/deploy/prepare-s1-r2-backup.sh"
[[ "$ROLLSBAR_FRESH_BACKUP_VERIFIED" == YES ]]
snapshot="$HOME/rollsbar-backups/staging/$ROLLSBAR_FRESH_BACKUP_SNAPSHOT"
cp -p "$WP_PATH/{FILE.removeprefix('wordpress/')}" "$snapshot/career-recipients-before.php"
sha256sum "$snapshot/career-recipients-before.php" > "$snapshot/career-recipients-before.sha256"
sha256sum -c "$snapshot/career-recipients-before.sha256"
php -l "$PROJECT_ROOT/{FILE}"
install -m 0644 "$PROJECT_ROOT/{FILE}" "$WP_PATH/{FILE.removeprefix('wordpress/')}.mail-new"
mv -f "$WP_PATH/{FILE.removeprefix('wordpress/')}.mail-new" "$WP_PATH/{FILE.removeprefix('wordpress/')}"
{t.code_hash_guard(sha, changed=[FILE], base=BASE)}
wp_cmd eval-file "$PROJECT_ROOT/wordpress/deploy/verify-careers.php"
wp_cmd eval {shlex.quote(probe)}; echo
printf '%s\n' 'release={sha}' "backup=$ROLLSBAR_FRESH_BACKUP_SNAPSHOT" 'phase=recipients_verified' > "$HOME/.rollsbar-career-recipients-release"
echo CAREER_RECIPIENTS_APPLIED
''')

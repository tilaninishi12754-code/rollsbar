# Access model — least privilege

## Human owner
Keeps the main WordPress owner/admin credentials and hosting billing credentials.

## Codex / automation
Do not share the owner's WordPress password.

Preferred access:
1. GitHub write access only to the Rolls Bar repository.
2. Dedicated SSH/SFTP user limited to the Rolls Bar staging/project directory.
3. WordPress Application Password or a separate WordPress user only when REST/admin actions are actually required.
4. WooCommerce API keys only if store API access is needed, using the minimum required permission (read / write / read-write).

## Secrets
Keep secrets on the server or secret manager. Never commit:
- WordPress passwords;
- Application Passwords;
- WooCommerce API secrets;
- bank/acquiring credentials;
- Telegram bot tokens;
- iKeeper credentials;
- database credentials.

## Production
Automation should not need unrestricted server root access or the owner's permanent WordPress password.

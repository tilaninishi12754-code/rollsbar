#!/usr/bin/env python3
"""Run the fixed, backup-gated RollsBar catalog repair against staging only."""
from __future__ import annotations

import json
import os
import re
import shlex
from pathlib import Path
from urllib.parse import urlsplit

from staging_catalog_audit import AUDIT_PHP, EXPECTED_UPSELLS, parse_audit, validate_catalog_audit

try:
    import paramiko
except ImportError:  # Local contract tests do not need an SSH connection.
    paramiko = None

DOMAIN = "staging.rollsbar.ru"
EXPECTED_SHA = "88826907fc7ffe805a7c47f36c35a74c0049e08e"
PROJECT_ROOT = "$HOME/.rollsbar-deploy"
WP_PATH = "$HOME/www/staging.rollsbar.ru"
BRANCH = "wordpress/checkout-visual-parity-2026-10-25"
CURRENT_STAGE = "startup"
BACKUP_VERIFIED = False
COMMANDS = (
    "wp rollsbar catalog repair_variations --dry-run",
    "wp rollsbar catalog repair_variations",
    "wp rollsbar catalog repair_variations --dry-run",
    "wp rollsbar catalog upsells --dry-run --confirm-staging",
    "wp rollsbar catalog upsells --confirm-staging",
    "wp rollsbar catalog upsells --dry-run --confirm-staging",
    "wp rollsbar catalog repair_variations --dry-run",
)


def job_should_run(job: str, event: str, operation: str, ref_name: str) -> bool:
    """Mirror the workflow's mutually exclusive, branch-pinned job conditions."""
    if job == "deploy":
        return event == "push" or (event == "workflow_dispatch" and operation == "deploy")
    if job == "catalog-maintenance":
        return (event == "workflow_dispatch" and operation == "catalog-maintenance"
                and ref_name == BRANCH)
    raise ValueError("Unknown fixed workflow job")


def validate_variation(payload: dict, *, dry_run: bool, updated: int | None = None) -> None:
    if (payload.get("parents"), payload.get("variations"), payload.get("dry_run")) != (13, 26, dry_run):
        raise RuntimeError("Variation repair result differs from canonical 13/26 contract")
    if updated is not None and payload.get("updated") != updated:
        raise RuntimeError("Variation readback is not idempotent")


def validate_upsell_dry(payload: dict, *, initial: bool) -> None:
    expected = (3, 0) if initial else (0, 3)
    if (payload.get("dry_run"), payload.get("created"), payload.get("existing"),
            payload.get("provisional_price")) != (True, *expected, True):
        raise RuntimeError("Upsell dry-run result differs from the fixed provisional identity contract")


def validate_upsell_mutation(payload: dict) -> None:
    created, existing = payload.get("created"), payload.get("existing")
    if payload.get("dry_run") is not False or payload.get("provisional_price") is not True:
        raise RuntimeError("Upsell mutation did not preserve provisional price provenance")
    if not isinstance(created, int) or not isinstance(existing, int) or created + existing != 3 or created not in (0, 3):
        raise RuntimeError("Upsell mutation result is partial or could have duplicated products")


def parse_success_json(output: str) -> dict:
    for line in reversed(output.splitlines()):
        candidate = line.removeprefix("Success: ").strip()
        try:
            result = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict):
            return result
    raise RuntimeError("WP-CLI did not return machine-readable JSON")


def validate_canonical_preflight(audit: dict) -> None:
    expected = {"canonical_count": 118, "canonical_missing": 0,
                "canonical_duplicates": 0, "canonical_marked_upsell": 0,
                "actual_variation_posts": 26}
    if any(audit.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Pre-mutation canonical product identity guard failed")


def validate_audit(audit: dict) -> None:
    validate_catalog_audit(audit, expected_deployed_sha=EXPECTED_SHA)


CANONICAL_PREFLIGHT_PHP = r'''$catalog=RollsBar_Catalog_Importer::load_catalog()['products'];$all=get_posts(['post_type'=>'product','post_status'=>array_values(get_post_stati([], 'names')),'numberposts'=>-1,'fields'=>'ids']);$sources=[];foreach($all as $id){$source=(string)get_post_meta($id,'_rollsbar_source_id',true);if($source!=='')$sources[$source][]=(int)$id;}$ids=[];$missing=0;$duplicates=0;$marked=0;foreach($catalog as $row){$source=(string)$row['id'];$id=wc_get_product_id_by_sku(RollsBar_Catalog_Importer::sku_for($source));$p=$id?wc_get_product($id):false;if(!$p||$p->get_meta('_rollsbar_source_id',true)!==$source){$missing++;continue;}if(count($sources[$source]??[])!==1)$duplicates++;if(isset($ids[$id]))$duplicates++;$ids[$id]=true;if($p->get_meta('_rollsbar_upsell_only',true)==='yes')$marked++;}$actualVariationPosts=count(get_posts(['post_type'=>'product_variation','post_status'=>array_values(get_post_stati([], 'names')),'numberposts'=>-1,'fields'=>'ids']));echo wp_json_encode(['canonical_count'=>count($ids),'canonical_missing'=>$missing,'canonical_duplicates'=>$duplicates,'canonical_marked_upsell'=>$marked,'actual_variation_posts'=>$actualVariationPosts]);'''


def shell_prefix() -> str:
    return f'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
PROJECT_ROOT="$HOME/.rollsbar-deploy"
WP_PATH="$HOME/www/{DOMAIN}"
MARKER="$HOME/.rollsbar-staging-deployed-sha"
wp_cmd() {{ wp --path="$WP_PATH" "$@"; }}
'''


def preflight_script() -> str:
    return shell_prefix() + f'''[[ "$PROJECT_ROOT" == "$HOME/.rollsbar-deploy" && -d "$PROJECT_ROOT/.git" ]]
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == '{EXPECTED_SHA}' ]]
git -C "$PROJECT_ROOT" ls-files --error-unmatch wordpress/deploy/backup-staging.sh >/dev/null
git -C "$PROJECT_ROOT" diff --quiet HEAD -- wordpress/deploy/backup-staging.sh
[[ "$WP_PATH" == "$HOME/www/{DOMAIN}" && -f "$WP_PATH/wp-load.php" ]]
[[ "$(wp_cmd eval 'echo strtolower((string)wp_parse_url(home_url("/"), PHP_URL_HOST));')" == '{DOMAIN}' ]]
[[ "$(wp_cmd eval 'echo wp_get_environment_type();')" == 'staging' ]]
[[ -f "$MARKER" && "$(tr -d '[:space:]' < "$MARKER")" == '{EXPECTED_SHA}' ]]
[[ "$(stat -c '%a' "$MARKER")" == '600' ]]
wp_cmd plugin is-active rollsbar-core >/dev/null
wp_cmd plugin is-active woocommerce >/dev/null
[[ "$(wp_cmd post list --post_type=product --post_status=publish --format=count)" == '118' ]]
'''


def backup_script() -> str:
    wrapper = Path(__file__).with_name("prepare-s1-r2-backup.sh").read_text(encoding="utf-8")
    return shell_prefix() + "export WP_PATH PROJECT_ROOT\n" + wrapper


def wp_command(command: str) -> str:
    if not command.startswith("wp "):
        raise ValueError("Only fixed WP-CLI commands are permitted")
    return shell_prefix() + "wp_cmd " + command[3:]


def final_readback_command() -> str:
    return shell_prefix() + f"wp_cmd eval {shlex.quote(AUDIT_PHP)}"


def canonical_preflight_command() -> str:
    return shell_prefix() + f"wp_cmd eval {shlex.quote(CANONICAL_PREFLIGHT_PHP)}"


def final_guard_script() -> str:
    return shell_prefix() + f'''[[ "$(wp_cmd eval 'echo strtolower((string)wp_parse_url(home_url("/"), PHP_URL_HOST));')" == '{DOMAIN}' ]]
[[ "$(wp_cmd eval 'echo wp_get_environment_type();')" == 'staging' ]]
[[ -f "$MARKER" && "$(tr -d '[:space:]' < "$MARKER")" == '{EXPECTED_SHA}' ]]
[[ "$(stat -c '%a' "$MARKER")" == '600' ]]
'''


def connect() -> paramiko.SSHClient:
    if paramiko is None:
        raise RuntimeError("Paramiko is required for the authorized staging runner")
    base = os.environ["ISP_MANAGER_URL"].strip()
    user = os.environ["ISP_MANAGER_USER"].strip()
    password = os.environ["ISP_MANAGER_PASSWORD"].strip()
    host = urlsplit(base).hostname or ""
    if not host or not user or not password:
        raise RuntimeError("Staging hosting access secrets are incomplete")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, port=22, username=user, password=password, timeout=15,
                   auth_timeout=15, banner_timeout=15, look_for_keys=False, allow_agent=False)
    return client


def execute(client: paramiko.SSHClient, command: str, *, stage: str, timeout: int = 180) -> str:
    global CURRENT_STAGE
    CURRENT_STAGE = stage
    # Commands passed here are assembled only from source constants above.
    _, stdout, stderr = client.exec_command("bash -lc " + shlex.quote(command), timeout=timeout)
    output = stdout.read().decode("utf-8", "replace")
    error = stderr.read().decode("utf-8", "replace")
    status = stdout.channel.recv_exit_status()
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    if status:
        evidence = stderr_evidence(error, command)
        raise RuntimeError(f"stage={stage} failed exit={status}; partial state may exist; verified backup gate must be used for recovery; remote_stderr_tail={evidence}")
    return output


def stderr_evidence(stderr: str, command: str, *, limit: int = 3000) -> str:
    """Return bounded failure context without echoing fixed commands or secrets."""
    if not stderr:
        return "[stderr empty]"
    evidence = stderr[-limit:]
    if command:
        evidence = evidence.replace(command, "[fixed remote command redacted]")
    for name, value in os.environ.items():
        if value and (name.startswith("ISP_MANAGER_") or re.search(r"(?:SECRET|TOKEN|PASSWORD|API_KEY|CREDENTIAL)", name, re.I)):
            evidence = evidence.replace(value, "[REDACTED]")
    evidence = re.sub(
        r"(?i)\b(password|token|secret|api[_-]?key|credential)\b\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]", evidence)
    evidence = re.sub(r"(?i)ISP_MANAGER_(?:URL|USER|PASSWORD)", "[ENV_REDACTED]", evidence)
    evidence = re.sub(r"(?m)^\s*[A-Z_][A-Z0-9_]*=.*$", "[environment assignment redacted]", evidence)
    return evidence[-limit:].strip() or "[stderr empty]"


def run_maintenance(client: paramiko.SSHClient) -> None:
    global BACKUP_VERIFIED, CURRENT_STAGE
    execute(client, preflight_script(), stage="preflight")
    canonical = parse_audit(execute(client, canonical_preflight_command(), stage="canonical-identity-preflight"))
    validate_canonical_preflight(canonical)
    initial_dry = parse_success_json(execute(client, wp_command(COMMANDS[0]), stage="variation-preflight"))
    validate_variation(initial_dry, dry_run=True)
    execute(client, backup_script(), stage="canonical-backup-gate", timeout=600)
    BACKUP_VERIFIED = True
    print("backup_gate=prepare-s1-r2-backup.sh verified; historical snapshot protection retained")

    step_a = parse_success_json(execute(client, wp_command(COMMANDS[0]), stage="variation-dry-run"))
    validate_variation(step_a, dry_run=True)
    mutation = parse_success_json(execute(client, wp_command(COMMANDS[1]), stage="variation-mutation"))
    validate_variation(mutation, dry_run=False)
    variation_read = parse_success_json(execute(client, wp_command(COMMANDS[2]), stage="variation-readback"))
    validate_variation(variation_read, dry_run=True, updated=0)
    upsell_dry = parse_success_json(execute(client, wp_command(COMMANDS[3]), stage="upsell-dry-run"))
    validate_upsell_dry(upsell_dry, initial=True)
    upsell_mutation = parse_success_json(execute(client, wp_command(COMMANDS[4]), stage="upsell-mutation"))
    validate_upsell_mutation(upsell_mutation)
    upsell_idempotency = parse_success_json(execute(client, wp_command(COMMANDS[5]), stage="upsell-idempotency-readback"))
    validate_upsell_dry(upsell_idempotency, initial=False)
    final_variation = parse_success_json(execute(client, wp_command(COMMANDS[6]), stage="final-variation-readback"))
    validate_variation(final_variation, dry_run=True, updated=0)
    execute(client, final_guard_script(), stage="final-live-identity-readback")
    audit = parse_audit(execute(client, final_readback_command(), stage="final-woocommerce-readback"))
    validate_audit(audit)
    print("MAINTENANCE SEQUENCE PASS")


def main() -> None:
    client = None
    try:
        client = connect()
        run_maintenance(client)
    except Exception as exc:
        # Never render credentials or arbitrary remote stderr into Actions logs.
        print(f"maintenance=failed stage={CURRENT_STAGE} backup_verified={'yes' if BACKUP_VERIFIED else 'no'}; partial state may exist; no automatic retry or rollback: {exc}")
        raise SystemExit(1)
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()

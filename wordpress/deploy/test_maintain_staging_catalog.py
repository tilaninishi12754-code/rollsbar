#!/usr/bin/env python3
"""Deterministic safety contract for the staging-only catalog maintenance path."""
from __future__ import annotations

import importlib.util
import inspect
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "wordpress/deploy/maintain_staging_catalog.py"
WORKFLOW = ROOT / ".github/workflows/deploy-reg-ru-staging-wordpress.yml"
BACKUP_WRAPPER = ROOT / "wordpress/deploy/prepare-s1-r2-backup.sh"
CONTINUATION_BASELINE = "cbb387aea067e9a312691376788015e436610ee8"
sys.path.insert(0, str(RUNNER.parent))
SPEC = importlib.util.spec_from_file_location("maintenance", RUNNER)
maintenance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(maintenance)


class MaintenanceContract(unittest.TestCase):
    def test_workflow_dispatch_choice_and_existing_deploy_preserved(self):
        current = WORKFLOW.read_text()
        baseline_ref = f"{maintenance.EXPECTED_SHA}:.github/workflows/deploy-reg-ru-staging-wordpress.yml"
        self.assertEqual(maintenance.EXPECTED_SHA, "88826907fc7ffe805a7c47f36c35a74c0049e08e")
        self.assertNotIn(baseline_ref.split(":", 1)[0], ("HEAD", "HEAD^"))
        original = subprocess.check_output(["git", "show", baseline_ref], cwd=ROOT, text=True)
        block = "  workflow_dispatch:\n" + current.split("  workflow_dispatch:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertIn("default: deploy", block)
        self.assertIn("type: choice", block)
        self.assertEqual(re.findall(r"(?m)^\s+- ([a-z-]+)$", block), ["deploy", "catalog-maintenance", "release-inspect", "release-resume"])
        self.assertIn("required: true", block)
        self.assertIn("release_sha:", block)
        self.assertNotRegex(block, r"(?i)command|shell|php|wp-cli|hostname|path|environment|credential")
        self.assertNotRegex(current, r"(?m)^\s+(schedule|repository_dispatch):")

        # Remove only the explicitly requested dispatch input and job condition,
        # then prove the existing deploy implementation and push trigger match HEAD.
        restored = current.replace(block, "  workflow_dispatch:\n", 1)
        restored = restored.replace(
            "    if: github.event_name == 'push' || (github.event_name == 'workflow_dispatch' && inputs.operation == 'deploy')\n",
            "", 1)
        restored = restored.split("\n  catalog-maintenance:\n", 1)[0].rstrip("\n") + "\n"
        self.assertEqual(restored, original)

    def test_workflow_jobs_are_mutually_exclusive(self):
        source = WORKFLOW.read_text()
        self.assertIn("if: github.event_name == 'push' || (github.event_name == 'workflow_dispatch' && inputs.operation == 'deploy')", source)
        self.assertIn("if: github.event_name == 'workflow_dispatch' && inputs.operation == 'catalog-maintenance' && github.ref_name == 'wordpress/checkout-visual-parity-2026-10-25'", source)
        self.assertIn("name: staging\n      deployment: false", source)
        self.assertIn("run: python3 wordpress/deploy/maintain_staging_catalog.py", source)
        self.assertEqual(maintenance.job_should_run("deploy", "push", "", "wordpress/migration-2026-10-01"), True)
        self.assertEqual(maintenance.job_should_run("catalog-maintenance", "push", "catalog-maintenance", maintenance.BRANCH), False)
        self.assertEqual(maintenance.job_should_run("deploy", "workflow_dispatch", "deploy", maintenance.BRANCH), True)
        self.assertEqual(maintenance.job_should_run("catalog-maintenance", "workflow_dispatch", "deploy", maintenance.BRANCH), False)
        self.assertEqual(maintenance.job_should_run("deploy", "workflow_dispatch", "catalog-maintenance", maintenance.BRANCH), False)
        self.assertEqual(maintenance.job_should_run("catalog-maintenance", "workflow_dispatch", "catalog-maintenance", maintenance.BRANCH), True)
        self.assertEqual(maintenance.job_should_run("catalog-maintenance", "workflow_dispatch", "catalog-maintenance", "other-branch"), False)

    def test_fixed_target_canonical_backup_and_no_remote_artifacts(self):
        source = RUNNER.read_text()
        self.assertIn('DOMAIN = "staging.rollsbar.ru"', source)
        self.assertIn('EXPECTED_SHA = "88826907fc7ffe805a7c47f36c35a74c0049e08e"', source)
        self.assertIn('PROJECT_ROOT = "$HOME/.rollsbar-deploy"', source)
        self.assertIn('WP_PATH = "$HOME/www/staging.rollsbar.ru"', source)
        preflight = maintenance.preflight_script()
        self.assertIn("git -C \"$PROJECT_ROOT\" rev-parse HEAD", preflight)
        self.assertIn("git -C \"$PROJECT_ROOT\" ls-files --error-unmatch wordpress/deploy/backup-staging.sh", preflight)
        self.assertIn("git -C \"$PROJECT_ROOT\" diff --quiet HEAD -- wordpress/deploy/backup-staging.sh", preflight)
        for guard in ("wp-load.php", "home_url", "wp_get_environment_type", "stat -c '%a'", "plugin is-active rollsbar-core", "plugin is-active woocommerce"):
            self.assertIn(guard, preflight + source)
        backup = maintenance.backup_script()
        local_wrapper = BACKUP_WRAPPER.read_text(encoding="utf-8")
        export = "export WP_PATH PROJECT_ROOT\n"
        expected_backup = maintenance.shell_prefix() + export + local_wrapper
        self.assertIn(export, backup)
        self.assertGreaterEqual(backup.index(export), len(maintenance.shell_prefix()))
        self.assertLess(backup.index(export), backup.index(local_wrapper))
        self.assertEqual(backup, expected_backup)
        self.assertEqual(backup.index(export), len(maintenance.shell_prefix()))
        self.assertEqual(BACKUP_WRAPPER.read_bytes(), subprocess.check_output(
            ["git", "show", f"{CONTINUATION_BASELINE}:wordpress/deploy/prepare-s1-r2-backup.sh"],
            cwd=ROOT))
        self.assertNotIn('. "$PROJECT_ROOT/wordpress/deploy/prepare-s1-r2-backup.sh"', backup)
        self.assertIn('bash "$PROJECT_ROOT/wordpress/deploy/backup-staging.sh"', backup)
        self.assertIn("export ROLLSBAR_BACKUP_RETENTION=6", local_wrapper)
        self.assertIn("export ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT=20261023T215945Z", local_wrapper)
        self.assertNotIn("open_sftp", source)
        self.assertNotIn("prepare-s1-r2-backup.sh\" as", source)
        self.assertNotIn("open_sftp", source)
        self.assertNotIn("REMOTE_MAINTENANCE", source)
        self.assertNotIn("REMOTE_BACKUP", source)
        self.assertNotIn("catalog import", source)
        self.assertNotRegex(source, r"(?i)telegram|sendmail|notification|wc_create_order|wp\s+order")
        self.assertNotRegex(source, r"(?i)production\.rollsbar|/www/production")

    def test_canonical_backup_wrapper_changes_only_the_retention_slot(self):
        baseline_ref = f"{maintenance.EXPECTED_SHA}:wordpress/deploy/prepare-s1-r2-backup.sh"
        baseline = subprocess.check_output(["git", "show", baseline_ref], cwd=ROOT, text=True)
        current = BACKUP_WRAPPER.read_text(encoding="utf-8")
        old_line = "export ROLLSBAR_BACKUP_RETENTION=5"
        new_line = "export ROLLSBAR_BACKUP_RETENTION=6"
        self.assertEqual(baseline.count(old_line), 1)
        self.assertEqual(current, baseline.replace(old_line, new_line, 1))
        self.assertIn("export ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT=20261023T215945Z", current)

    def test_fixed_command_sequence_and_real_final_readback(self):
        commands = maintenance.COMMANDS
        self.assertEqual(commands, (
            "wp rollsbar catalog repair_variations --dry-run",
            "wp rollsbar catalog repair_variations",
            "wp rollsbar catalog repair_variations --dry-run",
            "wp rollsbar catalog upsells --dry-run --confirm-staging",
            "wp rollsbar catalog upsells --confirm-staging",
            "wp rollsbar catalog upsells --dry-run --confirm-staging",
            "wp rollsbar catalog repair_variations --dry-run",
        ))
        variation_commands = [command for command in commands if "repair" in command]
        self.assertEqual(len(variation_commands), 4)
        self.assertTrue(all("repair_variations" in command for command in variation_commands))
        self.assertFalse(any("repair-variations" in command for command in variation_commands))
        body = re.search(r"(?ms)^def run_maintenance\(.*?(?=^\ndef main\()", RUNNER.read_text()).group(0)
        order = [body.index(f"COMMANDS[{index}]") for index in range(7)]
        order.extend([body.index("final_readback_command()")])
        self.assertEqual(order, sorted(order))
        self.assertLess(body.index("stage=\"canonical-backup-gate\""), body.index("stage=\"variation-mutation\""))
        self.assertLess(body.index("stage=\"preflight\""), body.index("stage=\"canonical-identity-preflight\""))
        self.assertLess(body.index("stage=\"canonical-identity-preflight\""), body.index("stage=\"variation-preflight\""))
        self.assertLess(body.index("stage=\"variation-preflight\""), body.index("stage=\"canonical-backup-gate\""))
        self.assertLess(body.index("stage=\"canonical-backup-gate\""), body.index("stage=\"variation-mutation\""))
        self.assertLess(body.index("stage=\"upsell-mutation\""), body.index("stage=\"upsell-idempotency-readback\""))
        self.assertLess(body.index("stage=\"upsell-mutation\""), body.index("stage=\"final-variation-readback\""))
        php = maintenance.AUDIT_PHP
        for api in ("wc_get_product(", "->is_type('simple')", "->get_catalog_visibility()", "->get_status()", "get_posts(", "_rollsbar_upsell_only", "RollsBar_Catalog_Importer::sku_for"):
            self.assertIn(api, php)
        self.assertIn("get_post_stati([], 'names')", php)
        self.assertIn("'actual_variation_posts'=>$actualVariationPosts", php)
        self.assertIn("'post_type'=>'product_variation'", php)
        self.assertIn("'post_status'=>array_values(get_post_stati([], 'names'))", maintenance.CANONICAL_PREFLIGHT_PHP)
        self.assertIn("'actual_variation_posts'=>$actualVariationPosts", maintenance.CANONICAL_PREFLIGHT_PHP)
        self.assertIn('"actual_variation_posts": 26', inspect.getsource(maintenance.validate_canonical_preflight))
        self.assertIn('"actual_variation_posts": 26', inspect.getsource(maintenance.validate_catalog_audit))
        self.assertIn('"canonical_count": 118', inspect.getsource(maintenance.validate_catalog_audit))
        self.assertIn("updated", source := RUNNER.read_text())
        self.assertNotIn("rm -rf", source)

    def test_pinned_wp_cli_method_matches_fixed_variation_command(self):
        self.assertEqual(maintenance.EXPECTED_SHA, "88826907fc7ffe805a7c47f36c35a74c0049e08e")
        pinned = subprocess.check_output([
            "git", "show",
            f"{maintenance.EXPECTED_SHA}:wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-catalog-importer.php",
        ], cwd=ROOT, text=True, encoding="utf-8")
        method = re.search(
            r"(?s)(/\*\*.*?\*/)[ \t\r\n]*public function repair_variations\(", pinned)
        self.assertIsNotNone(method)
        self.assertRegex(pinned, r"public function repair_variations\(")
        self.assertNotRegex(method.group(1), r"(?m)@subcommand\s+repair-variations\b")

    def test_execute_reports_bounded_sanitized_stderr_and_fails_immediately(self):
        class Stream:
            def __init__(self, content, status=None):
                self.content = content
                self.channel = self if status is not None else None
                self.status = status

            def read(self):
                return self.content.encode()

            def recv_exit_status(self):
                return self.status

        class Client:
            def __init__(self, stderr, status):
                self.stderr = Stream(stderr)
                self.stdout = Stream("", status)
                self.calls = []

            def exec_command(self, command, timeout):
                self.calls.append((command, timeout))
                return None, self.stdout, self.stderr

        command = "fixed WP command input"
        password = "test-secret-value"
        stderr = "x" * 3300 + f" ISP_MANAGER_PASSWORD={password}; {command}; WP-CLI registration error"
        client = Client(stderr, 127)
        with patch.dict("os.environ", {"ISP_MANAGER_PASSWORD": password}):
            with self.assertRaises(RuntimeError) as caught:
                maintenance.execute(client, command, stage="variation-preflight")
        message = str(caught.exception)
        self.assertIn("stage=variation-preflight", message)
        self.assertIn("exit=127", message)
        evidence = message.split("remote_stderr_tail=", 1)[1]
        self.assertLessEqual(len(evidence), 3000)
        self.assertIn("WP-CLI registration error", evidence)
        self.assertNotIn(password, evidence)
        self.assertNotIn(command, evidence)
        self.assertEqual(len(client.calls), 1)

        empty = Client("", 2)
        with self.assertRaises(RuntimeError) as empty_error:
            maintenance.execute(empty, command, stage="empty-stderr")
        self.assertIn("[stderr empty]", str(empty_error.exception))
        self.assertEqual(len(empty.calls), 1)

    def test_local_assertions_fail_closed(self):
        maintenance.validate_variation({"parents": 13, "variations": 26, "dry_run": True, "updated": 5}, dry_run=True)
        with self.assertRaises(RuntimeError):
            maintenance.validate_variation({"parents": 12, "variations": 26, "dry_run": True}, dry_run=True)
        with self.assertRaises(RuntimeError):
            maintenance.validate_variation({"parents": 13, "variations": 26, "dry_run": True, "updated": 1}, dry_run=True, updated=0)
        maintenance.validate_upsell_dry({"dry_run": True, "created": 3, "existing": 0, "provisional_price": True}, initial=True)
        maintenance.validate_upsell_dry({"dry_run": True, "created": 0, "existing": 3, "provisional_price": True}, initial=False)
        with self.assertRaises(RuntimeError):
            maintenance.validate_upsell_mutation({"dry_run": False, "created": 2, "existing": 0, "provisional_price": True})
        audit = {"host": maintenance.DOMAIN, "environment": "staging", "deployed_sha": maintenance.EXPECTED_SHA,
                 "canonical_count": 118, "canonical_missing": 0, "canonical_duplicates": 0,
                 "canonical_marked_upsell": 0, "canonical_wrong_status": 0, "variable_parents": 13,
                 "variations": 26, "actual_variation_posts": 26,
                 "variation_mismatches": 0, "blank_variation_attributes": 0,
                 "upsell_count": 3, "upsell_duplicates": 0, "upsell_identity_mismatches": 0,
                 "wrong_upsell_type": 0, "wrong_upsell_visibility": 0, "wrong_upsell_status": 0,
                 "missing_provisional_provenance": 0, "published_total": 121, "unexpected_published_products": 0,
                 "upsell_source_ids": list(maintenance.EXPECTED_UPSELLS)}
        maintenance.validate_audit(audit)
        maintenance.validate_canonical_preflight({"canonical_count": 118, "canonical_missing": 0,
                                                  "canonical_duplicates": 0, "canonical_marked_upsell": 0,
                                                  "actual_variation_posts": 26})
        for wrong_count in (25, 27):
            with self.subTest(actual_variation_posts=wrong_count):
                bad_preflight = {"canonical_count": 118, "canonical_missing": 0,
                                 "canonical_duplicates": 0, "canonical_marked_upsell": 0,
                                 "actual_variation_posts": wrong_count}
                with self.assertRaises(RuntimeError):
                    maintenance.validate_canonical_preflight(bad_preflight)
                bad_audit = dict(audit, actual_variation_posts=wrong_count)
                with self.assertRaises(RuntimeError):
                    maintenance.validate_audit(bad_audit)
        audit["canonical_count"] = 121
        with self.assertRaises(RuntimeError):
            maintenance.validate_audit(audit)


if __name__ == "__main__":
    unittest.main(verbosity=2)

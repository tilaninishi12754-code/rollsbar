"""Focused offline contracts for the existing workflow's shadow-preview extension."""
import ast
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
tree=ast.parse((ROOT/'qa/repair/s1_r3q_release_read.py').read_text(encoding='utf-8'))
# Exercise the real command builder without importing SSH dependencies locally.
builder=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='marker_command')
namespace={'re':re}
exec(compile(ast.Module(body=[builder],type_ignores=[]),'marker_command','exec'),namespace)
marker_command=namespace['marker_command']


class RemotePreviewContracts(unittest.TestCase):
    def test_marker_override_is_literal_sha_and_read_only(self):
        for sha in ['88826907fc7ffe805a7c47f36c35a74c0049e08e','e0c3d4edd4c2bce0718bed8e20bc7c356a55d0ea']:
            command=marker_command(sha)
            self.assertIn('test "$marker" = '+sha,command)
            self.assertIn('cat "$HOME/.rollsbar-staging-deployed-sha"',command)
            self.assertNotIn('wp ',command)
            self.assertNotRegex(command,r'\b(?:rm|cp|mv|mkdir|tee)\b|>>?')
        for bad in ['', '8882690', 'A'*40, 'a'*40+';echo injection', 'a'*40+'\n']:
            with self.subTest(value=bad),self.assertRaises(ValueError):marker_command(bad)

    def test_workflow_keeps_gate_and_always_marker_and_artifacts(self):
        source=(ROOT/'.github/workflows/gate-b-browser.yml').read_text(encoding='utf-8')
        self.assertEqual(source.count('run: python3 wordpress/deploy/gate_b_browser.py'),1)
        self.assertEqual(source.count('run: python3 qa/repair/s1_r3q_release_read.py'),2)
        self.assertIn('if: always()\n',source)
        self.assertIn('uses: actions/upload-artifact@v4',source)
        self.assertIn('set -o pipefail',source)
        self.assertIn('python3 qa/checkout/shadow_preview.py',source)
        self.assertNotRegex(source,r'(?m)^  (?:push|schedule|workflow_run):')
        self.assertIn('deployment: false',source)


if __name__=='__main__':unittest.main()

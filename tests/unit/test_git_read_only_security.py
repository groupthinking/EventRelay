"""Real Git marker regressions for the exact read-only launcher function bodies.

No MCP server or provider is launched. The Node VM excludes SDK imports and
transport wiring; this test does not establish MCP end-to-end acceptance.
"""
import subprocess
import unittest
from pathlib import Path


class GitReadOnlySecurityTests(unittest.TestCase):
    def test_repository_helpers_do_not_run_from_read_tools(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            ["node", str(root / "tests/security/git_workflow_read_only_probe.mjs"),
             str(root / "tools/mcp/git_workflow_server.mjs")],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("PASS "), 7)


if __name__ == "__main__":
    unittest.main()

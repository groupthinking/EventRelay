"""Exercise the workflow's actual shell gate without querying a live registry."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


class NpmAuditWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        workflow = yaml.safe_load(
            (cls.root / ".github/workflows/security.yml").read_text()
        )
        cls.job = workflow["jobs"]["npm-audit"]
        cls.steps = cls.job["steps"]
        cls.audit = next(
            step
            for step in cls.steps
            if step.get("name") == "Audit locked npm dependencies"
        )

    def test_audit_uses_exact_head_and_declared_locked_graph(self):
        manifest = json.loads((self.root / "package.json").read_text())
        npm_version = manifest["packageManager"].removeprefix("npm@")
        self.assertEqual(
            self.steps[0]["with"]["ref"],
            "${{ github.event.pull_request.head.sha || github.sha }}",
        )
        self.assertIn(
            "npm install --global npm@" + npm_version,
            [step.get("run") for step in self.steps],
        )
        self.assertIn(
            "npm ci --ignore-scripts --no-audit --no-fund",
            [step.get("run") for step in self.steps],
        )
        self.assertFalse(self.job.get("continue-on-error", False))
        self.assertFalse(self.audit.get("continue-on-error", False))
        artifact = next(
            step for step in self.steps if "upload-artifact@" in step.get("uses", "")
        )
        self.assertEqual(artifact["if"], "always()")
        self.assertEqual(artifact["with"]["path"], "npm-audit-report.json")
        self.assertEqual(artifact["with"]["if-no-files-found"], "error")

    def test_actual_workflow_shell_retains_report_and_propagates_audit_result(self):
        # A controlled executable stands in for npm's already-tested advisory
        # query. Run the workflow shell verbatim to catch swallowed return codes,
        # report loss, or failure to request the high severity threshold.
        for exit_code in (0, 1, 2):
            with (
                self.subTest(exit_code=exit_code),
                tempfile.TemporaryDirectory() as tmp,
            ):
                directory = Path(tmp)
                fake_npm = directory / "npm"
                fake_npm.write_text(
                    "#!/bin/sh\n"
                    '[ "$*" = "audit --audit-level=high --json" ] || exit 99\n'
                    "printf '%s\\n' \"$AUDIT_TEST_REPORT\"\n"
                    'exit "$AUDIT_TEST_EXIT"\n'
                )
                fake_npm.chmod(0o755)
                report = {
                    "metadata": {"vulnerabilities": {"high": int(exit_code == 1)}}
                }
                if exit_code == 2:
                    report = {
                        "error": {
                            "code": "EAI_AGAIN",
                            "summary": "Controlled registry error",
                        }
                    }
                env = {
                    **os.environ,
                    "PATH": str(directory) + os.pathsep + os.environ["PATH"],
                    "AUDIT_TEST_EXIT": str(exit_code),
                    "AUDIT_TEST_REPORT": json.dumps(report),
                }
                result = subprocess.run(
                    ["bash", "-e", "-o", "pipefail", "-c", self.audit["run"]],
                    cwd=directory,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, exit_code, result.stderr)
                self.assertEqual(json.loads(result.stdout), report)
                self.assertEqual(
                    json.loads((directory / "npm-audit-report.json").read_text()),
                    report,
                )


if __name__ == "__main__":
    unittest.main()

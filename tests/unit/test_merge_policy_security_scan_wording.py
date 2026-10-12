from pathlib import Path
import json
import unittest


class ImageGatePolicyTests(unittest.TestCase):
    def test_image_findings_block_and_unverified_exceptions_are_not_applied(self):
        root = Path(__file__).resolve().parents[2]
        policy = (root / "MERGE_POLICY.md").read_text()
        workflow = (root / ".github/workflows/security.yml").read_text()
        enforcing = workflow.split("name: Run Trivy vulnerability scanner", 1)[1].split("- name:", 1)[0]
        self.assertIn("exit-code: '1'", enforcing)
        self.assertIn("ignore-unfixed: false", enforcing)
        self.assertIn("trivyignores: '.github/trivy-no-exceptions.txt'", enforcing)
        self.assertIn("severity: 'CRITICAL,HIGH'", enforcing)
        self.assertIn("No exceptions are accepted", policy)
        self.assertIn("Do not automatically demote `trivy`", policy)

    def test_failed_scan_evidence_is_retained(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github/workflows/security.yml").read_text()
        self.assertIn("if: always() && hashFiles('trivy-results.sarif') != ''", workflow)
        retention = workflow.split("name: Retain exact image scan evidence", 1)[1]
        self.assertIn("if: always()", retention)
        self.assertIn("image-identity.json", retention)
        self.assertIn("trivy-results.sarif", retention)

    def test_scanner_reported_runtime_dependency_floors_are_locked(self):
        root = Path(__file__).resolve().parents[2]
        manifest = json.loads((root / "package.json").read_text())
        lock = json.loads((root / "package-lock.json").read_text())
        packages = lock["packages"]

        self.assertEqual(manifest["overrides"]["@workflow/core"]["devalue"], "5.9.3")
        self.assertEqual(manifest["overrides"]["proxy-addr"], "^2.0.8")
        self.assertEqual(manifest["overrides"]["source-map-js"], "^1.2.2")
        self.assertEqual(packages["node_modules/devalue"]["version"], "5.9.3")
        self.assertEqual(packages["node_modules/proxy-addr"]["version"], "2.0.8")
        self.assertEqual(packages["node_modules/source-map-js"]["version"], "1.2.2")

    def test_image_build_constrains_python_and_runtime_npm(self):
        root = Path(__file__).resolve().parents[2]
        constraints = (root / "constraints.txt").read_text()
        dockerfile = (root / "Dockerfile").read_text()

        self.assertIn("urllib3>=2.8.0", constraints)
        self.assertIn('"setuptools>=80.10.2"', dockerfile)
        self.assertIn('"wheel>=0.46.2"', dockerfile)
        self.assertIn("npm install --global npm@12.2.0", dockerfile)
        self.assertIn("rm -rf /usr/local/lib/python3.11/site-packages/*", dockerfile)


if __name__ == "__main__":
    unittest.main()

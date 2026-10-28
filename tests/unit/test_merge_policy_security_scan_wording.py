import json
import unittest
from pathlib import Path

import yaml


class ImageGatePolicyTests(unittest.TestCase):
    def test_bootstrap_separates_repairs_from_strict_enforcement(self):
        root = Path(__file__).resolve().parents[2]
        policy = (root / "MERGE_POLICY.md").read_text()
        workflow = yaml.safe_load((root / ".github/workflows/security.yml").read_text())
        job = workflow["jobs"]["trivy"]
        self.assertFalse(job.get("continue-on-error", False))
        scans = [
            step for step in job["steps"] if "trivy-action@" in step.get("uses", "")
        ]
        self.assertEqual(len(scans), 2)
        for scan in scans:
            self.assertEqual(scan["with"]["exit-code"], "0")
            self.assertFalse(scan.get("continue-on-error", False))
            self.assertIs(scan["with"]["ignore-unfixed"], False)
            self.assertEqual(scan["with"]["severity"], "CRITICAL,HIGH")
            self.assertEqual(
                scan["with"]["trivyignores"], ".github/trivy-no-exceptions.txt"
            )
        sarif = next(scan for scan in scans if scan["with"]["format"] == "sarif")
        self.assertIs(sarif["with"]["limit-severities-for-sarif"], True)
        self.assertIn("scan-completion gate", policy)
        self.assertIn("Parent #2396 stays open", policy)
        self.assertIn("no accepted baseline", policy)
        self.assertIn("separately reviewed", policy)
        self.assertIn("No exceptions are accepted", policy)
        self.assertIn("Do not automatically demote `trivy`", policy)
        exceptions = (root / ".github/trivy-no-exceptions.txt").read_text()
        self.assertFalse(
            [
                line
                for line in exceptions.splitlines()
                if line.strip() and not line.startswith("#")
            ]
        )

    def test_failed_scan_evidence_is_retained(self):
        root = Path(__file__).resolve().parents[2]
        workflow = yaml.safe_load((root / ".github/workflows/security.yml").read_text())
        steps = workflow["jobs"]["trivy"]["steps"]
        self.assertEqual(
            steps[0]["with"]["ref"],
            "${{ github.event.pull_request.head.sha || github.sha }}",
        )
        build = next(
            step for step in steps if step.get("name") == "Build image for scanning"
        )
        self.assertIn(
            "docker image inspect eventrelay:test > image-identity.json", build["run"]
        )
        self.assertIn("git rev-parse HEAD > image-source-commit.txt", build["run"])
        upload = next(step for step in steps if "upload-sarif@" in step.get("uses", ""))
        self.assertEqual(
            upload["if"], "always() && hashFiles('trivy-results.sarif') != ''"
        )
        retention = next(
            step
            for step in steps
            if step.get("name") == "Retain exact image scan evidence"
        )
        self.assertEqual(retention["if"], "always()")
        self.assertEqual(retention["with"]["if-no-files-found"], "error")
        self.assertEqual(
            set(retention["with"]["path"].splitlines()),
            {
                "image-identity.json",
                "image-source-commit.txt",
                "trivy-results.sarif",
            },
        )

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

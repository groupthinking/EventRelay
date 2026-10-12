from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()

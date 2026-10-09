"""Exercise the actual metadata-only workflow script with a mocked GitHub API."""
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/pr-checks.yml"

class SecurityEvidenceTest(unittest.TestCase):
    def validate(self, title, paths, body, labels=None):
        text = WORKFLOW.read_text()
        script = text.split("          script: |\n", 1)[1]
        script = "\n".join(line[12:] for line in script.splitlines())
        payload = json.dumps({"title": title, "body": body, "labels": labels or [], "number": 1})
        files = json.dumps([{"filename": path} for path in paths])
        harness = """
const context = {payload: {pull_request: PR}, repo: {owner:'test',repo:'test'}};
const core = {setFailed: message => {process.stdout.write(message);}};
const github = {rest: {pulls: {listFiles:'files'}, issues: {
listComments:'comments', updateComment:async()=>{},createComment:async()=>{}
}}, paginate:async kind => kind === 'files' ? FILES : []};
(async()=>{ SCRIPT })().catch(error=>{console.error(error);process.exit(1);});
""".replace("PR", payload).replace("FILES", files).replace("SCRIPT", script)
        return subprocess.run(["node", "-e", harness], capture_output=True, text=True, check=True).stdout

    def test_missing_and_placeholder_evidence_fail(self):
        for body in ["Closes #1. Security patch.", "## Security dependency evidence\n- Advisory: TODO\n- Package and versions: TBD\n- Validation: ...\n- Rollback: N/A"]:
            self.assertIn("failed", self.validate("fix: security patch", ["package-lock.json"], body))

    def test_complete_evidence_passes(self):
        body = "## Security dependency evidence\n- Advisory: https://github.com/advisories/GHSA-example\n- Package and versions: example 1 -> 2 transitive\n- Validation: NOT RUN; blocked by unavailable runner\n- Rollback: revert patch through reviewed PR"
        self.assertEqual("", self.validate("fix: security patch", ["package-lock.json"], body))

    def test_unrelated_pr_and_non_dependency_security_pr_pass(self):
        self.assertEqual("", self.validate("docs: security procedure", ["docs/runbook.md"], "Closes #1. Adds procedure."))
        self.assertEqual("", self.validate("chore: regular update", ["package-lock.json"], "Closes #1. Regular update."))

    def test_security_label_and_nested_python_dependency_trigger(self):
        self.assertIn("failed", self.validate("fix: update library", ["services/requirements.txt"], "Closes #1. Updates library.", [{"name":"security"}]))

    def test_python_inputs_and_annotated_placeholders_fail(self):
        for path in ["requirements.in", "setup.py", "setup.cfg", "Pipfile", "Pipfile.lock", "pylock.toml", "constraints.in", "constraints.txt"]:
            self.assertIn("failed", self.validate("fix: security patch", [path], "Closes #1. Updates library."))
        body = "## Security dependency evidence\n- Advisory: TODO add link\n- Package and versions: example 1 -> 2\n- Validation: passed\n- Rollback: revert"
        self.assertIn("failed", self.validate("fix: security patch", ["package.json"], body))

    def test_empty_field_does_not_consume_next_line(self):
        body = "## Security dependency evidence\n- Advisory:\n- Package and versions: example 1 -> 2\n- Validation: passed\n- Rollback: revert"
        self.assertIn("failed", self.validate("fix: security patch", ["package.json"], body))

if __name__ == "__main__":
    unittest.main()

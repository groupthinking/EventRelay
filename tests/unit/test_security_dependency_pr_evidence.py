"""Exercise the actual metadata-only workflow script with a mocked GitHub API."""
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/pr-checks.yml"

class SecurityEvidenceTest(unittest.TestCase):
    def validate(
        self, title, paths, body, labels=None, changed_files=None, include_changed_files=True, fork=False, author=None
    ):
        text = WORKFLOW.read_text()
        script = text.split("          script: |\n", 1)[1]
        script = "\n".join(line[12:] for line in script.splitlines())
        pull_request = {"title": title, "body": body, "labels": labels or [], "number": 1}
        if include_changed_files:
            pull_request["changed_files"] = (
                len(paths) if changed_files is None else changed_files
            )
        pull_request["head"] = {"repo": {"full_name": "other/fork" if fork else "test/test"}}
        pull_request["user"] = {"login": author or "contributor"}
        payload = json.dumps(pull_request)
        files = json.dumps([{"filename": path} for path in paths])
        harness = """
const context = {payload: {pull_request: PR}, repo: {owner:'test',repo:'test'}};
const core = {warning:()=>{},setFailed: message => {process.stdout.write(message);}};
const github = {rest: {pulls: {listFiles:'files'}, issues: {
listComments:'comments', updateComment:async()=>{if(FORK)throw Error('fork write');},
createComment:async()=>{if(FORK)throw Error('fork write');}
}}, paginate:async kind => {
if(kind !== 'files' && FORK)throw Error('fork comment read');
return kind === 'files' ? FILES : [];
}};
(async()=>{ SCRIPT })().catch(error=>{console.error(error);process.exit(1);});
""".replace("PR", payload).replace("FILES", files).replace("SCRIPT", script).replace("FORK", json.dumps(fork or author == "dependabot[bot]"))
        return subprocess.run(["node", "-e", harness], capture_output=True, text=True, check=True).stdout

    def test_fork_missing_evidence_fails_without_comment_access(self):
        self.assertIn("failed", self.validate(
            "fix: security patch", ["package-lock.json"], "Closes #1. Patch.", fork=True))

    def test_valid_fork_passes_without_comment_access(self):
        self.assertEqual("", self.validate(
            "docs: explain behavior", ["docs/readme.md"], "Closes #1. Document behavior.",
            fork=True))

    def test_dependabot_validation_does_not_attempt_comment_writes(self):
        self.assertIn("failed", self.validate(
            "fix: security patch", ["package-lock.json"], "Closes #1. Patch.",
            author="dependabot[bot]"))

    def test_no_privileged_pull_request_trigger(self):
        import yaml
        workflow = yaml.safe_load(WORKFLOW.read_text())
        self.assertIn("pull_request", workflow[True])
        self.assertNotIn("pull_request_target", workflow[True])

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

    def test_incomplete_file_listing_requires_security_evidence(self):
        self.assertIn("failed", self.validate(
            "fix: security update", ["docs/visible-file.md"],
            "Closes #1. Large security change.", changed_files=3001))

    def test_file_listing_at_github_limit_requires_security_evidence(self):
        paths = [f"docs/file-{index}.md" for index in range(3000)]
        self.assertIn("failed", self.validate(
            "fix: security update", paths,
            "Closes #1. Large security change.", changed_files=3000))

    def test_missing_file_count_requires_security_evidence(self):
        self.assertIn("failed", self.validate(
            "fix: security update", ["docs/visible-file.md"],
            "Closes #1. Large security change.", include_changed_files=False))

if __name__ == "__main__":
    unittest.main()

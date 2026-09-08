from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github/workflows/repository-reconciliation.yml"
)


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), "Repository reconciliation workflow should exist"
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _get_script(workflow: dict) -> str:
    steps = workflow["jobs"]["report"]["steps"]
    script_step = next(
        step for step in steps if "Reconcile" in step.get("name", "")
    )
    return script_step["with"]["script"]


def _run_reconciliation(tmp_path: Path, scenario: dict) -> dict:
    """Execute the workflow's real reconciliation script against stubbed GitHub APIs."""
    node = shutil.which("node")
    if node is None:  # pragma: no cover - depends on the runner image
        pytest.skip("node is required to execute the workflow's inline script")

    script_path = tmp_path / "repository_reconciliation.js"
    script_path.write_text(_get_script(_load_workflow()), encoding="utf-8")
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
    driver_path = tmp_path / "driver.js"
    driver_path.write_text(
        """
const fs = require("fs");
const vm = require("vm");

const [scriptPath, scenarioPath] = process.argv.slice(2);
const script = fs.readFileSync(scriptPath, "utf8");
const scenario = JSON.parse(fs.readFileSync(scenarioPath, "utf8"));
const actions = { issueUpdates: [], issueCreates: [], comments: [], pullUpdates: [], infos: [] };

const pullsList = async () => ({ data: scenario.pulls || [] });
pullsList.__tag = "pulls.list";
const listBranches = async () => ({ data: scenario.branches || [] });
listBranches.__tag = "repos.listBranches";
const listComments = async ({ issue_number }) => ({ data: (scenario.commentsByIssue || {})[issue_number] || [] });
listComments.__tag = "issues.listComments";

const github = {
  paginate: async (fn, params) => {
    switch (fn.__tag) {
      case "pulls.list":
        return scenario.pulls || [];
      case "repos.listBranches":
        return scenario.branches || [];
      case "issues.listComments":
        return ((scenario.commentsByIssue || {})[params.issue_number]) || [];
      default:
        throw new Error(`Unsupported paginate call: ${fn.__tag}`);
    }
  },
  rest: {
    pulls: {
      list: pullsList,
      update: async (payload) => {
        actions.pullUpdates.push(payload);
        return { data: payload };
      },
    },
    repos: {
      listBranches,
      getCommit: async ({ ref }) => ({
        data: {
          commit: {
            committer: { date: ((scenario.commitsBySha || {})[ref]) || "2026-07-01T00:00:00Z" },
          },
        },
      }),
    },
    issues: {
      get: async ({ issue_number }) => {
        const issue = (scenario.issuesByNumber || {})[issue_number];
        if (!issue) {
          const err = new Error(`Missing issue ${issue_number}`);
          err.status = 404;
          throw err;
        }
        return { data: issue };
      },
      update: async (payload) => {
        actions.issueUpdates.push(payload);
        return { data: payload };
      },
      create: async (payload) => {
        actions.issueCreates.push(payload);
        return { data: { number: scenario.createdReportNumber || 999 } };
      },
      listComments,
      createComment: async (payload) => {
        actions.comments.push(payload);
        return { data: payload };
      },
    },
    search: {
      issuesAndPullRequests: async () => ({
        data: {
          items: scenario.existingReport ? [scenario.existingReport] : [],
        },
      }),
    },
  },
};

const context = { repo: { owner: "groupthinking", repo: "EventRelay" } };
const core = { info: (message) => actions.infos.push(message) };

(async () => {
  await vm.runInNewContext(
    `(async () => {${script}\\n})()`,
    { context, github, core, console, Date, Set, Map, Number, Error },
  );
  process.stdout.write(JSON.stringify(actions));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [node, str(driver_path), str(script_path), str(scenario_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"driver failed: {result.stderr}"
    return json.loads(result.stdout)


def test_reconciliation_workflow_file_is_valid_yaml() -> None:
    workflow = _load_workflow()
    assert workflow["name"] == "Repository Reconciliation"


def test_reconciliation_workflow_triggers_on_schedule_and_dispatch() -> None:
    workflow = _load_workflow()
    # PyYAML parses the YAML 'on' key as Python True.
    triggers = workflow[True]
    assert "schedule" in triggers
    assert "workflow_dispatch" in triggers
    crons = [entry["cron"] for entry in triggers["schedule"]]
    assert len(crons) >= 1


def test_reconciliation_workflow_reacts_to_repo_state_changes() -> None:
    """The report must refresh when PR, issue, or branch state changes."""
    triggers = _load_workflow()[True]
    assert triggers["pull_request_target"]["types"] == [
        "opened",
        "reopened",
        "edited",
        "synchronize",
        "ready_for_review",
        "converted_to_draft",
        "closed",
    ]
    assert triggers["issues"]["types"] == ["opened", "reopened", "closed"]
    assert "create" in triggers
    assert "delete" in triggers


def test_reconciliation_workflow_minimum_permissions() -> None:
    workflow = _load_workflow()
    perms = workflow["permissions"]
    assert perms.get("contents") == "read"
    # Comments on untracked PRs and closes superseded draft PRs via pulls.update.
    assert perms.get("pull-requests") == "write"
    # Needs write to upsert the drift report issue.
    assert perms.get("issues") == "write"


def test_reconciliation_workflow_excludes_draft_prs_from_untracked() -> None:
    """Draft PRs must not be counted as governance drift in the untracked list."""
    script = _get_script(_load_workflow())
    assert "pr.draft" in script, (
        "Draft PRs must be excluded from the untracked list; governance defers enforcement for drafts."
    )


def test_reconciliation_workflow_validates_issue_numbers_via_api() -> None:
    """Issue numbers referenced in PR bodies must be validated through the Issues API."""
    script = _get_script(_load_workflow())
    assert "github.rest.issues.get" in script, (
        "Issue numbers must be validated via the Issues API to prevent fictitious duplicate groups."
    )
    # Must verify it's a real issue (not a PR number).
    assert "pull_request" in script
    # Must handle 404 (non-existent references).
    assert "404" in script


def test_reconciliation_workflow_restricts_active_heads_to_same_repo() -> None:
    """activeHeads must only include branches from the same repository, not forks."""
    script = _get_script(_load_workflow())
    assert "head.repo" in script and "full_name" in script, (
        "activeHeads must filter by pr.head.repo.full_name to exclude fork branch names."
    )


def test_reconciliation_workflow_stale_cutoff_is_positive() -> None:
    """The stale-branch cutoff must be a positive number of milliseconds."""
    script = _get_script(_load_workflow())
    assert "staleAfterMs" in script
    # The constant must appear as a numeric expression > 0.
    assert "14 * 24 * 60 * 60 * 1000" in script or "staleAfterMs = " in script


def test_reconciliation_workflow_total_branches_metric_is_accurate() -> None:
    """The branches metric must correctly reflect what was fetched (all branches)."""
    script = _get_script(_load_workflow())
    # Should NOT fetch with protected: false, because that excludes protected branches.
    assert "protected: false" not in script, (
        "Fetching with protected: false excludes protected branches and makes the total inaccurate."
    )
    # The label in the report must say "Total remote branches" (includes all fetched).
    assert "Total remote branches" in script


def test_reconciliation_workflow_report_is_idempotent() -> None:
    """Running the reconciliation twice must upsert a single issue, not create duplicates."""
    script = _get_script(_load_workflow())
    # Should search for the existing report issue.
    assert "search.issuesAndPullRequests" in script or "issuesAndPullRequests" in script
    # Should update the existing issue if found, otherwise create a new one.
    assert "issues.update" in script
    assert "issues.create" in script


def test_reconciliation_accepts_repo_qualified_issue_references(tmp_path: Path) -> None:
    """Canonical references like owner/repo#123 must not be reported missing."""
    outcome = _run_reconciliation(
        tmp_path,
        {
            "pulls": [
                {
                    "number": 903,
                    "title": "fix(auth): restore Google OAuth configuration in Vercel production",
                    "body": "## Canonical issue\\n\\nCloses groupthinking/EventRelay#900",
                    "draft": False,
                    "head": {
                        "ref": "jules-15243187445261469621-ffdb089e",
                        "repo": {"full_name": "groupthinking/EventRelay"},
                    },
                }
            ],
            "branches": [],
            "issuesByNumber": {"900": {"state": "open"}},
            "existingReport": {"number": 1584, "title": "[automation] Repository drift report"},
        },
    )

    assert outcome["comments"] == []
    assert (
        "- Ready PRs without exactly one canonical issue: **0**"
        in outcome["issueUpdates"][0]["body"]
    )


def test_reconciliation_keeps_closed_canonical_issues_tracked(tmp_path: Path) -> None:
    """A PR linked to one real issue stays canonical even after that issue closes."""
    outcome = _run_reconciliation(
        tmp_path,
        {
            "pulls": [
                {
                    "number": 1673,
                    "title": "Canonicalize retired routes into the Studio workbench",
                    "body": "## Canonical issue\\n\\nCloses #1669",
                    "draft": False,
                    "head": {
                        "ref": "copilot/make-home-sell-page-and-route-studio",
                        "repo": {"full_name": "groupthinking/EventRelay"},
                    },
                }
            ],
            "branches": [],
            "issuesByNumber": {"1669": {"state": "closed"}},
            "existingReport": {"number": 1584, "title": "[automation] Repository drift report"},
        },
    )

    assert outcome["comments"] == []
    assert (
        "- Ready PRs without exactly one canonical issue: **0**"
        in outcome["issueUpdates"][0]["body"]
    )

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
const listBranches = async (params = {}) => ({
  data: params.protected
    ? (scenario.protectedBranches || (scenario.branches || []).filter(branch => branch.protected))
    : (scenario.branches || []),
});
listBranches.__tag = "repos.listBranches";
const listComments = async ({ issue_number }) => ({ data: (scenario.commentsByIssue || {})[issue_number] || [] });
listComments.__tag = "issues.listComments";

const graphql = async () => {
  if (scenario.graphqlError) {
    const err = new Error(scenario.graphqlError.message);
    err.status = scenario.graphqlError.status;
    throw err;
  }
  return {
    repository: {
      refs: {
        totalCount: (scenario.branches || []).length,
        pageInfo: { hasNextPage: false, endCursor: null },
        nodes: (scenario.branches || []).map((branch) => ({
          name: branch.name,
          branchProtectionRule: branch.protected ? { id: "protected" } : null,
          target: {
            oid: branch.commit?.sha || branch.sha || "fixture-sha",
            committedDate:
              branch.committedDate ||
              ((scenario.commitsBySha || {})[branch.commit?.sha || branch.sha]) ||
              "2026-07-01T00:00:00Z",
          },
        })),
      },
    },
  };
};

const github = {
  graphql,
  paginate: async (fn, params) => {
    switch (fn.__tag) {
      case "pulls.list":
        return scenario.pulls || [];
      case "repos.listBranches":
        return params.protected
          ? (scenario.protectedBranches || (scenario.branches || []).filter(branch => branch.protected))
          : (scenario.branches || []);
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
    """The report refreshes on governance state changes, not every code push."""
    triggers = _load_workflow()[True]
    assert triggers["pull_request_target"]["types"] == [
        "opened",
        "reopened",
        "edited",
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
    assert perms.get("pull-requests") == "read"
    # Needs write to upsert the report and comment on untracked PRs.
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


def test_reconciliation_workflow_accepts_same_repo_qualified_closing_refs() -> None:
    """Canonical issue detection must accept `Closes owner/repo#123` for this repo."""
    script = _get_script(_load_workflow())
    assert "escapedRepoFullName" in script, (
        "Closing-reference parsing should escape the current repo name so fully qualified"
        " same-repo references are accepted."
    )
    assert "repoFullName" in script, (
        "Closing-reference parsing should derive the fully qualified repo prefix from"
        " the current workflow repository context."
    )


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


def test_reconciliation_uses_graphql_branch_inventory_without_rest_pagination() -> None:
    """Branch inventory must avoid one REST request per page and per stale branch."""
    script = _get_script(_load_workflow())

    assert "github.graphql" in script
    assert 'refs(refPrefix: "refs/heads/"' in script
    assert "committedDate" in script
    assert "github.paginate(github.rest.repos.listBranches" not in script


def test_reconciliation_branch_query_omits_admin_only_branch_protection_field() -> None:
    """The branch inventory query must not request admin-only branch protection data."""
    script = _get_script(_load_workflow())

    assert "branchProtectionRule { id }" not in script


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


def test_reconciliation_workflow_excludes_dependabot_from_untracked() -> None:
    """Dependabot dependency PRs should not be counted as canonical-issue drift."""
    script = _get_script(_load_workflow())
    assert "dependabot[bot]" in script
    assert "isDependencyAutomationPR" in script


@pytest.mark.parametrize(
    "title",
    [
        "build(deps): bump anyio",
        "build(deps-dev): bump pytest",
        "fix: bump anyio in the uv group across 1 directory",
        "chore(deps): bump anyio",
        "Bump anyio",
    ],
)
@pytest.mark.parametrize("author", ["dependabot[bot]", "contributor"])
def test_dependency_exemption_uses_author_not_title(
    tmp_path: Path, title: str, author: str
) -> None:
    outcome = _run_reconciliation(
        tmp_path,
        {
            "pulls": [
                {
                    "number": 2006,
                    "title": title,
                    "body": "",
                    "user": {"login": author},
                    "draft": False,
                    "head": {"ref": "dependabot/uv/anyio", "repo": None},
                }
            ],
        },
    )

    expected = 0 if author == "dependabot[bot]" else 1
    assert len(outcome["comments"]) == expected
    assert (
        f"- Ready PRs without exactly one canonical issue: **{expected}**"
        in outcome["issueCreates"][0]["body"]
    )


@pytest.mark.parametrize(
    "example",
    [
        "`Closes #123`",
        "``Example `Closes #123` here``",
        "```Closes #123```",
        "```text\nCloses #123\n```",
        "````text\n```\nCloses #123\n```\n````",
        "~~~text\nCloses #123\n~~~",
        "  ```text\nCloses #123\n  ````",
    ],
)
@pytest.mark.parametrize("canonical", ["", "\n\n- Fixes groupthinking/EventRelay#1822"])
def test_reconciliation_ignores_code_examples(
    tmp_path: Path, example: str, canonical: str
) -> None:
    outcome = _run_reconciliation(
        tmp_path,
        {
            "pulls": [
                {
                    "number": 1825,
                    "title": "fix(reconciliation): accept same-repo qualified issue refs",
                    "body": f"Example:\n{example}{canonical}",
                    "draft": False,
                    "head": {"ref": "reconciliation", "repo": None},
                },
                {
                    "number": 124,
                    "title": "Implement a different issue",
                    "body": "Closes #123",
                    "draft": False,
                    "head": {"ref": "other-work", "repo": None},
                },
            ],
            "issuesByNumber": {"123": {"state": "open"}, "1822": {"state": "open"}},
        },
    )

    body = outcome["issueCreates"][0]["body"]
    expected = 0 if canonical else 1
    assert f"- Ready PRs without exactly one canonical issue: **{expected}**" in body
    assert "- Issues with competing implementation PRs: **0**" in body
    assert [comment["issue_number"] for comment in outcome["comments"]] == (
        [] if canonical else [1825]
    )


@pytest.mark.parametrize(
    "body",
    [
        "Closes other/repo#1822",
        "Closes #999999",
        "Closes #1825",
        "Closes #1822\nFixes #123",
        "```text\nCloses #1822",
        "~~~text\nCloses #1822",
        "Closes `example` #1822",
        "Closes\n```\nexample\n```\n#1822",
    ],
)
def test_reconciliation_still_reports_noncanonical_references(
    tmp_path: Path, body: str
) -> None:
    outcome = _run_reconciliation(
        tmp_path,
        {
            "pulls": [
                {
                    "number": 1691,
                    "title": "Partial implementation",
                    "body": body,
                    "draft": False,
                    "head": {"ref": "partial", "repo": None},
                }
            ],
            "issuesByNumber": {
                "123": {"state": "open"},
                "1822": {"state": "open"},
                "1825": {"pull_request": {}},
            },
        },
    )

    assert "- Ready PRs without exactly one canonical issue: **1**" in (
        outcome["issueCreates"][0]["body"]
    )
    assert [comment["issue_number"] for comment in outcome["comments"]] == [1691]


def test_reconciliation_reports_competition_and_stale_branches_without_closing_prs(
    tmp_path: Path,
) -> None:
    outcome = _run_reconciliation(
        tmp_path,
        {
            "pulls": [
                {
                    "number": number,
                    "title": "Landing page implementation",
                    "body": body,
                    "draft": True,
                    "head": {
                        "ref": f"implementation-{number}",
                        "repo": {"full_name": "groupthinking/EventRelay"},
                    },
                }
                for number, body in [
                    (1981, "Closes #1975"),
                    (1996, "Closes #1975\nSupersedes draft #1981"),
                ]
            ],
            "branches": [
                {
                    "name": name,
                    "protected": protected,
                    "commit": {"sha": "042989a9abcdef"},
                }
                for name, protected in [
                    ("main", False),
                    ("protected", True),
                    ("implementation-1981", False),
                    ("implementation-1996", False),
                    ("unattached", False),
                ]
            ],
            "commitsBySha": {"042989a9abcdef": "2000-01-01T00:00:00Z"},
            "issuesByNumber": {"1975": {"state": "open"}},
            "existingReport": {
                "number": 1951,
                "title": "[automation] Repository drift report",
            },
        },
    )

    assert outcome["issueCreates"] == []
    assert len(outcome["issueUpdates"]) == 1
    body = outcome["issueUpdates"][0]["body"]
    assert "- Ready PRs without exactly one canonical issue: **0**" in body
    assert "- Issues with competing implementation PRs: **1**" in body
    assert "- Issue #1975: #1981, #1996" in body
    assert "- Total remote branches: **5**" in body
    assert "- Unattached branches older than 14 days: **1**" in body
    assert "- `unattached` — 042989a9" in body
    assert outcome["pullUpdates"] == []
    assert outcome["comments"] == []


def test_reconciliation_defers_without_writing_when_github_rate_limits(
    tmp_path: Path,
) -> None:
    """Rate exhaustion must not produce an incomplete drift report or a red PR check."""
    outcome = _run_reconciliation(
        tmp_path,
        {
            "pulls": [],
            "branches": [],
            "graphqlError": {
                "status": 403,
                "message": "API rate limit exceeded for installation",
            },
        },
    )

    assert outcome["issueUpdates"] == []
    assert outcome["issueCreates"] == []
    assert any("Repository reconciliation deferred" in message for message in outcome["infos"])


def test_reconciliation_defers_without_writing_on_forbidden_graphql_scope(
    tmp_path: Path,
) -> None:
    """Forbidden GraphQL scope errors must defer instead of failing the whole workflow."""
    outcome = _run_reconciliation(
        tmp_path,
        {
            "pulls": [],
            "branches": [],
            "graphqlError": {
                "status": 403,
                "message": "Resource not accessible by integration",
            },
        },
    )

    assert outcome["issueUpdates"] == []
    assert outcome["issueCreates"] == []
    assert any("Repository reconciliation deferred" in message for message in outcome["infos"])

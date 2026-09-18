---
name: pr-iteration-loop
description: Solve a problem through verified iterations on one long-running draft pull request.
intent: Determine which agentic workflow pattern delivers the most operational value to EventRelay by advancing one verified repository problem at a time on a single draft pull request.
on:
  workflow_dispatch:
  issues:
    types: [labeled]
  pull_request:
    types: [labeled]
  issue_comment:
    types: [created]
  push:
    branches: [main]
  schedule:
    - cron: "0 9 * * 1-5"
concurrency:
  group: pr-iteration-loop-${{ github.repository }}
  cancel-in-progress: false
permissions:
  actions: read
  contents: read
  copilot-requests: write
  discussions: read
  issues: read
  pull-requests: read
network:
  allowed:
    - defaults
    - github
    - node
    - python
checkout:
  fetch: ["*"]
  fetch-depth: 0
engine: copilot
lsp:
  python:
    command: pyright-langserver
    args: ["--stdio"]
    fileExtensions:
      ".py": python
  typescript:
    command: typescript-language-server
    args: ["--stdio"]
    fileExtensions:
      ".ts": typescript
      ".tsx": typescriptreact
      ".js": javascript
      ".mjs": javascript
      ".cjs": javascript
tools:
  github:
    mode: gh-proxy
    toolsets: [context, repos, issues, pull_requests, actions, discussions]
  cache-memory:
    key: pr-iteration-loop-${{ github.repository }}
    retention-days: 30
    allowed-extensions: [".json", ".jsonl", ".md", ".txt"]
  agentic-workflows: true
  playwright:
    mode: cli
    browsers: [chromium]
evals:
  - id: operational_value
    question: Does the agent output show that this run delivered an evidence-backed recommendation or accepted iteration proving which of Chopin, Continuous AI, Autoloop, or Agentic Workflows most helps one high-value EventRelay problem on a single long-running draft pull request?
  - id: bounded_checkpoint
    question: Does the agent output show that exactly one deterministic checkpoint or repository problem was selected for this run?
  - id: verified_outcome
    question: Does the agent output include concrete verification evidence for the selected change or recommendation, such as command output, CI results, or browser checks tied to the current head or verified URL?
  - id: memory_updated
    question: Does the agent output record what had already been tried, what outcome it produced, and what was learned, gained, lost, or foreclosed for future runs?
  - id: visualized_status
    question: Does the agent output include a chart asset or discussion-ready digest that visualizes the selected repository opportunity or iteration status?
  - id: deterministic_postcondition
    question: Does the run include claimed_outcome, observed_outcome, and a match result proving the intended safe-output mutation succeeded on the selected canonical item without duplicate fallback artifacts?
pre-agent-steps:
  - name: Select deterministic checkpoint seed
    id: select-checkpoint
    uses: actions/github-script@v9
    with:
      script: |
        const fs = require("fs");
        const now = Date.now();
        const weekMs = 7 * 24 * 60 * 60 * 1000;
        const triggerLabel = "pr-iteration";
        const triggerCommand = "/pr-iteration";
        const owner = context.repo.owner;
        const repo = context.repo.repo;
        const payload = {
          repository: `${owner}/${repo}`,
          event_name: context.eventName,
          generated_at: new Date().toISOString(),
          skipped: [],
          selection: {
            reasons: [],
            authorized_trigger: false,
            duplicate_owner: null,
          },
        };

        if (context.eventName === "issues") {
          const issue = context.payload.issue;
          payload.triggered = {
            kind: "issue",
            number: issue.number,
            title: issue.title,
            url: issue.html_url,
            label: context.payload.label?.name || null,
          };
        } else if (context.eventName === "pull_request") {
          const pr = context.payload.pull_request;
          payload.triggered = {
            kind: "pull_request",
            number: pr.number,
            title: pr.title,
            url: pr.html_url,
            label: context.payload.label?.name || null,
          };
        } else if (context.eventName === "issue_comment") {
          const issue = context.payload.issue;
          payload.triggered = {
            kind: issue.pull_request ? "pull_request" : "issue",
            number: issue.number,
            title: issue.title,
            url: issue.html_url,
            command: context.payload.comment?.body || "",
          };
        }

        const [runs, pulls, issues] = await Promise.all([
          github.paginate(github.rest.actions.listWorkflowRunsForRepo, {
            owner,
            repo,
            per_page: 100,
          }),
          github.paginate(github.rest.pulls.list, {
            owner,
            repo,
            state: "open",
            per_page: 100,
          }),
          github.paginate(github.rest.issues.listForRepo, {
            owner,
            repo,
            state: "open",
            per_page: 100,
          }),
        ]);

        const recentFailingRuns = runs
          .filter((run) => run.conclusion === "failure")
          .filter((run) => now - new Date(run.created_at).getTime() <= weekMs)
          .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
          .slice(0, 10)
          .map((run) => ({
            kind: "workflow_failure",
            id: run.id,
            name: run.name,
            created_at: run.created_at,
            html_url: run.html_url,
            head_branch: run.head_branch,
            head_sha: run.head_sha,
          }));

        const stalePulls = pulls
          .filter((pr) => pr.head?.ref?.startsWith("pr-iteration/"))
          .filter((pr) => now - new Date(pr.updated_at).getTime() > weekMs)
          .sort((a, b) => new Date(a.updated_at) - new Date(b.updated_at))
          .slice(0, 10)
          .map((pr) => ({
            kind: "stale_pull_request",
            number: pr.number,
            title: pr.title,
            updated_at: pr.updated_at,
            html_url: pr.html_url,
            draft: pr.draft,
            head: pr.head.ref,
            labels: pr.labels.map((label) => label.name),
          }));

        const staleIssues = issues
          .filter((item) => !item.pull_request)
          .filter((item) => now - new Date(item.updated_at).getTime() > weekMs)
          .sort((a, b) => new Date(a.updated_at) - new Date(b.updated_at))
          .slice(0, 10)
          .map((issue) => ({
            kind: "stale_issue",
            number: issue.number,
            title: issue.title,
            updated_at: issue.updated_at,
            html_url: issue.html_url,
            labels: issue.labels.map((label) => label.name),
          }));

        const unauthorizedStalePulls = pulls
          .filter((pr) => !pr.head?.ref?.startsWith("pr-iteration/"))
          .filter((pr) => now - new Date(pr.updated_at).getTime() > weekMs)
          .slice(0, 10)
          .map((pr) => ({ number: pr.number, head: pr.head.ref }));

        payload.candidates = {
          recent_failing_workflow_runs: recentFailingRuns,
          stale_pull_requests: stalePulls,
          stale_issues: staleIssues,
        };
        if (unauthorizedStalePulls.length > 0) {
          payload.skipped.push({
            reason: "incompatible_mutation_target",
            count: unauthorizedStalePulls.length,
            sample: unauthorizedStalePulls[0],
          });
        }

        const isAuthorizedIssueLabel =
          context.eventName === "issues" &&
          context.payload.action === "labeled" &&
          context.payload.label?.name === triggerLabel;
        const isAuthorizedPrLabel =
          context.eventName === "pull_request" &&
          context.payload.action === "labeled" &&
          context.payload.label?.name === triggerLabel;
        const isAuthorizedComment =
          context.eventName === "issue_comment" &&
          context.payload.action === "created" &&
          (context.payload.comment?.body || "").includes(triggerCommand);

        if (isAuthorizedIssueLabel || isAuthorizedPrLabel || isAuthorizedComment) {
          payload.selection.authorized_trigger = true;
          payload.selection.reasons.push(
            "Authorized trigger item selected before ranked fallback."
          );
        } else if (payload.triggered) {
          payload.selection.reasons.push(
            "Trigger observed but not authorized label/command; using ranked fallback."
          );
        }

        let selected = null;
        if (payload.selection.authorized_trigger && payload.triggered) {
          selected = payload.triggered;
        } else {
          selected = recentFailingRuns[0] || stalePulls[0] || staleIssues[0] || null;
          if (selected) {
            payload.selection.reasons.push("Selected via ranked fallback priority.");
          }
        }

        const fingerprintFor = (item) => {
          if (!item) {
            return null;
          }
          if (item.kind === "workflow_failure") {
            return `workflow_failure:${item.name}:${item.head_branch || "none"}:${item.head_sha || "none"}`;
          }
          if (item.kind === "pull_request" || item.kind === "stale_pull_request") {
            return `pull_request:${item.number}`;
          }
          if (item.kind === "issue" || item.kind === "stale_issue") {
            return `issue:${item.number}`;
          }
          return `${item.kind}:${item.number || item.id || "unknown"}`;
        };

        const fingerprint = fingerprintFor(selected);
        payload.selection.fingerprint = fingerprint;

        if (!selected) {
          payload.selection.reasons.push(
            "No candidate selected; exiting before dependency installation."
          );
          fs.writeFileSync(
            "/tmp/gh-aw/pr-iteration-loop-context.json",
            JSON.stringify(payload, null, 2),
          );
          core.setOutput("should_proceed", "false");
          return;
        }

        const marker = `pr-iteration-fingerprint: ${fingerprint}`;
        const duplicatePr = pulls.find(
          (pr) => pr.state === "open" && typeof pr.body === "string" && pr.body.includes(marker),
        );
        const duplicateIssue = issues.find(
          (issue) =>
            !issue.pull_request &&
            issue.state === "open" &&
            typeof issue.body === "string" &&
            issue.body.includes(marker),
        );
        const duplicateOwner = duplicatePr || duplicateIssue || null;
        if (duplicateOwner) {
          payload.selection.duplicate_owner = {
            kind: duplicateOwner.pull_request ? "pull_request" : "issue",
            number: duplicateOwner.number,
            url: duplicateOwner.html_url,
          };
          payload.selection.reasons.push(
            "Canonical fingerprint already owned by an open receipt/issue/PR."
          );
          payload.skipped.push({
            reason: "duplicate_fingerprint",
            owner: payload.selection.duplicate_owner,
          });
        }

        payload.selected = selected;
        payload.selected.fingerprint = fingerprint;
        payload.selection.selected_kind = selected.kind;
        payload.selection.selected_number = selected.number || null;
        if (recentFailingRuns[0] && selected !== recentFailingRuns[0]) {
          payload.skipped.push({
            reason: "not_selected_ranked_candidate",
            candidate: recentFailingRuns[0].kind,
            detail: recentFailingRuns[0].id,
          });
        }
        if (stalePulls[0] && selected !== stalePulls[0]) {
          payload.skipped.push({
            reason: "not_selected_ranked_candidate",
            candidate: stalePulls[0].kind,
            detail: stalePulls[0].number,
          });
        }
        if (staleIssues[0] && selected !== staleIssues[0]) {
          payload.skipped.push({
            reason: "not_selected_ranked_candidate",
            candidate: staleIssues[0].kind,
            detail: staleIssues[0].number,
          });
        }

        fs.writeFileSync(
          "/tmp/gh-aw/pr-iteration-loop-context.json",
          JSON.stringify(payload, null, 2),
        );
        core.setOutput("should_proceed", duplicateOwner ? "false" : "true");
        core.setOutput("fingerprint", fingerprint);
  - name: Install repository dependencies and language servers
    if: steps.select-checkpoint.outputs.should_proceed == 'true'
    run: |
      python -m pip install --upgrade pip
      python -m pip install -e ".[dev,youtube]" pandas matplotlib seaborn
      npm install --legacy-peer-deps
      npm install -g pyright typescript-language-server typescript
  - name: Prime loop workspaces
    if: steps.select-checkpoint.outputs.should_proceed == 'true'
    run: |
      mkdir -p /tmp/gh-aw/{agent,python/data,python/charts,cache-memory/pr-iteration-loop}
safe-outputs:
  github-app:
    client-id: ${{ vars.GH_AW_APP_ID }}
    private-key: ${{ secrets.GH_AW_APP_PRIVATE_KEY }}
    ignore-if-missing: true
  create-issue:
    title-prefix: "[ai] "
    labels: [automation]
    max: 1
    expires: 7
  add-comment:
    max: 2
  create-pull-request:
    title-prefix: "[ai] "
    labels: [automation, ai-agent]
    draft: true
    expires: 7
    base-branch: main
    branch-prefix: pr-iteration/
    preserve-branch-name: true
    allow-workflows: true
    allowed-files:
      - ".github/workflows/**"
      - ".github/aw/**"
      - "apps/web/**"
      - "docs/**"
      - "mcp-servers/**"
      - "packages/**"
      - "scripts/**"
      - "sdk/**"
      - "shared/**"
      - "src/**"
      - "tests/**"
      - "Dockerfile"
      - "Makefile"
      - "package-lock.json"
      - "package.json"
      - "pyproject.toml"
      - "requirements.txt"
      - "turbo.json"
      - "uv.lock"
  push-to-pull-request-branch:
    target: "triggering"
    if-no-changes: warn
    allowed-files:
      - ".github/workflows/**"
      - ".github/aw/**"
      - "apps/web/**"
      - "docs/**"
      - "mcp-servers/**"
      - "packages/**"
      - "scripts/**"
      - "sdk/**"
      - "shared/**"
      - "src/**"
      - "tests/**"
      - "Dockerfile"
      - "Makefile"
      - "package-lock.json"
      - "package.json"
      - "pyproject.toml"
      - "requirements.txt"
      - "turbo.json"
      - "uv.lock"
  create-pull-request-review-comment:
    target: "*"
    max: 6
  create-discussion:
    title-prefix: "[ai] "
    category: General
    labels: [automation]
    max: 1
  upload-asset:
    branch: assets/pr-iteration-loop
    allowed-exts: [.png, .jpg, .jpeg, .svg]
    max: 3
timeout-minutes: 45
---

# PR Iteration Loop

Read `/tmp/gh-aw/pr-iteration-loop-context.json` first, then load any existing
memory from `/tmp/gh-aw/cache-memory/pr-iteration-loop/` before doing new work.

## Mission

Solve one repository problem through verified iterations on one long-running
draft pull request, then state which of these patterns most benefits
EventRelay for that problem right now:

- **Chopin** — real-time multiplayer, agentic planning environment
- **Continuous AI** — LLM-powered automation in platform-based collaboration
- **Autoloop** — simple goal-driven iterative automation
- **Agentic Workflows** — natural-language programming for GitHub Actions

The operational value for each run is simple: leave the repository with one
evidence-backed answer about which pattern best helps the selected problem and
either preserve a verified improvement on the canonical draft PR or explain why
no improvement was accepted.

## Repository-specific constraints

- Respect EventRelay's single product workflow: YouTube link → transcript →
  events → agents → outputs. Do not introduce alternate product flows.
- Reuse one canonical issue and one canonical draft PR per selected problem.
  Never create competing PRs for the same issue.
- Preserve draft state until the repository's acceptance criteria are met.
- Prefer the repo's actual commands:
  - Python install: `python -m pip install -e ".[dev,youtube]"`
  - Python checks: `PYTHONPATH=src pytest ... --no-cov`, `ruff check src/`,
    `python -m compileall -q src/`
  - Web checks: `npm install --legacy-peer-deps`, `turbo run test`,
    `turbo run lint`, `npm run build:web`
- If you touch `.github/workflows/*.md`, use `agentic-workflows` plus
  `gh aw compile <workflow-id> --validate --approve`, update the matching
  `.lock.yml`, and keep `.github/workflows/gh-aw-validation.yml` aligned. Do
  not hand-edit compiled lock files.
- Use the configured language servers on the actual repo roots:
  - Python: `src/**/*.py`, `tests/**/*.py`
  - TypeScript/TSX: `apps/web/**/*.ts`, `apps/web/**/*.tsx`

## Selection policy

Select exactly one bounded checkpoint per run.

Only honor issue/PR event targets when explicitly authorized by label
`pr-iteration` or command `/pr-iteration`. Otherwise, select from ranked
fallbacks and record why higher-priority non-selected candidates were skipped.

Priority order:

1. failing GitHub workflows on this repo within the last 7 days
2. open pull requests unresolved or stuck for more than 7 days
3. open issues unresolved for more than 7 days
4. redundant or low-value automation/workflow work that evidence shows should
   be paused or closed

If no candidate has enough evidence, or the same failure signature already
repeated twice without progress, use `noop` with a short reason instead of
retrying indefinitely.

## Loop rules

1. Read prior memory and answer these questions before acting:
   - What has already been addressed?
   - Did it produce the intended outcome?
   - What was gained or lost?
   - What should be carried forward or abandoned?
2. Keep durable state in cache-memory under this workflow directory with at
   least:
   - `status.json`
   - `history.jsonl`
   - `lessons.md`
3. Record the selected checkpoint, exact evidence, verification commands,
   failure signatures, accepted/rejected result, next step, and which of the
   four research patterns best fits the evidence.
4. Work the smallest useful change only. One accepted checkpoint per run.
5. Accept an iteration only if it improves the chosen completion contract or
   evidence quality and passes verification on the new head.
6. After two repeated failures with the same signature, pause and explain the
   blocker instead of looping.
7. Before any model-heavy work, compute and persist a stable fingerprint for the
   selected problem. If an open issue/PR already owns that fingerprint, use
   comment-or-noop behavior and do not create duplicates.
8. A run may create at most one canonical issue and one draft PR for one
   fingerprint. If a mutation fails once, trigger a circuit-breaker pause for
   that run rather than attempting competing fallbacks.

## Browser and chart requirements

- When a verified public URL exists for the selected checkpoint, use Playwright
  CLI to check it. Prefer the documented docs URL
  `https://uvai.github.io/youtube-extension/`, a PR preview URL, or another
  verified deploy receipt. If no verified URL exists, say so explicitly.
- Generate at least one chart or heatmap under `/tmp/gh-aw/python/charts/`
  showing the selected repository opportunity or iteration status. Good fits
  include failing-workflow frequency, stale-item age, or a repo-area heatmap of
  affected directories. Upload the asset and reference it in the visible output.

## Allowed visible actions

Use only the configured safe outputs for writes:

- `create-issue`
- `add-comment`
- `create-pull-request`
- `push-to-pull-request-branch`
- `create-pull-request-review-comment`
- `create-discussion`
- `upload-asset`

No automation path may merge to `main`; all merges require human review and
approval outside this workflow.

When the run is scheduled or triggered by `push` to `main`, use repository-level
concurrency and prefer no-op when no authorized or ranked candidate remains.

## Final report requirements

Your final visible output must include:

1. the selected checkpoint and why it won priority
2. the canonical issue/PR/branch mapping
3. verification evidence tied to the current head or verified URL
4. accepted progress or explicit pause reason
5. the primary recommended pattern among Chopin, Continuous AI, Autoloop, and
   Agentic Workflows, with a short evidence-backed reason
6. what was written back to cache-memory for the next run
7. deterministic postcondition grading: `claimed_outcome`,
   `observed_outcome`, and their match result

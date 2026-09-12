---
name: pr-iteration-loop
description: Solve a problem through verified iterations on one long-running draft pull request.
intent: Determine which agentic workflow pattern delivers the most operational value to EventRelay by advancing one verified repository problem at a time on a single draft pull request.
on:
  issues:
    types: [opened]
  pull_request:
    types: [opened, ready_for_review]
  push:
    branches: [main]
  schedule:
    - cron: "0 9 * * 1-5"
    - cron: "0 12 * * 1"
  skip-if-match: 'is:issue is:open "gh-aw-workflow-id: pr-iteration-loop" in:body'
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
pre-agent-steps:
  - name: Install repository dependencies and language servers
    run: |
      python -m pip install --upgrade pip
      python -m pip install -e ".[dev,youtube]" pandas matplotlib seaborn
      npm install --legacy-peer-deps
      npm install -g pyright typescript-language-server typescript
  - name: Prime loop workspaces
    run: |
      mkdir -p /tmp/gh-aw/{agent,python/data,python/charts,cache-memory/pr-iteration-loop}
  - name: Select deterministic checkpoint seed
    uses: actions/github-script@v9
    with:
      script: |
        const fs = require("fs");
        const now = Date.now();
        const weekMs = 7 * 24 * 60 * 60 * 1000;
        const owner = context.repo.owner;
        const repo = context.repo.repo;
        const payload = {
          repository: `${owner}/${repo}`,
          event_name: context.eventName,
          generated_at: new Date().toISOString(),
        };

        if (context.eventName === "issues") {
          const issue = context.payload.issue;
          payload.triggered = {
            kind: "issue",
            number: issue.number,
            title: issue.title,
            url: issue.html_url,
          };
        } else if (context.eventName === "pull_request") {
          const pr = context.payload.pull_request;
          payload.triggered = {
            kind: "pull_request",
            number: pr.number,
            title: pr.title,
            url: pr.html_url,
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

        payload.candidates = {
          recent_failing_workflow_runs: recentFailingRuns,
          stale_pull_requests: stalePulls,
          stale_issues: staleIssues,
        };
        payload.selected =
          recentFailingRuns[0] || stalePulls[0] || staleIssues[0] || null;

        fs.writeFileSync(
          "/tmp/gh-aw/pr-iteration-loop-context.json",
          JSON.stringify(payload, null, 2),
        );
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
    target: "*"
    required-title-prefix: "[ai] "
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
  merge-pull-request:
    target: "*"
    required-labels: [ready-to-merge]
    allowed-branches: ["pr-iteration/*"]
    max: 1
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
- `merge-pull-request`
- `create-pull-request-review-comment`
- `create-discussion`
- `upload-asset`

When the run is scheduled or triggered by `push` to `main`, prefer a narrative
discussion digest only when there is new verified information worth publishing.

## Final report requirements

Your final visible output must include:

1. the selected checkpoint and why it won priority
2. the canonical issue/PR/branch mapping
3. verification evidence tied to the current head or verified URL
4. accepted progress or explicit pause reason
5. the primary recommended pattern among Chopin, Continuous AI, Autoloop, and
   Agentic Workflows, with a short evidence-backed reason
6. what was written back to cache-memory for the next run

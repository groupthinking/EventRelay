# PR Remediation Run — 2026-07-29

Runbook: PR Remediation & Publish Runbook (RASOR). GitHub surface: `github-mcp`
(PR read + comment + merge). Scan performed against `groupthinking/eventrelay`,
oldest-first. Auto-merge policy: `label:automerge` (no open PR carries it) → every
merge to protected `main` remains a human gate by design. Prior records: #1044
(2026-07-27), #1059 (2026-07-28).

## Definition-of-done outcome

- **Open PRs scanned:** 36
- **Autonomously mergeable this run:** 0 — the correct, safe outcome, not a failure.
  All 36 open PRs are drafts (scope-gated → `DEFERRED(draft)`). Merging any of them
  requires the author to first mark the PR ready and a human to clear the publish gate
  on protected `main`.
- **Terminal-state tally:** 36 `DEFERRED(draft)`, 0 `HALTED`, 0 `MERGED`.
- **Delta vs 2026-07-28:** +3 net open PRs (33 → 36). New since last run: #1059
  (the 07-28 triage record itself), #1064 (`docs(runbook)` Google OAuth 403 diagnosis),
  #1075 (`fix(pipeline)` preserve captured transcript on analysis timeout). No PR was
  merged or closed between runs.
- **#903 status change:** on 2026-07-28 #903 was the single non-draft, human-gated PR
  (`HALTED(awaiting_human_production_approval)`). It has since been **restored to draft**
  (`draft: true`, head `jules-15243187445261469621-ffdb089e@57ff988`,
  `mergeable_state: unstable`). It therefore scope-gates to `DEFERRED(draft)` this run —
  no PR remains in a HALTED (human-decision-pending) state today.

## Why zero autonomous merges (unchanged, structural)

1. **Every open PR is a draft.** The runbook scope gate routes drafts to
   `DEFERRED` — the author must request review before any remediation loop can advance
   them. This is a repo-wide posture, not a per-PR defect.
2. **Protected `main` + human publish gate.** No open PR carries the `automerge` label,
   so `auto_merge_policy: label:automerge` yields no eligible merge. Auto-merging to a
   protected branch is explicitly out of scope for the runbook.
3. **No outward-facing CodeRabbit fan-out performed.** Posting `@coderabbitai full review`
   across 36 draft PRs (15 of them dependabot bumps, several duplicate bot proposals)
   would consume the paid review allowance for no mergeable outcome. Deferred until a PR
   flips to ready.

## Deferred — drafts (scope gate: draft → `DEFERRED(draft)`)

| PR | Age (d) | Author | Title | Terminal state |
|----|---------|--------|-------|----------------|
| 734 | 17 | groupthinking | fix(security): pin cloud callbacks against DNS rebinding | DEFERRED(draft) |
| 810 | 12 | groupthinking | fix(security): sanitize user-controlled values in API logs (CWE-117) | DEFERRED(draft) |
| 831 | 12 | groupthinking | fix(security): restore CWE-209 response protections | DEFERRED(draft) |
| 869 | 11 | groupthinking | fix: harden API-cost webhook outbox retries (MYX-79) | DEFERRED(draft) |
| 903 | 9 | jules[bot] | fix(auth): restore Google OAuth configuration in Vercel production | DEFERRED(draft) |
| 906 | 9 | groupthinking | fix(ci): remediate PR #877 rollout and verification gaps | DEFERRED(draft) |
| 961 | 6 | jules[bot] | [DRAFT EVIDENCE] duplicate dashboard accessibility proposal | DEFERRED(draft) |
| 987 | 4 | Copilot | [DRAFT EVIDENCE] unbound CI and module-shadowing proposal | DEFERRED(draft) |
| 995 | 4 | groupthinking | perf(mcp): reuse pooled aiohttp session in orchestrator | DEFERRED(draft) |
| 996 | 4 | groupthinking | fix(mcp): actually reuse pooled aiohttp session | DEFERRED(draft) |
| 997 | 4 | jules[bot] | Bolt: optimize layout boundary in AgentFlowVisualizer | DEFERRED(draft) |
| 999 | 4 | dependabot | build(deps): bump gh-aw-actions/setup 0.82.14→0.83 | DEFERRED(draft) |
| 1000 | 4 | dependabot | build(deps): bump actions/checkout 4.2.2→7.0.1 | DEFERRED(draft) |
| 1001 | 4 | dependabot | build(deps): bump actions/setup-python 6→7 | DEFERRED(draft) |
| 1002 | 4 | dependabot | build(deps-dev): bump locust 2.45.0→2.46.0 | DEFERRED(draft) |
| 1003 | 4 | dependabot | build(deps): bump actions/github-script 8→9 | DEFERRED(draft) |
| 1004 | 4 | dependabot | build(deps): bump @opentelemetry/exporter-trace-otlp-http | DEFERRED(draft) |
| 1005 | 4 | dependabot | build(deps): bump @opentelemetry/core 2.9.0→2.10.0 | DEFERRED(draft) |
| 1006 | 4 | dependabot | build(deps): bump @opentelemetry/instrumentation | DEFERRED(draft) |
| 1007 | 4 | dependabot | build(deps): bump @opentelemetry/resources 2.9.0→2.10.0 | DEFERRED(draft) |
| 1008 | 4 | dependabot | build(deps): bump @opentelemetry/sdk-trace-base | DEFERRED(draft) |
| 1020 | 3 | jules[bot] | perf: optimize call stack operations and string allocations | DEFERRED(draft) |
| 1022 | 3 | jules[bot] | perf(web): optimize bounding box in AgentFlowVisualizer | DEFERRED(draft) |
| 1038 | 2 | jules[bot] | feat: implement MCPOrchestrator._execute_on_server E2E | DEFERRED(draft) |
| 1040 | 2 | groupthinking | fix(mcp): green up MCPOrchestrator._execute_on_server E2E | DEFERRED(draft) |
| 1043 | 2 | jules[bot] | perf(web): optimize viewBox boundary computation | DEFERRED(draft) |
| 1044 | 2 | groupthinking | docs(triage): PR remediation run 2026-07-27 | DEFERRED(draft) |
| 1045 | 2 | jules[bot] | Palette: add keyboard focus-visible styling to dashboard | DEFERRED(draft) |
| 1047 | 2 | jules[bot] | ci: suppress failure issues on no-op runs | DEFERRED(draft) |
| 1049 | 2 | groupthinking | fix(a11y): complete dashboard focus contrast + coverage | DEFERRED(draft) |
| 1050 | 2 | jules[bot] | configure agentic workflows no-op comment suppression | DEFERRED(draft) |
| 1052 | 2 | jules[bot] | fix: allow awmg-mcpg gateway in workflow firewalls | DEFERRED(draft) |
| 1055 | 1 | dependabot | build(deps): bump npm-minor-patch group | DEFERRED(draft) |
| 1059 | 1 | groupthinking | docs(triage): PR remediation run 2026-07-28 | DEFERRED(draft) |
| 1064 | 1 | groupthinking | docs(runbook): diagnose Google OAuth 403 org_internal | DEFERRED(draft) |
| 1075 | 0 | groupthinking | fix(pipeline): preserve captured transcript on analysis timeout | DEFERRED(draft) |

## Duplicate clusters worth a human close (housekeeping, not autonomous)

These are labeled `duplicate` by the repo's own triage automation and represent
redundant bot proposals accumulating in the backlog. A human closing the superseded
members would shrink the draft queue without any code risk:

- **AgentFlowVisualizer boundary/viewBox perf:** #997, #1022, #1043 (and related #1020)
  — repeated bot passes over the same layout-computation hot path.
- **OpenTelemetry JS bumps:** #1004–#1008 all tagged `duplicate` (overlap with the
  #1055 `npm-minor-patch` group bump).
- **aiohttp pooled-session reuse:** #995 vs #996 (same MCP orchestrator change).

## Loop decision

**More autonomous work available: no.** Every open PR is a draft; none carries
`automerge`; the one previously human-gated PR (#903) has been returned to draft. The
remediation loop cannot advance any PR to `MERGED` without a human first marking a PR
ready for review and clearing the protected-`main` publish gate. This matches the
2026-07-27 (#1044) and 2026-07-28 (#1059) conclusions — the backlog is human-gated by
design, so the loop should idle until a draft flips to ready, a PR gains `automerge`, or
the owner acts on the #903 / #900 production-OAuth decision.

## This run's branch (`claude/determined-maxwell-82cm3w`)

Beyond this triage record, the run's branch carries the **refreshed canonical CWE-209
response-sanitization work for #831** (13 commits, ~1000 insertions across
`cloud_api_endpoints.py`, `real_api_endpoints.py`, `cloud_ai_routes.py`,
`official_api.py`, `code_generator.py`, and their tests), rebased onto verified `main`
(0 commits behind). It is surfaced here as a **draft** PR for human review — it is a
security change, so it stays behind the same human publish gate as every other PR and is
not auto-merged.

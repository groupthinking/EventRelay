# Agent Orchestration Standard Operating Procedure (SOP) & Inventory

## 1. Introduction & Mission
The mission of the EventRelay AI Agent Orchestration team is to enable high-integrity, autonomous planning, reasoning, and execution of Model Context Protocol (MCP) servers and Video Intelligence pipelines.

To maintain safety, reliability, and security, all dispatched agents must follow these strictly defined Standard Operating Procedures (SOP) without deviation.

---

## 2. Team Directory & Roles

Our orchestration relies on a multi-agent cooperative framework with specialized roles:

- **@Copilot (Lead Organizer)**: Responsible for overall PR organization, triage, diagnostic coordination, and high-level strategy. Grants final approval for draft decisions, commits, closing, and merging on the canonical repository.
- **@Claude (Reasoning & Code Architect)**: Specialized in advanced reasoning, applying Chain-of-Thought (CoT) logic, structural refactoring, and complex backend implementation.
- **/gemini (@Gemini) (Verification & Pipeline Specialist)**: Specialized in verification, running E2E pipeline checks, validating Next.js frontend, and auditing media processing code.
- **@Codex (Execution Engine)**: The primary engine executing workflow steps, and handling repository delivery.

---

## 3. Communication & Handoff Protocols

To ensure seamless progress and full context sharing, communication among agents must follow these rules:

1. **Single Thread of Execution**: Only one agent runs at a time. The current agent must conclude their execution by handing off and tagging the next agent.
2. **Standardized Handoff Format**: The handoff comment must conclude with:
   - **Current State**: Summary of what was accomplished.
   - **Blockers / Observations**: Any identified issues.
   - **Next Step**: A clear, concise, actionable directive for the receiving agent.
   - **Tag**: The explicit tagging of the receiving agent (e.g., `@Claude`).
3. **Verification Before Handoff**: No work is handed off or declared complete without running local verification gates and tests.
4. **Handoff Target**: Upon completion of any subtask, the executing agent must tag `@Copilot` to ask for a PR review and to progress the PR to the next step if acceptable.

---

## 4. Current Truth & Status Inventory

The following is the current exact-head status of the repository:

### 4.1. Complete
- ✅ **Authoritative Coverage Workflow**: The `Coverage` workflow (`.github/workflows/coverage.yml`) has been fully repaired. It is authoritative, runs tests under python 3.12 without `continue-on-error` or `|| true` on the runner, and relies on strict `pyproject.toml` configurations.
- ✅ **Obsolete Workflow Removal**: The obsolete `.github/agentic/verification-loop.aw.yml` was deleted.
- ✅ **gh-aw Compiler & Version Pinning**: `gh-aw Validation` workflow pins `github/gh-aw` to stable version `v0.82.14` and compiles source `.md` files to their `.lock.yml` equivalents while performing actionlint, zizmor, and poutine security checks.

### 4.2. Staged
- ⏸ **EventRelay CI Investigator**: Staged in read-only report-first mode triggered on `workflow_run` events (not hourly AI sweep) to avoid high API costs.
- ⏸ **Canonical PR Remediator**: Staged to run only on existing canonical PR branches connected to a focused-child issue of `#898`.
- ⏸ **Focused Coverage Controller**: Staged to run in read-only mode to prevent continuous, expensive AI execution.

### 4.3. Blocked / Not Done
- ❌ **Cloud Tasks Authentication Mismatch**: Cloud Tasks are enqueued without OIDC or `X-API-Key`, but callbacks require `X-API-Key`.
- ❌ **Non-Durable Execution State**: State is held in JSON and in-memory maps/asyncio tasks, risking state loss during Cloud Run instance recycling.
- ❌ **Incomplete MCP Execution**: Server execution path inside `MCPOrchestrator._execute_on_server` and `src/youtube_extension/orchestrator/main.py` raises `NotImplementedError`.

---

## 5. Bounded Agent Constraints (Guardrails)

All agents are subject to the following strict safety guardrails:
1. **Fork Scope Gate**: Never commit, merge, or push work into the parents or original pre-fork repo. Only write to the `Groupthinking` account.
2. **Credential Safety**: Never use or modify Vercel, Google OAuth, database, GCP, Sentry-management, or production application credentials.
3. **No Automatic Upgrades**: Do not upgrade `gh-aw`, Node packages, or Python packages to `@latest` or unpinned floating versions.
4. **No Structural Workflows Modification**: Agents must never weaken rulesets, workflow checks, or security configurations.

---

## 6. Next Steps & Action Plan

1. **Dispatch @Claude** to analyze and draft solutions for the **Cloud Tasks Authentication Mismatch** and **Non-Durable Execution State** issues.
2. Claude will provide the technical design and implement the fixes, accompanied by rigorous unit tests.
3. **Dispatch @Gemini** to run the complete verification suite, including E2E, Next.js type-checks, and lints, to certify production readiness.
4. **@Copilot** will perform final review, merge, and close.

# Jules Agent System: Nightly Audit & Ruthless Remediation

**Role:** High-Integrity Systems Auditor & First-Principles Engineer
**Frequency:** Nightly Execution (02:00 UTC)

## 1. Objective: The Audit Trace

You are tasked with a nightly deep-scan of all system logs, transaction traces, and state changes. Your goal is not just to find "failures," but to identify **divergences from first principles** (e.g., "Is this data state logically possible given the laws of the system?").

## 2. Analysis Phase: First-Principles Inquiry

For every error, bottleneck, or inconsistency discovered, you must execute a "Five Whys" interrogation:

* **Identify the Issue:** Define the exact delta between the expected state and the actual state.
* **The Origin Inquiry:** Ask exactly *how* and *why* the system architecture allowed this state to exist. Do not accept "random glitch" as an answer; find the logic gap.
* **Clean-up Motives:** Propose immediate mitigation to restore service or data integrity.

## 3. Execution Phase: Ruthless Solutions

You are authorized to take autonomous action on **all** issues found. You must bypass "band-aid" fixes in favor of **ruthless, proven solutions**:

* **Discard the Fragile:** If a component fails consistently, your suggested action should be a structural rewrite rather than a patch.
* **Atomic Remediation:** Ensure every fix is idempotent and verified against the system's core constraints.
* **No Half-Measures:** If a record is corrupt, quarantine and rebuild from the last known-good state; do not attempt to "guess" missing data.

## 4. Fortification: Preventative Measures

Every remediation must be accompanied by a hard-coded preventative measure. This includes:

* **Constraint Injection:** Adding schema-level or logic-level guards to make the error mathematically impossible to repeat.
* **Automated Regression:** Creating a new trace-point specifically for this failure mode to catch it in real-time before the next nightly audit.

## Implementation Instructions for Jules

1. **Initialize Audit Agent:** Load the trace logs for the previous 24-hour window.
2. **Filter Logic:** Flag any status code > 400 or any latency > 200ms.
3. **Action Loop:**
   * **IF** issue found **THEN** execute `FirstPrinciplesAnalysis()`.
   * **EXECUTE** `RuthlessCleanup()`.
   * **DEPLOY** `PreventativeGuard()`.
4. **Reporting:** Summarize all "Ruthless Actions" taken and list the new constraints added to the system.

## Workflow Integration
* **GCP:** Monitor logs and service health.
* **GITHUB:** Track code changes and potential regressions.
* **SUPABASE:** Verify data integrity and execute cleanup.

To execute this audit manually or test the agent logic, run:
```bash
PYTHONPATH=src python3 scripts/nightly_audit_agent.py --dry-run
```
# AGENTS.md

## Mission
To enable autonomous AI agents to efficiently reason, plan, and execute tasks within this repository, specifically focusing on the integration and orchestration of Model Context Protocol (MCP) servers and Video Intelligence pipelines.

## Scope of "Actionable Room"
Agents are granted permission and encouraged to:
1.  **Modify and Expand `mcp-servers/`**: Create new MCP servers, update existing ones, and refactor code to improve modularity and performance.
2.  **Improve Automation**: Create and edit GitHub Actions workflows (`.github/workflows/`) to add robust testing and verification for new features.
3.  **Refactor for Clarity**: Improve documentation (READMEs) and code structure to facilitate better "Machine Readability" and "Human Understandability".

## Protocols
1.  **Verify Before Submit**:
    - Always run relevant verification scripts or tests before submitting changes.
    - If no test exists for a new feature, **create one**.
2.  **CI/CD Alignment**:
    - Ensure all changes pass existing CI checks.
    - When adding a new component (like an MCP server), add a corresponding CI workflow to ensure it remains functional.
3.  **Cross-Platform Compatibility**:
    - Write code that is compatible with Linux and Windows environments whenever possible (e.g., handling `asyncio` loops correctly).
4.  **Documentation**:
    - Update `README.md` files when interface changes occur.
    - Document limitations (e.g., "Text-only CLI wrapper") clearly.

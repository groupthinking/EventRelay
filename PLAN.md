# TASK: Clean obsolete unused surface (scripts / infra / dead tests)

## 1. Goal & Scope
* **Objective:** Remove obsolete unused leftovers that must not be wired into the live UVAI ship path (Origin G.A.T.E. / Video Pack / Studio), and relocate the one live dependency (`knowledge_base`) out of `scripts/`.
* **Context:** Nightly audit + follow-up confirmed Fly deploy, empty autonomous-video stage runners, broken nightly audit stubs, Ray K8s manifests, and deleted-backend verify/load probes should not be used.
* **Scope:** Completed as listed below. Kept `src/uvai/ml/**`, `apps/backend`, SDK mock tests.

## 2. Execution Plan
- [x] Delete Fly / nightly / autonomous-video / Ray K8s / dead probes
- [x] Relocate knowledge_base and fix importer
- [x] Retarget e2e redirect assertions
- [x] Update CHANGELOG + workflow README / emergency-stop / AGENTS.md
- [x] Verify, commit, push, open PR

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Dead surfaces gone; knowledge_base importable from `agents.knowledge_base`; e2e asserts redirect contract.
* **Verification Method:** `rg` for deleted paths; focused pytest import + unit tests.
* **Proof Artifact:** `PYTHONPATH=src` knowledge_base + MCP call OK; `pytest tests/unit/test_mcp_routed_false_success_2168.py` → 23 passed.

## 4. Post-Task Reflection
* **What was done:** Deleted obsolete Fly/nightly/autonomous-video/Ray-K8s/dead-backend probe surfaces; moved knowledge_base into `src/agents/`; retargeted e2e redirects.
* **Why it was needed:** Leftovers implied a parallel product/deploy path that is not authorized and confused CI/docs.
* **How it was tested:** Import/call check for relocated KB; 23 focused MCP unit tests passed.
* **CI note:** PR body includes `Closes #2455` for the require-issue-closer gate.

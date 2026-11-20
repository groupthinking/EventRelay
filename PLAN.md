# TASK: Clean obsolete unused surface (scripts / infra / dead tests)

## 1. Goal & Scope
* **Objective:** Remove obsolete unused leftovers that must not be wired into the live UVAI ship path (Origin G.A.T.E. / Video Pack / Studio), and relocate the one live dependency (`knowledge_base`) out of `scripts/`.
* **Context:** Nightly audit + follow-up confirmed Fly deploy, empty autonomous-video stage runners, broken nightly audit stubs, Ray K8s manifests, and deleted-backend verify/load probes are still present and should not be used.
* **Scope:**
  * KILL: Fly deploy script + token refs; nightly audit agent + unit test + AGENTS.md dry-run tip; autonomous-video CI scripts/workflow/tests/docs refs; `infrastructure/k8s/ray/**`; deleted-backend verify/populate/load probes; `AUTOMATION_LAUNCHER.sh` localhost:8000 markdown path.
  * RELOCATE: `scripts/knowledge_base.py` → `src/agents/knowledge_base.py`; fix `mcp_agent_network` import.
  * RETARGET: `tests/e2e/pipeline.test.ts` `/features` and `/dashboard` expectations to permanent redirects (`/` and `/studio`).
  * KEEP: `src/uvai/ml/**` (library + unit tests), `apps/backend` caption service + its tests, SDK mock-based tests.
* *Initial check:* Prefer delete/relocate existing files; no new product machinery.

## 2. Execution Plan
- [ ] Delete Fly / nightly / autonomous-video / Ray K8s / dead probes
- [ ] Relocate knowledge_base and fix importer
- [ ] Retarget e2e redirect assertions
- [ ] Update CHANGELOG + workflow README / emergency-stop / AGENTS.md
- [ ] Run focused pytest + e2e type sanity; commit; push; open PR

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Dead surfaces gone; knowledge_base importable from `src.agents`; e2e asserts redirect contract; no remaining references to deleted paths in CI.
* **Verification Method:** `rg` for deleted paths returns none in live code/CI; focused unit tests for agents/knowledge_base; pytest collect on remaining tests.
* **Proof Artifact:** Command output in PR verification section.

## 4. Post-Task Reflection
* **What was done:** (fill after)
* **Why it was needed:** (fill after)
* **How it was tested:** (fill after)

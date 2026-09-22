# Audit remediation status (#2175)

**Source session:** [36f6c3e5-60dc-4dfe-a151-ef2ab9114afa](https://github.com/groupthinking/EventRelay/tasks/36f6c3e5-60dc-4dfe-a151-ef2ab9114afa)  
**Master index:** [.github/AUDIT_FINDINGS_SESSION.md](../.github/AUDIT_FINDINGS_SESSION.md)  
**Phase 1 merge:** `dc2aa69b0` on `main`  
**Phase 2 merge:** `bb06a0417` on `main` (PR [#2190](https://github.com/groupthinking/EventRelay/pull/2190))  
**Closeout narrative:** [AUDIT_SESSION_CLOSEOUT_REPORT.md](./AUDIT_SESSION_CLOSEOUT_REPORT.md)

| ID | Issue | Phase | Status |
| --- | --- | --- | --- |
| AUDIT-001 | #2163 Video Pack dual store | 1 | **Done** — Upstash REST factory; FS dev-only |
| AUDIT-002 | #2164 G.A.T.E. verification | 1–2 | **Done** — Origin attestations + HTTP probe in origin-gate & Studio |
| AUDIT-003 | #2165 Reconciliation workflow | 1 | **Done** — REST protection; verification.yml dispatch-only |
| AUDIT-004 | #2166 Agent orchestration | 2 | **Done** — `AGENT_ORCHESTRATION_TRUTH.md` + pipeline warning |
| AUDIT-005 | #2167 Duplicate API routes | 2 | **Done** — v1 video routes re-export canonical handlers |
| AUDIT-006 | #2168 Bare exceptions | 2 | **Done** — `EXCEPTION_HANDLING_STANDARDS.md` + disclosure tests |
| AUDIT-007 | #2169 SQL vs migrations | 2 | **Done** — `MIGRATION_TRUTH.md` + inventory test |
| AUDIT-008 | #2170 Architecture narratives | 3 | **Done** — `CURRENT_ARCHITECTURE.md` |
| AUDIT-009 | #2171 MCP routing | 3 | **Done** — `MCP_ORCHESTRATION_ROUTING.md` + registry test |
| AUDIT-010 | #2172 Open issue triage | 3 | **Done** — `AUDIT_ISSUE_TRIAGE.md` |
| AUDIT-011 | #2173 yt-dlp fallback | 4 | **Done** — circuit breaker + tests |
| AUDIT-012 | #2174 undici overrides | 4 | **Done** — `WORKFLOW_DEVKIT_OVERRIDES.md` |

## Verification

```bash
PYTHONPATH=src python3 -m pytest tests/unit/test_ytdlp_circuit_breaker.py tests/unit/test_migration_truth.py tests/unit/test_mcp_registry_routing.py tests/unit/test_videopack_store_factory.py -o addopts= -q
npm --workspace=apps/web run test -- --run src/lib/__tests__/origin-gate.test.ts src/lib/__tests__/gate-transition.test.ts
```

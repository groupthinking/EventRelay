# Audit remediation status (#2175)

**Source session:** [36f6c3e5-60dc-4dfe-a151-ef2ab9114afa](https://github.com/groupthinking/EventRelay/tasks/36f6c3e5-60dc-4dfe-a151-ef2ab9114afa)  
**Master index:** [.github/AUDIT_FINDINGS_SESSION.md](../.github/AUDIT_FINDINGS_SESSION.md)  
**Implementation PR:** #2188 (`cursor/audit-remediation-tracker-9e63`)  
**Closeout narrative:** [AUDIT_SESSION_CLOSEOUT_REPORT.md](./AUDIT_SESSION_CLOSEOUT_REPORT.md) (14-session + 12-issue matrix)

| ID | Issue | Phase | Status in #2188 |
| --- | --- | --- | --- |
| AUDIT-001 | #2163 Video Pack dual store | 1 | **Done** — Upstash REST factory; FS dev-only |
| AUDIT-002 | #2164 G.A.T.E. verification | 1 | **Partial** — HTTP probe + `/api/gate/probe-live`; Origin ownership unchanged |
| AUDIT-003 | #2165 Reconciliation workflow | 1 | **Done** — remove `branchProtectionRule`; FORBIDDEN degrade |
| AUDIT-004 | #2166 Agent orchestration | 2 | **Doc** — `AGENT_ORCHESTRATION_TRUTH.md` |
| AUDIT-005 | #2167 Duplicate API routes | 2 | **Doc** — `API_ROUTE_VERSIONING.md`; pack routes share handlers |
| AUDIT-006 | #2168 Bare exceptions | 2 | **Doc** — `EXCEPTION_HANDLING_STANDARDS.md` |
| AUDIT-007 | #2169 SQL vs migrations | 2 | **Follow-up PR** |
| AUDIT-008 | #2170 Architecture narratives | 3 | **Partial** — README + gate contract; REPO_MAP pointer |
| AUDIT-009 | #2171 MCP routing | 3 | **Doc** — `MCP_ORCHESTRATION_ROUTING.md` |
| AUDIT-010 | #2172 Open issue triage | 3 | **Follow-up** — matrix in this file; manual triage |
| AUDIT-011 | #2173 yt-dlp fallback | 4 | **Doc** — `YTDLP_OPERATIONS.md`; code breaker TBD |
| AUDIT-012 | #2174 undici overrides | 4 | **Doc** — `WORKFLOW_DEVKIT_OVERRIDES.md` |

## Session log acknowledgment

The full deep-research event stream lives in the linked GitHub task session (1000+ events). The repository copy of record for findings is `.github/AUDIT_FINDINGS_SESSION.md` (revision 1, 2026-09-19). Remediation work traces each issue back to that index and the templates in `.github/audit-issues.template.md`.

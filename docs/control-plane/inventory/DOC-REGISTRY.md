# DOC REGISTRY — Classification (bootstrap)

**Created:** 2026-07-09T23:15:00Z  
**Rule:** Classification only. Physical moves happen under GATE-6 with a logged list.  
**Classes:** `CANONICAL` · `OPERATIONAL` · `HISTORICAL` · `CONCEPT` · `STALE-DO-NOT-TRUST` · `AGENT-ENTRY`

---

## 1. Control plane (this program)

| Path | Class |
|------|--------|
| `docs/control-plane/00-CEO-DIRECTIVE.md` | **CANONICAL** |
| `docs/control-plane/plans/EXECUTION-PLAN.md` | **CANONICAL** |
| `docs/control-plane/inventory/LIVE-STATUS.md` | **CANONICAL** (must refresh) |
| `docs/control-plane/inventory/SURFACES.md` | **CANONICAL** |
| `docs/control-plane/inventory/DOC-REGISTRY.md` | **CANONICAL** |
| `docs/control-plane/sessions/*` | **OPERATIONAL** evidence |
| `CONTROL.md` (repo root pointer) | **AGENT-ENTRY** |

---

## 2. Root entry / agent files

| Path | Class | Note |
|------|--------|------|
| `README.md` | OPERATIONAL + marketing | Keep; ship claims must match LIVE-STATUS |
| `AGENTS.md` | AGENT-ENTRY | Jules-oriented; must point to control-plane |
| `CLAUDE.md` | AGENT-ENTRY | Must point to control-plane |
| `GEMINI.md` | AGENT-ENTRY | Must point to control-plane |
| `ARCHITECTURE.md` | **STALE-DO-NOT-TRUST** | Wrong folder map vs tree |
| `LAUNCH_CHECKLIST.md` | OPERATIONAL | Re-verify every checkbox live |
| `BACKEND_DEPLOY.md` | OPERATIONAL | Useful; confirm service names vs gcloud list |
| `CONTRIBUTING.md` | OPERATIONAL | |
| `SECURITY.md` | OPERATIONAL | |
| `CHANGELOG.md` | HISTORICAL | |
| `eventrelay-audit-report.md` | OPERATIONAL security baseline | High findings still open until GATE-4 |
| `.audit-findings.json` | OPERATIONAL | Machine form of audit |

---

## 3. `docs/` top-level markdown (initial pass)

| Path | Class | Note |
|------|--------|------|
| `docs/MASTER_ROADMAP.md` | OPERATIONAL (aspirational) | North star useful; Phase dates stale |
| `docs/CAPABILITIES_AUDIT.md` | OPERATIONAL | Vendor depth honest |
| `docs/FRONTEND_CONSOLIDATION.md` | OPERATIONAL | Domain consolidation history |
| `docs/API_REFERENCE.md` | OPERATIONAL | Reconcile with live OpenAPI later |
| `docs/ONBOARDING.md` | STALE risk | Claims “production-ready” tone |
| `docs/TECH_STACK.md` | STALE risk | Cloud SQL names mismatch UI |
| `docs/ARCHITECTURE.md` / `ARCHITECTURE_DIAGRAM.md` | STALE-DO-NOT-TRUST | Prefer tree + control-plane |
| `docs/EventRelay-Full-System-Breakdown.md` | HISTORICAL / sprawl | Do not expand |
| `docs/refactor/STATE.md` | HISTORICAL | 2026-06-23 hybrid refactor |
| `docs/triage/pr-remediation-*.md` | HISTORICAL | Keep for PR archaeology |
| `docs/branch-cleanup-*.md` | OPERATIONAL | Use in GATE-1 branch work |
| `docs/deployment/*` | OPERATIONAL | Prefer after LIVE-STATUS |
| `docs/guides/*` | MIXED | Classify file-by-file in GATE-6 |
| `docs/knowledge_prototypes/*` | CONCEPT / HISTORICAL | Not ship path |
| `docs/analysis/*` `docs/reports/*` | HISTORICAL | |
| `docs/superpowers/*` | CONCEPT | |
| `docs/VTB_RECONCILIATION_PLAN.md` | CONCEPT | |
| `docs/VERA_AUDIT_REPORT.md` | HISTORICAL | VERA source missing |

---

## 4. Outside repo (do not “fix” into monorepo blindly)

| Path | Class |
|------|--------|
| Drive `UVAI + concept ` | CONCEPT |
| Documents `UVAI_MASTER_SPECIFICATION.md` | CONCEPT |
| `/Users/garvey/Dev/ALL VID-ANYTHING /` | ARCHIVE |
| `/Users/garvey/Dev/MASTER_PROMPT.md` | STALE (conflict markers) |

---

## 5. Move policy (GATE-6 only)

When moving a file:

1. Add row to `sessions/doc-moves-YYYY-MM-DD.md` with old path → new path  
2. Leave a 5-line stub at old path pointing to new path for 14 days (or Git history only if no external links)  
3. Never move `.env*` or credential files into docs  

**Preferred archive root:** `docs/control-plane/archives/yyyy-mm/`  

---

## 6. Registry completion checklist

- [ ] Every file under `docs/*.md` classified (GATE-6)  
- [ ] Every root `*.md` classified (partial done)  
- [ ] Broken links after moves grepped  
- [ ] README points to CONTROL.md  

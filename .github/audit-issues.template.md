# Audit Issue Templates

These templates are used to create the 12 connected audit issues from the deep research session.
**Master findings:** `.github/AUDIT_FINDINGS_SESSION.md`

---

## [AUDIT-001] Dual Video Pack Persistence Systems (🔴 CRITICAL)

**Title:** Consolidate dual Video Pack implementations (Upstash + Filesystem)

**Description:**
EventRelay contains two separate Video Pack storage systems:

1. **Web Frontend Path (Canonical):** `apps/web/src/lib/video-pack-store.ts`
   - Storage: Upstash REST only in production
   - Behavior: Throws error if REST credentials missing
   - State machine: `processing → ready → error`

2. **Backend Path (Parallel):** `src/youtube_extension/backend/api/v1/router.py:2272-2313`
   - Storage: Filesystem-based (`storage/video_packs/<video_id>/pack.json`)
   - Behavior: Silent fallback, no error if Upstash unavailable
   - Exposed via backend v1 `/video/pack` route
   - **NOT DOCUMENTED in README**

**Impact:** Data consistency risk, operational complexity, unclear truth source

**Files to Review:**
- `apps/web/src/lib/video-pack-store.ts`
- `src/youtube_extension/backend/api/v1/router.py:2272-2313`
- `src/youtube_extension/videopack/store.py`
- `README.md:18-32`

**Required Actions:**
1. Declare single pack store truth (recommend: Upstash REST for all)
2. Retire or explicitly gate filesystem path
3. Update README to document persistence strategy
4. Add migration/deprecation notice if retiring backend path

**Acceptance Criteria:**
- [ ] Only one Video Pack implementation is active in production
- [ ] Both web and backend routes use same persistence layer
- [ ] README explicitly documents pack persistence strategy
- [ ] Tests verify no state divergence between paths

**Labels:** `🔴 critical`, `architecture`, `persistence`, `backend`, `frontend`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 1

---

## [AUDIT-002] G.A.T.E. Gate Lacks Provider Ownership Verification (🔴 CRITICAL)

**Title:** Add provider ownership verification to G.A.T.E. deployment gate

**Description:**
The G.A.T.E. gate currently only validates basic URL structure and HTTPS hostname. Per `README.md:32-33`:
> "The existing Studio gate checks a returned HTTPS URL with a hostname before showing a live result. It does **not** independently probe the deployment or establish provider-backed ownership."

This creates a security gap where a user could claim false deployment evidence without verification.

**Files to Review:**
- `apps/web/src/lib/gate-transition.ts`
- `apps/web/src/lib/__tests__/gate-transition.test.ts`
- `README.md:32-33` (documents the limitation)

**Required Actions:**
1. Implement provider verification (probe endpoint, check HTTP status, validate provider API)
2. Add clear error messaging if deployment verification fails
3. Document verification strategy in architecture
4. Add test coverage for failed verification scenarios

**Acceptance Criteria:**
- [ ] G.A.T.E. gate attempts to verify deployment via HTTP probe or provider API
- [ ] Clear error UI when verification fails
- [ ] Documentation updated with verification method
- [ ] Tests cover both success and failure cases
- [ ] README updated to reflect new verification capability

**Labels:** `🔴 critical`, `security`, `deployment`, `gate`, `frontend`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 2

---

## [AUDIT-003] Broken Repository Reconciliation Workflow (🔴 CRITICAL)

**Title:** Fix GitHub Actions repository-reconciliation workflow GraphQL errors

**Description:**
The `.github/workflows/repository-reconciliation.yml` workflow repeatedly fails with:
```
GraphqlResponseError ... Resource not accessible by integration
```

Root cause: Workflow requests `branchProtectionRule` GraphQL field but token lacks required scope.

Additionally, `.github/workflows/verification.yml` appears to be legacy (last 7 runs all failed, no clear owner).

**Files to Review:**
- `.github/workflows/repository-reconciliation.yml` (GraphQL scope error)
- `.github/workflows/verification.yml` (legacy, all failures)
- Related issues: #2067, #2068, #2069

**Required Actions:**
1. Fix token scope in reconciliation workflow (or remove branchProtectionRule field)
2. Verify all other workflows have adequate token scopes
3. Triage verification.yml (retire, fix, or document owner)
4. Ensure all enabled workflows have green recent runs

**Acceptance Criteria:**
- [ ] `repository-reconciliation.yml` runs successfully (0 GraphQL errors)
- [ ] All token scopes documented in workflow comments
- [ ] `verification.yml` either fixed or formally retired
- [ ] All enabled workflows green in last 5 runs

**Labels:** `🔴 critical`, `ci/cd`, `github-actions`, `automation`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 3, Issues #2067, #2068, #2069

---

## [AUDIT-004] Multiple Agent Orchestration Layers (🟠 HIGH)

**Title:** Unify agent orchestration (clarify active path, consolidate)

**Description:**
The codebase contains two separate agent orchestration implementations, making routing and maintenance unclear:

**Layer 1: Backend Orchestrator (Likely Production)**
- Location: `src/youtube_extension/services/agents/adapters/agent_orchestrator.py`
- Features: Task dispatch, parallel execution, shared SQL state, A2A session logging
- Used by: `/agents/dispatch`, `/agents/status` routes

**Layer 2: Agent Network (Experimental/Internal)**
- Location: `src/agents/mcp_agent_network.py`, `pipeline_orchestrator.py`
- Agents: `video-ingest`, `architect`, `code-gen`, `build-validator`, `deployer`, `knowledge-capture`
- Each mapped to MCP endpoints

**Impact:** Unclear which orchestrator is active; maintenance burden; feature discoverability

**Files to Review:**
- `src/youtube_extension/services/agents/adapters/agent_orchestrator.py`
- `src/agents/mcp_agent_network.py`
- `src/agents/pipeline_orchestrator.py`
- `src/youtube_extension/services/shared_sql_state.py` (state store)

**Required Actions:**
1. Document active agent orchestration path
2. Decide: consolidate into one, or clearly separate production/experimental
3. If consolidating: merge logic, retire redundant code
4. Update architecture docs with agent routing diagram

**Acceptance Criteria:**
- [ ] One primary agent orchestrator clearly documented
- [ ] All agent routing flows through documented path
- [ ] Redundant orchestration code removed or explicitly marked experimental
- [ ] Architecture diagram shows agent dispatch flow

**Labels:** `🟠 high`, `architecture`, `agents`, `backend`, `mcp`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 4

---

## [AUDIT-005] 14 Duplicate Public API Route Pairs (🟠 HIGH)

**Title:** Consolidate duplicate API routes (/api vs /api/v1)

**Description:**
The codebase contains 14 pairs of duplicate routes:
- `/api/video/pack` vs `/api/v1/video/pack`
- `/api/video/sandbox` vs `/api/v1/video/sandbox`
- 12 additional pairs identified

**Impact:** Maintenance burden (bug fixes happen twice); data divergence if routes call different backends

**Files to Review:**
- `apps/web/src/app/api/video/pack/route.ts`
- `apps/web/src/app/api/v1/video/pack/route.ts`
- `apps/web/src/app/api/video/sandbox/route.ts`
- `apps/web/src/app/api/v1/video/sandbox/route.ts`
- (and 10 additional pairs)

**Required Actions:**
1. Audit why each pair exists (compatibility, gradual migration?)
2. Decide on consolidation strategy (merge, deprecate, redirect)
3. If keeping both: ensure shared handler logic
4. Update API versioning strategy docs

**Acceptance Criteria:**
- [ ] Consolidation strategy documented (all pairs addressed)
- [ ] No byte-identical route twins without explanation
- [ ] All deprecated routes have clear deprecation notices
- [ ] Tests cover route consolidation/redirects

**Labels:** `🟠 high`, `api`, `refactoring`, `frontend`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 5

---

## [AUDIT-006] 800+ Bare Exception Handlers in src/ (🟠 HIGH)

**Title:** Reduce bare `except Exception` patterns; add structured error handling

**Description:**
Repository-wide search found ~800 `except Exception` / `except:` matches in `src/`, concentrated in:
- `src/youtube_extension/backend/services/*`
- `src/youtube_extension/backend/api/*`
- `src/agents/*`

**Impact:** Failure opacity, difficult debugging, hidden errors

**Files to Review:**
- `src/youtube_extension/backend/services/` (all files)
- `src/youtube_extension/backend/api/` (all files)
- `src/agents/` (all files)

**Required Actions:**
1. Audit critical paths (agents, routes, services) for bare exceptions
2. Implement structured logging with failure reasons
3. Add fail-closed patterns where appropriate (don't silent-fail on auth/security)
4. Define exception handling standards doc

**Acceptance Criteria:**
- [ ] All critical paths (auth, deployment, agents) use specific exceptions
- [ ] Bare `except:` eliminated from critical paths
- [ ] Failure reasons logged with context
- [ ] Exception handling standards documented

**Labels:** `🟠 high`, `code-quality`, `logging`, `backend`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 6

---

## [AUDIT-007] SQL Models Exceed Migration Coverage (🟠 HIGH)

**Title:** Reconcile SQL models with migration files (schema drift)

**Description:**
Rich SQL model surface (120+ lines of mixins in `base.py`) but only 3 migration files visible:
- `migrations/versions/001_...`
- `migrations/versions/002_...`
- `migrations/versions/003_...`

**Impact:** Schema drift risk, unclear state ownership, silent migrations

**Files to Review:**
- `src/youtube_extension/backend/models/base.py` (model mixins)
- `src/youtube_extension/backend/migrations/versions/` (only 3 files?)
- `src/youtube_extension/backend/config/database.py` (RLS config unclear)
- All model files under `src/youtube_extension/backend/models/`

**Required Actions:**
1. Inventory all active SQL models
2. Map models to migration coverage
3. Identify unmigrated models (schema drift risk)
4. Create missing migrations or deprecate models
5. Document RLS and tenanting strategy

**Acceptance Criteria:**
- [ ] All active models have migration history
- [ ] No schema drift (model ≠ database)
- [ ] RLS and tenanting strategy documented
- [ ] Migration file naming consistent

**Labels:** `🟠 high`, `database`, `backend`, `migrations`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 7

---

## [AUDIT-008] Three Conflicting "Current" Architecture Narratives (🟡 MEDIUM)

**Title:** Consolidate architecture documentation into single "current" truth

**Description:**
Three competing documentation sources describe different "current" architecture:

1. **README.md** → Current flow: URL → Studio → pack → evidence → optional deploy
2. **docs/REPO_MAP.md** → Current entry points and code locations
3. **docs/video_to_gtm_architecture.md** → Historical FORGE/PRISM/ATLAS multi-agent pipeline (marked "non-current" but not clearly archived)
4. **AGENTS.md** → Locked product rules (restricts visibility)

**Impact:** Onboarding friction, maintenance confusion, unclear "source of truth"

**Files to Review:**
- `README.md`
- `docs/REPO_MAP.md`
- `docs/video_to_gtm_architecture.md`
- `AGENTS.md`
- `docs/NEXT-PHASE.md`
- `docs/MASTER_ROADMAP.md`

**Required Actions:**
1. Consolidate into single "current" narrative (recommend: README + REPO_MAP)
2. Move historical docs to `docs/history/` or clearly mark deprecated
3. Create single architecture diagram (components + flow)
4. Document product evolution (what changed and why)

**Acceptance Criteria:**
- [ ] Single source of truth for "current" architecture
- [ ] Historical docs clearly labeled and archived
- [ ] Architecture diagram up-to-date
- [ ] README, REPO_MAP, and NEXT-PHASE aligned

**Labels:** `🟡 medium`, `documentation`, `architecture`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 8

---

## [AUDIT-009] MCP Registry vs. Backend Orchestrator Routing (🟡 MEDIUM)

**Title:** Clarify MCP registry + orchestrator routing behavior

**Description:**
MCP integration has two overlapping layers:

1. **MCP Registry** (`src/youtube_extension/services/mcp/registry.py`)
   - Server registration, capability indexing, health monitoring
   - Best-server routing by capability

2. **MCP Orchestrator** (`src/youtube_extension/services/mcp/orchestrator.py`)
   - Task submission, JSON-RPC 2.0 routing via HTTP

3. **Legacy MCP Context Manager** (`src/youtube_extension/core/mcp/context_manager.py`)
   - Older/foundation layer for structured context

**Impact:** Call routing unpredictable, feature discoverability unclear

**Files to Review:**
- `src/youtube_extension/services/mcp/registry.py`
- `src/youtube_extension/services/mcp/orchestrator.py`
- `src/youtube_extension/core/mcp/context_manager.py`
- `src/youtube_extension/backend/api/v1/router.py` (MCP dispatch endpoints)

**Required Actions:**
1. Document MCP routing hierarchy
2. Decide on active MCP layer (registry + orchestrator vs. legacy)
3. Unify or clearly separate production/experimental paths
4. Add MCP routing tests

**Acceptance Criteria:**
- [ ] MCP routing documented (which servers, how selected)
- [ ] One primary MCP dispatch path
- [ ] Legacy MCP layer status clear (active/deprecated)
- [ ] MCP routing tests added

**Labels:** `🟡 medium`, `mcp`, `architecture`, `backend`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 9

---

## [AUDIT-010] 45 Open Issues (Scope/Priority Unclear) (🟡 MEDIUM)

**Title:** Triage backlog: clarify priority, scope, and ownership

**Description:**
Repository has 45 open issues with unclear scope and priority distribution:
- Some labeled `needs-triage`, some `triaged`
- Multiple issues by automation agents
- Mix of feature work, bug fixes, and CI improvements
- No clear backlog grooming process

**Impact:** Planning uncertainty, unclear priorities, maintenance burden

**Files to Review:**
- All open issues in repository
- Issue labels and milestones

**Required Actions:**
1. Create priority matrix (critical/high/medium/low)
2. Triage each issue: priority, owner, scope
3. Close/defer non-essential items
4. Create or update issue labeling standards
5. Document backlog grooming process

**Acceptance Criteria:**
- [ ] All open issues have priority label
- [ ] Critical items have estimated timeline
- [ ] Backlog grooming process documented
- [ ] Closed/deferred issues archived

**Labels:** `🟡 medium`, `process`, `backlog`, `triage`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 10

---

## [AUDIT-011] yt-dlp Binary Dependency Without Fallback (🟡 MEDIUM)

**Title:** Add fallback for yt-dlp binary; circuit breaker pattern

**Description:**
yt-dlp is the final fallback in YouTube metadata/transcript acquisition. If binary is unavailable or broken, the entire transcript path fails.

**Current fallback chain:**
1. YouTube Data API
2. PyTube
3. YouTube Search
4. **yt-dlp** (final, external binary)
5. (no fallback)

**Impact:** Transcript acquisition failure mode uncovered, external binary supply-chain risk

**Files to Review:**
- `src/youtube_extension/backend/services/youtube/adapters/robust.py`
- `src/youtube_extension/services/ai/speech_to_text_service.py`
- `pyproject.toml:79-85` (pinned: 2025.05.22)
- `src/youtube_extension/main.py:225-257` (health checks)

**Required Actions:**
1. Add circuit breaker pattern for yt-dlp failures
2. Implement fallback: PyTube-only mode if yt-dlp unavailable
3. Document failure modes and recovery
4. Add health checks for yt-dlp binary availability

**Acceptance Criteria:**
- [ ] yt-dlp failures don't cascade to entire workflow
- [ ] Circuit breaker logs yt-dlp unavailability
- [ ] Fallback mode documented
- [ ] Health checks include yt-dlp binary status

**Labels:** `🟡 medium`, `backend`, `reliability`, `youtube`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 11

---

## [AUDIT-012] Workflow DevKit Override Chain Not Documented (🟡 MEDIUM)

**Title:** Document Workflow DevKit undici override chain

**Description:**
`package.json` contains extensive overrides for Workflow DevKit compatibility:
```json
"@workflow/world-local": { "undici": "^7.29.0" },
"@workflow/world-vercel": { "undici": "^7.29.0" }
```

This is not documented anywhere, causing confusion during:
- Dependency upgrades
- Debugging fetch issues
- Onboarding new developers

**Impact:** Dependency resolution confusion, deployment debugging friction, upgrade uncertainty

**Files to Review:**
- `package.json:22-51` (overrides block)
- `apps/web/next.config.js:10-17` (withWorkflow)
- Architecture docs

**Required Actions:**
1. Document why overrides are needed
2. Add comments to package.json explaining each override
3. Create upgrade guide for Workflow DevKit
4. Document fetch/undici version constraints

**Acceptance Criteria:**
- [ ] Each override documented with reason
- [ ] Workflow DevKit integration guide created
- [ ] Upgrade path documented
- [ ] Comments added to package.json

**Labels:** `🟡 medium`, `documentation`, `dependencies`, `frontend`

**Related:** `.github/AUDIT_FINDINGS_SESSION.md` Section 12

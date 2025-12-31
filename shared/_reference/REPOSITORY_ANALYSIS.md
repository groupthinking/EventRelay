# Repository Analysis & Investigation Report

**Date:** December 20, 2024  
**Analyst:** Kombai AI Assistant  
**Status:** Phase 1 - Discovery Complete

---

## Executive Summary

**Repository Size:** 33,342 directories (before cleanup)  
**Current State:** Post-cleanup, well-organized archive structure  
**Critical Finding:** 203MB genkit-mcp bloat containing full Google Genkit repository (24,409 files)  
**Recommendation:** Immediate consolidation and cleanup required

---

## Project Inventory

### ✅ Active Production Projects

#### 1. **EventRelay** (`./projects/EventRelay/`)

**Purpose:** AI-powered video-to-action platform  
**Type:** Monorepo (Turbo)  
**Status:** ✅ Active Production  
**Last Activity:** Recent (GitHub synced)

**Tech Stack:**

- **Backend:** Python 3.9+, FastAPI, SQLAlchemy, Pydantic
- **Frontend:** React 18.2.0, MUI v7, Emotion, Tailwind v3, Vite 5
- **Database:** SQLite/Postgres (SQLAlchemy) + Prisma (TypeScript packages)
- **AI/ML:** Transformers, Torch, Google Gemini, OpenAI
- **Monorepo:** Turbo, npm workspaces

**Architecture:**

```
EventRelay/
├── backend/              # Python FastAPI
│   ├── firebase/         # Firebase integration
│   └── services/         # API services
├── frontend/             # React 18 + MUI
├── packages/             # 14 shared packages
│   ├── @repo/logger
│   ├── @repo/database (Prisma)
│   ├── @repo/ai-gateway
│   ├── @repo/mcp-connectors
│   └── [10 more packages]
├── apps/web/             # Main web app
├── supabase/             # 3 Supabase apps
├── deployment/           # Deployment configs
└── tools/                # Development tools
```

**Critical Issues:**

- ⚠️ TypeScript 4.9.5 (needs upgrade to 5.x)
- ⚠️ React version inconsistency (18.x and 19.x mixed)
- ⚠️ Three styling systems (MUI + Emotion + Tailwind)
- ⚠️ Two ORMs (SQLAlchemy + Prisma)
- ✅ Migrated to Vite 5

**Size:** Large monorepo with extensive dependencies

---

#### 2. **netmesh-production** (`./projects/netmesh-production/`)

**Purpose:** Cloudflare VibeSDK - AI vibe coding platform  
**Type:** Standalone application  
**Status:** ✅ Active Production  
**Last Activity:** Recent

**Tech Stack:**

- **Frontend:** React 19.1.1, Vite 6, Tailwind v4, shadcn
- **Backend:** Cloudflare Workers, Hono 4.9.7
- **Database:** D1 (SQLite)
- **ORM:** Drizzle 0.44.5
- **State:** Zustand
- **Charts:** Recharts 3.2.1
- **Animation:** Framer Motion 12.23.12
- **Icons:** Lucide React 0.541.0

**Architecture:**

```
netmesh-production/
├── src/                  # React 19 frontend
├── worker/               # Cloudflare Worker (Hono)
├── container/            # Sandbox system
├── customer-worker-1/    # Customer worker instance
└── scripts/              # Deployment scripts
```

**Status:** ✅ **Well-configured, modern stack** - No major issues  
**Size:** Moderate, well-optimized

---

#### 3. **MCP Ecosystem** (`./mcp-servers/`)

**Purpose:** Model Context Protocol server ecosystem  
**Type:** Distributed MCP servers  
**Status:** ✅ Active Infrastructure  
**Last Activity:** Recent

**Architecture:**

```
mcp-servers/
├── Coordination Layer
│   ├── shared-state/           # SQLite + WebSocket (Port 8005)
│   ├── ai_ops_skill_mesh_kit/  # AI operations toolkit
│   ├── ECOSYSTEM_SUMMARY.md    # Documentation
│   └── SKILL.md                # MCP setup guide
├── Active Servers (7 configured)
│   ├── github/                 # Express v5
│   ├── grok-server/
│   ├── perplexity-mcp/
│   ├── puppeteer-server/
│   ├── fetch-mcp/
│   ├── metacognition-tools/
│   └── unified-analytics/
├── Specialized Servers (6 servers)
│   ├── server-knowledge-management/
│   ├── server-code-assistant/
│   ├── server-creative-studio/
│   ├── server-communication-hub/
│   ├── server-data-analysis/
│   └── server-workflow-automation/
└── External Dependencies
    └── genkit-wrapper/         # ✅ Minimal wrapper (~100 files)
```

**Tech Stack:**

- **Languages:** TypeScript, Python
- **Frameworks:** Express v4/v5, FastAPI
- **Protocol:** MCP SDK (@modelcontextprotocol/sdk)
- **Coordination:** WebSocket, SQLite

**Critical Issues:**

- ✅ **genkit-mcp bloat resolved** (Full repo archived)
- ⚠️ Express version inconsistency (v4 and v5 mixed)
- ⚠️ No standardized structure across servers

**Size:** Moderate (optimized)

---

### ⚠️ Projects Requiring Investigation

#### 4. **self-correcting-executor-PRODUCTION** (MOVED)

**Action:** Moved to `~/Desktop/self-correcting-executor-PRODUCTION`
**Reason:** Disconnected from active MCP configuration; safeguarded on Desktop for cleanup.

---

#### 5. **software-on-demand** (`./projects/software-on-demand/`)

**Purpose:** Schema validation for Software-On-Demand multi-agent runtime  
**Type:** Utility/Validation library  
**Status:** ✅ **Active Utility**

**Description:**

- JSON Schema definitions for orchestrator execution graphs
- Validation helpers (AJV + YAML parsing)
- Dashboard event streaming schemas
- QA review templates

**Tech Stack:**

- Node.js (ES modules)
- AJV (JSON Schema validation)
- YAML parsing

**Files:**

- `step_graph.schema.json` - Execution graph schema
- `trace_ui_event_schema.json` - Event streaming schema
- `gold_set_evaluation_template.yaml` - QA template
- `src/validators.mjs` - Validation logic

**Recommendation:** ✅ **Keep** - Active utility for EventRelay/workflow validation  
**Size:** Small, lightweight

---

#### 6. **agents-marketplace** (`./agents-marketplace/`)

**Purpose:** Legacy project scaffolding scripts for OpenAI Hub  
**Type:** Shell script collection  
**Status:** 🗄️ **Archive Candidate** - Investigation Complete (Dec 22)

**Contents:**

- Symlink to `~/.claude/agents/` (exists but unused by scripts)
- Shell scripts in `bin/`:
  - `hub-add.sh` - Adds projects to OpenAI_Hub structure
  - `hub-sync.sh`, `hub-health.sh` - Hub management
  - `new-project.sh` - Scaffolds Node/Python projects
  - `newagent`, `newnode` - Wrapper scripts
  - `codex-batch.sh` - Batch processing

**Investigation Results (Dec 22):**

- Scripts reference `$HOME/Dev/OpenAI_Hub` which **does not exist**
- No usage found in active projects (EventRelay, netmesh-production, mcp-servers)
- Scripts modify `.codex/config.toml` but no agents-marketplace references found
- Legacy infrastructure from previous development setup

**Recommendation:** 🗄️ **Archive** to `_archive/agents-marketplace`  
**Rationale:** No active usage, references non-existent directories, safe to archive  
**Risk:** Minimal - scripts not integrated with current projects

**Size:** Minimal (8 shell scripts, 1 symlink)

---

#### 7. **xai-grok-wrapper** (`./xai-grok-wrapper/`)

**Purpose:** Python wrapper for xAI Grok API  
**Type:** Utility library  
**Status:** ✅ **Well-documented**

**Description:**

- Full-featured Python client for xAI Grok API
- Code execution, remote MCP tools, agentic features
- Server-side and client-side tool support

**Tech Stack:** Python, httpx

**Recommendation:**

- Option A: Move to EventRelay as a package (`@repo/grok-client`)
- Option B: Keep standalone if used by multiple projects
- Option C: Archive if not actively used

**Size:** Minimal, single-file wrapper

---

#### 8. **Zero to Launch Bundle** (REMOVED)

**Status:** 🗑️ **Removed by User**
**Reason:** Manually deleted as per cleanup plan.

---

### ✅ Archived Projects

#### 9. **\_archive/** (Well-organized)

**Contents:**

- `binaries/` - cloudflared binary
- `falling-union-bced/` - Unknown Cloudflare Worker project
- `legacy_hub_artifacts/` - Old OpenAI Hub artifacts
- `netmesh-extension/` - Browser extension (duplicate)
- `solitary-bread-bbcc/` - Unknown Cloudflare Worker project
- `state-fabric-concept/` - Duplicate of mcp-servers/shared-state

**Status:** ✅ Properly archived

---

### 📚 Reference Materials

#### 10. **reference/** (`./reference/`)

**Contents:**

- `Vision-Agents/` - AI agent reference implementation
- `jsoncstyleguide.xml` - JSON style guide

**Status:** ✅ Properly organized  
**Recommendation:** Keep as reference materials

---

## Critical Findings

### ✅ Priority 1: genkit-mcp Bloat - RESOLVED (Dec 21)

**Problem:** (Original)

- **Size:** 203MB
- **Files:** 24,409 files
- **Content:** Full Google Genkit repository (not just wrapper)
- **Impact:** Massive disk usage, slow operations

**Resolution:** ✅ Complete (Dec 21, 2024)

- Extracted MCP plugin wrapper to `mcp-servers/genkit-wrapper/`
- Archived full repository to `_archive/genkit-mcp-full-repo/`
- **Space saved:** ~200MB
- **Files removed:** ~24,300

**Current State:**

- `mcp-servers/genkit-wrapper/` - Minimal MCP plugin (~100 files)
- `_archive/genkit-mcp-full-repo/` - Full repo preserved for reference
- All functionality maintained, no broken imports

---

### ✅ Priority 2: self-correcting-executor-PRODUCTION - RESOLVED (Dec 21)

**Problem:** (Original)

- Contains duplicate MCP servers (github, unified-analytics)
- Overlaps with `mcp-servers/` infrastructure
- Unclear relationship to EventRelay

**Resolution:** ✅ Complete (Dec 21, 2024)

- Moved to `~/Desktop/self-correcting-executor-PRODUCTION`
- Disconnected from active MCP configuration
- Safeguarded for potential future reference

**Rationale:**

- Not referenced in `claude_desktop_config.json`
- Duplicate of EventRelay MCP infrastructure
- Moved to Desktop rather than archived for safety

---

### ⚠️ Priority 3: agents-marketplace Legacy Code - RESOLVED (Dec 22)

**Problem:** (Original)

- Unknown purpose and usage
- Unclear if actively used by projects
- Symlink to `.claude/agents/` with unclear purpose

**Resolution:** ✅ Investigation Complete (Dec 22, 2024)

- Identified as legacy OpenAI Hub scaffolding scripts
- No active usage in current projects
- References non-existent `$HOME/Dev/OpenAI_Hub` directory
- **Recommendation:** Archive to `_archive/agents-marketplace`

**Impact:** Minimal - safe to archive

---

### ⚠️ Priority 4: EventRelay Technical Debt

**Issues:**

1. TypeScript 4.9.5 (outdated)
2. React version inconsistency (18.x vs 19.x)
3. Three styling systems (MUI + Emotion + Tailwind)
4. Two ORMs (SQLAlchemy + Prisma)
5. Using CRA instead of Vite

**Impact:** Developer experience, build times, maintenance complexity

**Recommendation:** Phased upgrade plan (see action items)

---

## Dependency Analysis

### MCP Server Dependencies

**Configured Servers (from ECOSYSTEM_SUMMARY.md):**

1. YouTube UVAI Processor (Primary)
2. Self-Correcting Executor
3. Universal MCP Swarm
4. Cloudflare MCP
5. Perplexity MCP
6. Context7

**Custom vs External:**

- **Custom:** github, grok-server, puppeteer-server, fetch-mcp
- **External:** perplexity-mcp (uvx)
- **Specialized:** 6 server-\* projects (knowledge, code-assistant, etc.)

**Express Version Distribution:**

- Express v5: github, puppeteer-server
- Express v4: Multiple genkit samples
- **Recommendation:** Standardize on Express v5

---

### Inter-Project Dependencies

```
EventRelay
├── Uses: mcp-servers (MCP connectors package)
├── Uses: software-on-demand (validation schemas)
└── May use: xai-grok-wrapper (if Grok integration exists)

netmesh-production
└── Independent (no dependencies on other projects)

mcp-servers
├── Provides services to: EventRelay, netmesh-production
└── Contains: genkit-mcp (bloat to remove)

self-correcting-executor-PRODUCTION
└── Relationship unclear (needs investigation)
```

---

## Recommended Actions

### Immediate (This Week)

#### 1. Investigate self-correcting-executor-PRODUCTION

```bash
# Compare with EventRelay MCP
diff -r ./projects/EventRelay/packages/mcp-connectors/ \
        ./self-correcting-executor-PRODUCTION/MCP/

# Check git history
git -C ./self-correcting-executor-PRODUCTION log --oneline -20

# Determine last activity
find ./self-correcting-executor-PRODUCTION -type f -name "*.py" -o -name "*.ts" \
  -exec stat -f "%Sm %N" -t "%Y-%m-%d" {} \; | sort -r | head -10
```

**Decision Matrix:**

- If last modified > 90 days ago → Archive
- If duplicate of EventRelay → Archive
- If active deployment env → Document and keep
- If development sandbox → Consolidate into mcp-servers

---

#### 2. Extract genkit-mcp Wrapper

```bash
# Create minimal wrapper
mkdir -p ./mcp-servers/genkit-wrapper
cp -r ./mcp-servers/genkit-mcp/repo/js/plugins/mcp/* \
      ./mcp-servers/genkit-wrapper/

# Archive full repo
mv ./mcp-servers/genkit-mcp ./_archive/genkit-mcp-full-repo

# Update package.json references
# Update any imports in other projects
```

**Expected Outcome:**

- Disk usage: -200MB
- Files: -24,300 files
- Functionality: Unchanged

---

#### 3. Archive Zero to Launch Bundle

```bash
# Move to archive
mv "./Zero to Launch Bundle" ./_archive/documentation/zero-to-launch-bundle
```

---

#### 4. Review agents-marketplace

```bash
# Check usage
grep -r "agents-marketplace" ./projects/ ./mcp-servers/

# If unused, consider consolidating
mv ./agents-marketplace/bin/* ./mcp-servers/ai_ops_skill_mesh_kit/bin/
# Then archive the directory
```

---

### Short-term (This Month)

#### 5. EventRelay TypeScript Upgrade

```bash
cd ./projects/EventRelay/frontend
npm install typescript@^5.0.0 --save-dev
npm install @types/react@^18.0.0 @types/react-dom@^18.0.0 --save-dev

# Update tsconfig.json
# Run type checking
npx tsc --noEmit

# Fix any breaking changes
# Test thoroughly
```

---

#### 6. Standardize React Versions

**Strategy:** Standardize on React 18.x (safer than 19.x migration)

```bash
# Update all React 19 apps to 18.x
cd ./projects/EventRelay/supabase/mcp-supabase-frontend
npm install react@^18.2.0 react-dom@^18.2.0

# Repeat for other apps with React 19
```

---

#### 7. Consolidate MCP Servers

**Create monorepo structure:**

```bash
mkdir -p ./mcp-servers/servers-monorepo/{packages,apps}

# Move custom servers
mv ./mcp-servers/github ./mcp-servers/servers-monorepo/packages/
mv ./mcp-servers/grok-server ./mcp-servers/servers-monorepo/packages/
# ... etc

# Create root package.json with workspaces
# Standardize on Express v5
```

---

### Long-term (Next Quarter)

#### 8. EventRelay Vite Migration (COMPLETED)

- ✅ Migrated from CRA to Vite
- ✅ Configured build pipeline
- ✅ Verified with React 18

#### 9. Simplify Styling Strategy

- Choose: MUI + Emotion OR Tailwind (not both)
- Create migration plan
- Update component library

#### 10. ORM Consolidation

- Decide: SQLAlchemy (Python) + Drizzle (TypeScript)
- OR: SQLAlchemy (Python) + Prisma (TypeScript)
- Migrate to chosen stack

---

## Metrics & Goals

### Current State

- **Directories:** 33,342 (before cleanup)
- **Disk Usage:** ~500MB+ (estimated)
- **genkit-mcp:** 203MB, 24,409 files
- **Projects:** 10 total (3 active, 4 investigation, 1 archived, 2 reference)

### Target State (30 days)

- **Directories:** < 10,000 (-70%)
- **Disk Usage:** < 300MB (-40%)
- **genkit-mcp:** Removed/archived
- **Projects:** Categorized and documented (100%)
- **Unknown projects:** 0 (all investigated)

### Target State (90 days)

- **Directories:** < 5,000 (-85%)
- **Disk Usage:** < 200MB (-60%)
- **Tech debt:** TypeScript 5.x, React standardized
- **MCP servers:** Consolidated monorepo
- **Documentation:** Complete for all projects

---

## Next Steps

1. ✅ **Complete** - Initial investigation and documentation (Dec 20)
2. ✅ **Complete** - genkit-mcp extraction (Dec 21)
3. ✅ **Complete** - self-correcting-executor relocation (Dec 21)
4. ✅ **Complete** - Zero to Launch Bundle removal (Dec 21)
5. ✅ **Complete** - agents-marketplace investigation (Dec 22)
6. ⏳ **Pending** - Archive agents-marketplace (awaiting approval)
7. ✅ **Complete** - EventRelay TypeScript upgrade (Frontend verified)
8. ✅ **Complete** - EventRelay Vite Migration (Phase 3)
9. ⏳ **Pending** - React standardization (Phase 3)
10. ⏳ **Pending** - MCP server consolidation (Phase 3)

---

## Appendix

### Project Size Estimates

```
EventRelay:                 ~150MB (with node_modules)
netmesh-production:         ~100MB (with node_modules)
mcp-servers (excl genkit):  ~50MB
genkit-mcp:                 203MB ⚠️
self-correcting-executor:   ~30MB
Others:                     ~20MB
_archive:                   ~50MB
```

### File Count by Project

```
genkit-mcp:                 24,409 files ⚠️
EventRelay:                 ~5,000 files
netmesh-production:         ~2,000 files
mcp-servers (excl genkit):  ~1,000 files
Others:                     ~500 files
```

---

### ✅ Priority 5: Development Environment Standardization - RESOLVED (Dec 31)

**Problem:**

- Developer workflows (run API, deploy) relied on global user configuration or disparate scripts.
- No unified task interface for developers.

**Resolution:** ✅ Complete (Dec 31, 2024)

- Created `.vscode/tasks.json` in `EventRelay`.
- Standardized 5 key tasks: `Run API (Dev)`, `Deploy Staging`, `Run Worker`, `Verify Grok`, `Run Tests`.
- Documented in `PROJECT_DECISIONS.md`.

**State:**

- `EventRelay/.vscode/tasks.json` is now the source of truth for build commands.

---

**Report Status:** Phase 2 Complete - Cleanup & Extraction
**Next Phase:** Phase 3 - Consolidation (Awaiting Approval)
**Last Updated:** December 31, 2024

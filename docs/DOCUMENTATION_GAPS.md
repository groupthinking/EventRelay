# EventRelay Documentation Gaps & Areas Needing Input

> Issues identified during codebase analysis that need clarification or additional documentation.

---

## Summary

| Priority | Category | Count |
|----------|----------|-------|
| 🔴 Critical | Needs immediate input | 4 |
| 🟠 High | Should be addressed soon | 6 |
| 🟡 Medium | Nice to have | 5 |

---

## 🔴 Critical Gaps

### 1. Frontend-Backend Integration is Incomplete

**Location:** `apps/web/`

**Issue:** The Next.js frontend has mock data and placeholder components. The actual API integration appears incomplete:
- Dashboard (`apps/web/src/app/dashboard/page.tsx`) uses mock data
- No `apps/web/src/services/api.ts` file for API client
- Missing type definitions matching backend Pydantic models

**Questions for You:**
- Is the frontend meant to be functional or is it a placeholder?
- Should I create the API client with typed methods?
- Are there mockups/designs for the dashboard UI?

**What's Needed:**
- [ ] `apps/web/src/services/api.ts` - Typed API client
- [ ] `apps/web/src/types/index.ts` - TypeScript types matching backend
- [ ] WebSocket client for real-time job updates
- [ ] React components: `VideoInput`, `EventList`, `AgentStatus`, `ResultsPanel`

---

### 2. MCP Protocol Usage Not Documented

**Location:** `src/mcp/`, `mcp-servers/`

**Issue:** MCP (Model Context Protocol) is core to the agent system, but there's no guide explaining:
- How to define MCP tools
- How to set up an MCP server
- How agents communicate via MCP
- Configuration required in `.cursor/mcp.json` or `.vscode/mcp.json`

**Questions for You:**
- Is MCP based on the Anthropic spec or a custom implementation?
- Which MCP servers are required vs. optional?
- Should developers be building new MCP servers?

**What's Needed:**
- [ ] `docs/MCP_GUIDE.md` - Complete MCP usage guide
- [ ] Example MCP tool definition
- [ ] MCP server setup walkthrough

---

### 3. Agent Development Missing Step-by-Step Guide

**Location:** `src/youtube_extension/services/agents/`

**Issue:** `AGENTS.md` exists but lacks:
- How to create a new agent from scratch
- Agent lifecycle details (initialize → analyze → plan → execute → report)
- How agents are selected for events
- How to test agents in isolation

**Questions for You:**
- What's the expected agent approval workflow (automated vs. human-in-loop)?
- How should agent errors be handled?
- Can agents call other agents?

**What's Needed:**
- [ ] Step-by-step "Create Your First Agent" tutorial
- [ ] Agent testing patterns
- [ ] Agent selection/matching documentation

---

### 4. Environment Variables Unclear on Optional vs. Required

**Location:** `.env.example`

**Issue:** The env file has many variables but it's unclear:
- Which are truly required vs. optional
- What fails if certain variables are missing
- Minimum viable configuration for each use case

**Questions for You:**
- What's the minimum config for just transcript extraction?
- What's required for the full revenue pipeline?
- Which features degrade gracefully vs. fail hard?

**What's Needed:**
- [ ] Tiered configuration guide (minimal, recommended, full)
- [ ] Failure behavior documentation
- [ ] Feature flag mapping to env vars

---

## 🟠 High Priority Gaps

### 5. Service Container Pattern Not Explained

**Location:** `src/youtube_extension/backend/containers/service_container.py`

**Issue:** The dependency injection pattern is used throughout but not documented:
- How services are registered
- Singleton vs. transient behavior
- How to add new services

**What's Needed:**
- [ ] Service registration guide
- [ ] Dependency injection examples

---

### 6. Video Processing Fallback Chain Undocumented

**Location:** `src/youtube_extension/backend/services/video_processing_service.py`

**Issue:** There's a fallback chain for transcript extraction:
1. `youtube-transcript-api` (fast)
2. `Speech-to-Text v2 + yt-dlp` (slow but reliable)

But it's unclear:
- When does fallback trigger?
- What errors cause fallback?
- How long does each method take?

**What's Needed:**
- [ ] Fallback flow diagram
- [ ] Error handling documentation
- [ ] Performance expectations

---

### 7. Database Schema Not Documented

**Location:** `infrastructure/database/`, `src/youtube_extension/backend/migrations/`

**Issue:** Alembic migrations exist but no schema documentation:
- What tables exist?
- Entity relationships?
- Migration strategy for production?

**What's Needed:**
- [ ] ERD diagram
- [ ] Table descriptions
- [ ] Migration guide

---

### 8. Prescient Twin Purpose Unclear

**Location:** `prescient-twin/`

**Issue:** This subsystem is mentioned but its purpose and usage aren't clear:
- When should developers use it?
- Is it for development only or production?
- How does "dogfooding" work?

**Questions for You:**
- Should contributors be aware of Prescient Twin?
- Is it stable enough to document?

**What's Needed:**
- [ ] Prescient Twin overview
- [ ] Use cases and examples

---

### 9. Test Fixtures Missing

**Location:** `tests/fixtures/`

**Issue:** The fixtures directory exists but:
- What test data should be there?
- How to generate fixtures?
- Are fixtures checked into git?

**What's Needed:**
- [ ] Sample video data for testing
- [ ] Mock API responses
- [ ] Fixture generation scripts

---

### 10. CI/CD Secrets Not Listed

**Location:** `.github/workflows/`

**Issue:** Workflows reference secrets like `QLTY_COVERAGE_TOKEN` but there's no list of:
- Required GitHub secrets
- How to obtain each secret
- Which are optional

**What's Needed:**
- [ ] GitHub secrets checklist
- [ ] Setup guide for CI/CD

---

## 🟡 Medium Priority Gaps

### 11. Performance Tuning Not Documented

**Issue:** No guidance on:
- Caching strategy
- Query optimization
- Rate limiting configuration
- Scaling recommendations

---

### 12. Logging Standards Missing

**Issue:** Code uses `structlog` and `print` inconsistently:
- When to use structured logging?
- Log levels guide?
- Log aggregation setup?

---

### 13. Error Handling Patterns Unclear

**Issue:** Error responses exist but no standard for:
- Custom exception classes
- Error code catalog
- Client-side error handling

---

### 14. WebSocket API Incomplete

**Location:** `src/youtube_extension/backend/services/websocket_service.py`

**Issue:** WebSocket support exists but:
- What events are broadcast?
- Message format?
- Reconnection handling?

---

### 15. Docker Compose Variants Confusing

**Issue:** Multiple docker-compose files exist:
- `docker-compose.full.yml`
- `docker-compose.youtube-packager.yml`
- `supabase/docker-compose.yml`

No guide on which to use when.

---

## Questions for You

To complete the documentation, I need your input on:

### Architecture Decisions

1. **Frontend Status:** Is `apps/web` meant to be functional or just a demo? Should I document it as-is or note it's WIP?

2. **MCP Implementation:** Is this based on Anthropic's MCP spec or custom? Link to reference?

3. **Agent Approval:** Do agents run autonomously or require human approval? Is `GUIDED` mode used?

### Configuration

4. **Minimum Setup:** What's the absolute minimum to run a basic demo? Just `GEMINI_API_KEY`?

5. **Production Config:** What additional setup is required for production deployment?

6. **Feature Flags:** Is there a feature flag system? How do flags map to functionality?

### Development

7. **Test Coverage Goal:** What's the target coverage percentage?

8. **Breaking Changes:** How should contributors handle breaking API changes?

9. **Deprecation Policy:** How long before deprecated endpoints are removed?

### Operations

10. **Monitoring:** Is there a preferred monitoring stack (Datadog, Prometheus, etc.)?

11. **Incident Response:** Who should be contacted for production issues?

12. **SLA Expectations:** What uptime/latency targets exist?

---

## Recommended Documentation Additions

Based on this analysis, I recommend creating:

| Document | Purpose | Priority |
|----------|---------|----------|
| `docs/MCP_GUIDE.md` | MCP protocol usage | 🔴 Critical |
| `docs/AGENT_DEVELOPMENT.md` | Creating new agents | 🔴 Critical |
| `docs/FRONTEND_INTEGRATION.md` | Connecting frontend to backend | 🔴 Critical |
| `docs/CONFIGURATION_TIERS.md` | Env var tiers (minimal/recommended/full) | 🔴 Critical |
| `docs/DATABASE_SCHEMA.md` | ERD and table docs | 🟠 High |
| `docs/SERVICE_CONTAINER.md` | Dependency injection guide | 🟠 High |
| `docs/FALLBACK_STRATEGIES.md` | Video processing fallbacks | 🟠 High |
| `docs/TESTING_GUIDE.md` | Test patterns and fixtures | 🟠 High |
| `docs/CICD_SETUP.md` | GitHub Actions secrets and setup | 🟠 High |
| `docs/PERFORMANCE_TUNING.md` | Caching and optimization | 🟡 Medium |

---

## How to Use This Document

1. **Review the critical gaps** and provide clarification
2. **Answer the questions** in the "Questions for You" section
3. **Prioritize** which documentation to create first
4. **Assign ownership** for each documentation task

Once you provide input, I can generate the missing documentation.

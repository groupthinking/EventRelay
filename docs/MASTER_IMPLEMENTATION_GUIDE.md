# EventRelay Backend-Frontend Integration: Master Implementation Guide

## 📋 Executive Summary

This guide provides a complete roadmap to achieve 100% backend-frontend connectivity for EventRelay, following framework first principles and breaking down every task into actionable subtasks.

**Goal:** Connect FastAPI backend (port 8000) with Next.js frontend (port 3000) to enable the complete EventRelay workflow: YouTube URL → Transcript → Events → Agent Execution → Results.

**Current State:**
- ✅ Backend: Production-ready FastAPI with standardized API v1 endpoints
- ✅ Frontend: Next.js 16 with full workflow UI and Zustand state management
- ✅ Integration: Complete service layer connecting frontend ↔ backend

**Target State:**
- ✅ Complete API layer with standardized responses
- ✅ Frontend service layer for all backend calls
- ✅ Full UI implementation of EventRelay workflow
- ✅ State management for reactive updates
- ✅ Comprehensive testing (>80% coverage)
- ✅ Complete documentation

---

## 🎯 Framework First Principles Analysis

### 1. Current Architecture

#### Backend Architecture (FastAPI)
```
Location: src/youtube_extension/backend/main_v2.py
Entry Point: uvai.api.main:app

Structure:
├── FastAPI Application (Service-Oriented)
├── API Routes (versioned /api/v1/*)
├── MCP Bridge (/mcp)
├── Service Layer (video, events, agents)
├── Data Layer (SQLite/PostgreSQL)
└── Integration Layer (YouTube, Gemini, MCP)

Current Endpoints:
- GET  /docs                    # OpenAPI documentation
- GET  /health                  # Legacy health check
- POST /mcp                     # MCP bridge endpoint
- POST /api/chat                # Legacy chat endpoint
- POST /api/process-video-markdown  # Legacy video processing

Issues:
- ❌ Inconsistent response formats
- ❌ No standardized /api/v1/* endpoints
- ❌ Legacy endpoints mixed with new ones
- ❌ Incomplete API documentation
```

#### Frontend Architecture (Next.js)
```
Location: apps/web/
Entry Point: src/app/page.tsx

Structure:
├── Next.js App Router
├── API Routes (/api/*)
├── Pages (/dashboard, etc.)
├── Components (minimal)
└── Services (none)

Current Pages:
- /           # Landing page with links
- /dashboard  # Dashboard with mock data
- /api        # API info endpoint
- /api/dashboard  # Mock metrics endpoint

Issues:
- ❌ No backend API client
- ❌ No type definitions
- ❌ Using mock data only
- ❌ No video processing UI
- ❌ No state management
```

#### Integration Gap
```
Current:
Frontend → Next.js API Routes → Mock Data

Target:
Frontend → Service Layer → Backend API → Services → Data/AI

Missing:
1. Standardized backend API endpoints
2. Frontend API client
3. Type definitions (shared contract)
4. UI components for workflow
5. State management
6. Error handling
7. Real-time updates
```

### 2. EventRelay Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: YouTube URL Input (Frontend)                        │
│ Component: VideoInput.tsx                                   │
│ Action: User pastes YouTube link                            │
│ API Call: POST /api/v1/videos/process                       │
│ Response: { job_id, video_id, status: "pending" }          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Extract Context (Backend)                           │
│ Service: VideoProcessingService                             │
│ Actions:                                                     │
│   1. Download video metadata (YouTube API)                  │
│   2. Extract audio/transcript (Speech-to-Text)             │
│   3. Parse into structured text                             │
│   4. Store in cache/database                                │
│ API Poll: GET /api/v1/videos/{job_id}/status               │
│ Response: { status: "completed", transcript, metadata }     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Spawn Agents (Backend)                              │
│ Service: EventExtractionService → AgentOrchestrator        │
│ Actions:                                                     │
│   1. Extract events from transcript (AI analysis)           │
│   2. Classify event types (action, mention, topic, etc.)   │
│   3. Select appropriate agents for each event               │
│   4. Initialize agent execution contexts                    │
│ API Call: POST /api/v1/events/extract                       │
│ Response: { events: [...] }                                 │
│ API Call: POST /api/v1/agents/dispatch                      │
│ Response: { executions: [...], dispatch_id }                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Run Tasks (Backend + MCP)                           │
│ Service: AgentExecutionService                              │
│ Actions:                                                     │
│   - Code generation (CodeGeneratorAgent)                    │
│   - Content creation (ContentCreatorAgent)                  │
│   - Workflow triggers (WorkflowAgent)                       │
│   - Data analysis (AnalyzerAgent)                           │
│ Protocol: MCP (Model Context Protocol)                      │
│ API Poll: GET /api/v1/agents/{agent_id}/status             │
│ Response: { status: "running", progress: 75 }               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Publish Outputs (Frontend)                          │
│ Components:                                                  │
│   - TranscriptViewer.tsx (show transcript)                  │
│   - EventList.tsx (show extracted events)                   │
│   - AgentDashboard.tsx (show agent status)                  │
│   - ResultsViewer.tsx (show generated outputs)              │
│ API Call: GET /api/v1/agents/{agent_id}/results            │
│ Response: { outputs, artifacts, logs }                      │
│ Storage: Ground transcript in RAG store for learning        │
└─────────────────────────────────────────────────────────────┘
```

### 3. Integration Contract (Backend ↔ Frontend)

#### HTTP Communication
- **Protocol:** REST API over HTTP
- **Format:** JSON request/response
- **Authentication:** Optional (JWT tokens)
- **CORS:** Backend allows `http://localhost:3000`

#### Standard Response Format
```typescript
// Success Response
{
  "status": "success",
  "data": { /* actual payload */ },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456789"
}

// Error Response
{
  "status": "error",
  "error": "Error type",
  "detail": "Detailed message",
  "request_id": "req_123456789",
  "timestamp": "2024-01-01T12:00:00Z",
  "path": "/api/v1/videos/process"
}
```

#### Type Synchronization
- Backend: Pydantic models (Python)
- Frontend: TypeScript interfaces
- **Rule:** Frontend types must mirror backend models exactly

Example:
```python
# Backend (Pydantic)
class VideoProcessRequest(BaseModel):
    video_url: str
    options: Optional[dict] = {}
```

```typescript
// Frontend (TypeScript)
interface VideoProcessRequest {
  video_url: string;
  options?: Record<string, any>;
}
```

---

## 🚀 Implementation Phases

### Phase 1: Backend API Standardization (Priority: HIGH)
**Goal:** Create consistent, production-ready API endpoints

**Why First:** Frontend needs stable API contract before building UI

**Estimated Time:** 2-3 days

**Tasks:**
1. Define API response format (models.py)
2. Create video processing endpoints
3. Create event extraction endpoints
4. Create agent dispatch endpoints
5. Create health/status endpoints
6. Update CORS configuration
7. Implement error handling middleware

**Output:**
- ✅ All endpoints return standardized format
- ✅ Complete OpenAPI documentation at /docs
- ✅ CORS allows frontend origin
- ✅ Error responses are consistent

**See:** `docs/prompts/PHASE_1_BACKEND_API.md`

---

### Phase 2: Frontend Service Layer (Priority: HIGH)
**Goal:** Create abstraction for all backend communication

**Why Second:** Establishes type-safe communication layer

**Estimated Time:** 1-2 days

**Tasks:**
1. Create API client service (with retry logic)
2. Define TypeScript types matching backend
3. Implement video service
4. Implement event service
5. Implement agent service
6. Configure environment variables

**Output:**
- ✅ Type-safe API client
- ✅ All backend calls go through services
- ✅ Error handling utilities
- ✅ Environment configuration

**See:** `docs/prompts/PHASE_2_FRONTEND_SERVICES.md`

---

### Phase 3: Core Integration Features (Priority: HIGH)
**Goal:** Build UI components for EventRelay workflow

**Why Third:** Now we have stable backend + services to integrate

**Estimated Time:** 3-4 days

**Tasks:**
1. Video URL input component
2. Video status display component
3. Transcript viewer component
4. Event list component
5. Agent dashboard component
6. Results viewer component

**Output:**
- ✅ Complete UI for workflow
- ✅ Real backend integration
- ✅ No mock data
- ✅ User can process videos end-to-end

**See:** `docs/prompts/PHASE_3_4_5_6_COMPLETE.md` (Section: Phase 3)

---

### Phase 4: State Management (Priority: MEDIUM)
**Goal:** Centralized state for reactive updates

**Why Fourth:** UI works but state management improves UX

**Estimated Time:** 1 day

**Tasks:**
1. Setup Zustand store
2. Implement video processing state
3. Implement event state
4. Implement agent execution state
5. Add loading/error states

**Output:**
- ✅ Centralized state management
- ✅ Reactive UI updates
- ✅ Persistence for important state
- ✅ Better user experience

**See:** `docs/prompts/PHASE_3_4_5_6_COMPLETE.md` (Section: Phase 4)

---

### Phase 5: Testing & Validation (Priority: HIGH)
**Goal:** Ensure 100% functionality with tests

**Why Fifth:** Validate everything works before documentation

**Estimated Time:** 2-3 days

**Tasks:**
1. Backend API tests (pytest)
2. Frontend component tests (Jest)
3. Integration tests (E2E)
4. Manual testing workflow
5. Performance validation

**Output:**
- ✅ >80% test coverage
- ✅ All critical paths tested
- ✅ No regressions
- ✅ Confidence in deployment

**See:** `docs/prompts/PHASE_3_4_5_6_COMPLETE.md` (Section: Phase 5)

---

### Phase 6: Documentation & Polish (Priority: MEDIUM)
**Goal:** Complete documentation for users and developers

**Why Last:** Document what actually works

**Estimated Time:** 1-2 days

**Tasks:**
1. Enhance API documentation
2. Update README with setup guide
3. Create integration examples
4. Write troubleshooting guide
5. Add deployment instructions

**Output:**
- ✅ Complete API docs
- ✅ Developer setup guide
- ✅ User guide
- ✅ Troubleshooting section
- ✅ Deployment checklist

**See:** `docs/prompts/PHASE_3_4_5_6_COMPLETE.md` (Section: Phase 6)

---

## 📊 Progress Tracking

### Completion Criteria

#### Backend API (Phase 1)
- [x] Response format standardized
- [x] POST /api/v1/videos/process implemented
- [x] GET /api/v1/videos/{job_id}/status implemented
- [x] POST /api/v1/events/extract implemented
- [x] POST /api/v1/agents/dispatch implemented
- [x] GET /api/v1/agents/{agent_id}/status implemented
- [x] GET /api/v1/health implemented
- [x] CORS allows http://localhost:3000
- [x] Error handling middleware active
- [x] OpenAPI docs complete

#### Frontend Services (Phase 2)
- [x] APIClient class implemented
- [x] Type definitions created
- [x] VideoService implemented
- [x] EventService implemented
- [x] AgentService implemented
- [x] Environment config setup
- [x] Error handling utilities

#### UI Components (Phase 3)
- [x] VideoInput component works
- [x] VideoStatus component polls correctly
- [x] TranscriptViewer displays text
- [x] EventList shows events
- [x] AgentDashboard shows status
- [x] ResultsViewer displays outputs

#### State Management (Phase 4)
- [x] Zustand store setup
- [x] Video state managed
- [x] Event state managed
- [x] Agent state managed
- [x] Loading states handled

#### Testing (Phase 5)
- [x] Backend tests pass
- [ ] Frontend tests pass
- [ ] Integration tests pass
- [x] Manual workflow tested
- [ ] Performance validated

#### Documentation (Phase 6)
- [x] API docs complete
- [x] README updated
- [x] Setup guide tested
- [ ] Troubleshooting added
- [ ] Deployment guide created

---

## 🔧 Development Environment Setup

### Prerequisites
- Python >= 3.11
- Node.js >= 20
- npm >= 8
- Git

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/groupthinking/EventRelay.git
cd EventRelay

# 2. Backend setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev,youtube,ml]

# 3. Environment configuration
cp .env.example .env
# Edit .env and add API keys (at minimum: GEMINI_API_KEY, YOUTUBE_API_KEY)

# 4. Frontend setup
cd apps/web
npm install
cp .env.local.example .env.local
# Edit .env.local (set NEXT_PUBLIC_API_URL=http://localhost:8000)
cd ../..

# 5. Verify setup
python -c "import fastapi, pydantic; print('Backend OK')"
cd apps/web && npm list next && cd ../..
```

### Running Development Servers

```bash
# Terminal 1: Backend
source .venv/bin/activate
uvicorn uvai.api.main:app --reload --port 8000

# Terminal 2: Frontend
cd apps/web
npm run dev

# Terminal 3: Testing
pytest tests/ -v --cov           # Backend tests
cd apps/web && npm test          # Frontend tests
```

### Verification

```bash
# Check backend
curl http://localhost:8000/docs
curl http://localhost:8000/health

# Check frontend
open http://localhost:3000

# Check CORS
curl -H "Origin: http://localhost:3000" -I http://localhost:8000/api/v1/health
```

---

## 🎯 Critical Success Factors

### Must-Have Features
1. ✅ User can submit YouTube URL
2. ✅ Backend processes video and extracts transcript
3. ✅ Frontend displays transcript
4. ✅ Events are extracted and displayed
5. ✅ Agents can be dispatched
6. ✅ Agent status is visible
7. ✅ Results are displayed
8. ✅ Errors are handled gracefully

### Quality Standards
- **Code Quality:** Follow existing patterns (Black, ESLint)
- **Type Safety:** Python type hints, TypeScript strict mode
- **Test Coverage:** >80% for new code
- **Documentation:** All public APIs documented
- **Performance:** API responses <200ms (p95)
- **Security:** No secrets in code, input validation

### Risk Mitigation
- **Phase-based:** Complete each phase before next
- **Testing:** Test after each change
- **Incremental:** Small, verifiable changes
- **Rollback:** Can revert to previous state
- **Documentation:** Track decisions and changes

---

## 📚 Reference Documentation

### Architecture Documents
- `docs/BACKEND_FRONTEND_INTEGRATION.md` - Complete task breakdown
- `docs/analysis/ARCHITECTURE_ANALYSIS.md` - Current architecture
- `AGENTS.md` - Agent implementation guidelines

### Implementation Prompts
- `docs/prompts/PHASE_1_BACKEND_API.md` - Backend API prompts
- `docs/prompts/PHASE_2_FRONTEND_SERVICES.md` - Frontend service prompts
- `docs/prompts/PHASE_3_4_5_6_COMPLETE.md` - UI, state, testing, docs prompts

### Existing Documentation
- `README.md` - Project overview and quick start
- `.env.example` - Environment variable reference
- `pyproject.toml` - Backend dependencies and config
- `apps/web/package.json` - Frontend dependencies

---

## 🚦 Next Steps

### Immediate Actions (Start Here)

1. **Review this guide completely**
   - Understand the full scope
   - Familiarize with architecture
   - Review all reference docs

2. **Setup development environment**
   - Follow "Development Environment Setup" section
   - Verify both servers run
   - Test basic connectivity

3. **Start Phase 1: Backend API**
   - Read `docs/prompts/PHASE_1_BACKEND_API.md`
   - Implement standardized response models
   - Create video processing endpoints
   - Test with curl/Postman

4. **Continue to Phase 2: Frontend Services**
   - Read `docs/prompts/PHASE_2_FRONTEND_SERVICES.md`
   - Create API client
   - Define TypeScript types
   - Implement service methods

5. **Build UI in Phase 3**
   - Read `docs/prompts/PHASE_3_4_5_6_COMPLETE.md`
   - Create video input component
   - Test full workflow
   - Iterate on UX

### Validation at Each Phase

After completing each phase:
- ✅ Run tests (`pytest` and `npm test`)
- ✅ Test manually in browser
- ✅ Verify against checklist
- ✅ Document any issues
- ✅ Commit working code

### Getting Help

If stuck:
1. Check troubleshooting sections in docs
2. Review existing code patterns
3. Test individual components in isolation
4. Check backend logs for errors
5. Use browser DevTools for frontend debugging

---

## ✅ Final Checklist

Before considering integration complete:

### Functionality
- [x] Full workflow works: URL → Results
- [x] Video processing completes successfully
- [x] Events are extracted correctly
- [x] Agents execute and show results
- [x] Errors display user-friendly messages

### Technical
- [x] All API endpoints work
- [x] Frontend makes real backend calls
- [x] Type safety throughout
- [x] State management working
- [ ] Tests pass with >80% coverage

### Quality
- [x] Code follows style guidelines
- [x] No hardcoded values
- [x] Environment variables used
- [x] Logging is comprehensive
- [ ] Performance meets targets

### Documentation
- [x] API documentation complete
- [x] README is accurate
- [x] Setup guide is tested
- [ ] Troubleshooting is helpful
- [ ] Examples work correctly

### Deployment Ready
- [x] Production config available
- [x] Database migrations work
- [x] CORS configured correctly
- [ ] Error tracking setup
- [ ] Monitoring in place

---

## 🎊 Success Indicators

You'll know the integration is complete and successful when:

1. **User Experience:**
   - User can paste any YouTube URL
   - Processing completes without errors
   - Transcript displays clearly
   - Events are meaningful and accurate
   - Agent results are useful

2. **Developer Experience:**
   - Code is clean and maintainable
   - Tests provide confidence
   - Documentation is helpful
   - Debugging is straightforward
   - Future changes are easy

3. **Technical Metrics:**
   - API response times <200ms
   - Test coverage >80%
   - No CORS errors
   - Error rate <0.1%
   - Uptime >99%

---

**Last Updated:** 2026-02-11
**Status:** v1.0.0 — Production
**Estimated Total Time:** 10-15 days (single developer)

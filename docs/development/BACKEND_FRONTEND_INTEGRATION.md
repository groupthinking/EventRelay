# EventRelay Backend-Frontend Integration Guide

## 🎯 Framework First Principles Analysis

### Current State Architecture

#### Backend (FastAPI)
```
Location: src/youtube_extension/backend/main_v2.py
Port: 8000
Status: Production-ready with modular service architecture

Current Structure:
- FastAPI application with OpenAPI documentation
- CORS middleware configured for multiple origins
- Service-oriented architecture with dependency injection
- MCP bridge endpoint at /mcp
- Legacy endpoints for backward compatibility
- WebSocket support for real-time updates
```

#### Frontend (Next.js)
```
Location: apps/web/src/
Port: 3000 (dev), 3001 (production option)
Status: Basic structure in place, needs integration

Current Structure:
- Next.js 14+ with App Router
- TypeScript strict mode
- Tailwind CSS for styling
- API routes at /api/*
- Dashboard page at /dashboard
- Minimal API integration (mock data)
```

#### Integration Gap Analysis

**Missing Connections:**
1. ❌ Frontend has no direct backend API client
2. ❌ No shared type definitions between backend/frontend
3. ❌ Dashboard uses mock data instead of real backend
4. ❌ No video processing workflow in frontend
5. ❌ No agent execution UI
6. ❌ No real-time updates via WebSocket
7. ❌ Environment configuration incomplete

### Core EventRelay Workflow

```
┌──────────────────────────────────────────────────────────────┐
│  STEP 1: YouTube URL Input                                    │
│  User pastes YouTube link → Frontend captures URL             │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 2: Extract Context                                      │
│  Backend: Transcribe video → Extract events from transcript   │
│  - Use YouTube API or yt-dlp                                  │
│  - Process with Google Speech-to-Text v2                      │
│  - Parse transcript into structured events                    │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 3: Spawn Agents                                         │
│  Backend: Dispatch intelligent agents based on events         │
│  - Agent coordinator analyzes events                          │
│  - Select appropriate specialized agents                      │
│  - Initialize agent execution contexts                        │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 4: Run Tasks                                            │
│  Agents: Execute real-world actions                           │
│  - Code generation, content creation, workflow triggers       │
│  - Use MCP protocol for agent communication                   │
│  - Track progress and results                                 │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 5: Publish Outputs                                      │
│  Frontend: Display results through dashboard                  │
│  - Show transcript and extracted events                       │
│  - Display agent status and progress                          │
│  - Present generated outputs/artifacts                        │
│  - Store transcript in RAG for future learning                │
└──────────────────────────────────────────────────────────────┘
```

---

## 📋 Complete Task Breakdown

### Phase 1: Backend API Standardization (Priority: HIGH)

**Objective:** Create consistent, well-documented API endpoints that match EventRelay workflow

#### Task 1.1: Define API Response Format
**Subtasks:**
1. Create standardized response models in `src/youtube_extension/backend/api/v1/models.py`
2. Define `APIResponse`, `ErrorResponse`, `PaginatedResponse` types
3. Ensure all responses include `status`, `data`, `timestamp`, `request_id`
4. Add validation using Pydantic v2

**Steps:**
```python
# 1. Edit models.py
# 2. Add base response models
class APIResponse(BaseModel):
    status: str  # "success" | "error"
    data: Any
    timestamp: datetime
    request_id: str
    
class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    detail: Optional[str]
    request_id: str
```

#### Task 1.2: Video Processing Endpoints
**Subtasks:**
1. Create `/api/v1/videos/process` POST endpoint
2. Accept YouTube URL and options
3. Return job ID for async tracking
4. Implement `/api/v1/videos/{job_id}/status` GET endpoint
5. Return transcript, events, and agent status

**Steps:**
```python
# 1. Create video_routes.py in api/v1/
# 2. Define request/response models
# 3. Implement async processing
# 4. Add to router
```

**Clean:** Remove any duplicate/legacy video endpoints

#### Task 1.3: Event Extraction Endpoints
**Subtasks:**
1. Create `/api/v1/events/extract` POST endpoint
2. Accept transcript text or video_id
3. Return structured events list
4. Add `/api/v1/events/{event_id}` GET endpoint

#### Task 1.4: Agent Dispatch Endpoints
**Subtasks:**
1. Create `/api/v1/agents/dispatch` POST endpoint
2. Accept events and agent configuration
3. Return agent execution tracking IDs
4. Implement `/api/v1/agents/{agent_id}/status` GET
5. Add `/api/v1/agents/{agent_id}/results` GET

#### Task 1.5: Health & Status Endpoints
**Subtasks:**
1. Implement `/api/v1/health` GET endpoint
2. Add `/api/v1/status` with system metrics
3. Create `/api/v1/metrics` for monitoring

**Clean:** Remove duplicate health endpoints from root

#### Task 1.6: CORS Configuration
**Verification:**
- Ensure `http://localhost:3000` is in allowed origins
- Verify credentials=True for auth
- Test OPTIONS preflight requests

#### Task 1.7: Error Handling Middleware
**Subtasks:**
1. Create global exception handler
2. Map Python exceptions to HTTP status codes
3. Return consistent error format
4. Add request ID tracking
5. Log errors with context

---

### Phase 2: Frontend Service Layer (Priority: HIGH)

**Objective:** Create abstraction layer for all backend API calls

#### Task 2.1: API Client Service
**Subtasks:**
1. Create `apps/web/src/services/api-client.ts`
2. Configure base URL from environment
3. Add request/response interceptors
4. Implement retry logic
5. Add timeout handling

**Steps:**
```typescript
// 1. Create api-client.ts
// 2. Define APIClient class
class APIClient {
  private baseURL: string;
  
  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  
  async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    // Implementation with error handling
  }
}
```

#### Task 2.2: Environment Configuration
**Subtasks:**
1. Create `apps/web/.env.local.example`
2. Define `NEXT_PUBLIC_API_URL`
3. Add `NEXT_PUBLIC_WS_URL` for WebSocket
4. Document required variables

**Clean:** Remove hardcoded URLs from components

#### Task 2.3: Error Handling Utilities
**Subtasks:**
1. Create `apps/web/src/lib/errors.ts`
2. Define custom error classes
3. Implement error parsing
4. Add user-friendly error messages

#### Task 2.4: Type Definitions
**Subtasks:**
1. Create `apps/web/src/types/api.ts`
2. Mirror backend Pydantic models
3. Define video, event, agent types
4. Add response wrapper types

**Steps:**
```typescript
// 1. Create api.ts
interface VideoProcessRequest {
  video_url: string;
  options?: Record<string, any>;
}

interface VideoProcessResponse {
  job_id: string;
  status: string;
  video_id: string;
}

interface Event {
  id: string;
  type: string;
  description: string;
  timestamp: number;
  metadata: Record<string, any>;
}
```

#### Task 2.5: Service Methods
**Subtasks:**
1. Create `apps/web/src/services/video-service.ts`
2. Implement `processVideo(url: string)`
3. Implement `getVideoStatus(jobId: string)`
4. Create `apps/web/src/services/event-service.ts`
5. Create `apps/web/src/services/agent-service.ts`

---

### Phase 3: Core Integration Features (Priority: HIGH)

**Objective:** Build UI components that implement EventRelay workflow

#### Task 3.1: Video URL Input Component
**Subtasks:**
1. Create `apps/web/src/components/VideoInput.tsx`
2. Add URL validation
3. Show loading state during submission
4. Display error messages
5. Add submit handler calling backend

**Steps:**
```typescript
// 1. Create VideoInput.tsx
'use client';
import { useState } from 'react';
import { processVideo } from '@/services/video-service';

export function VideoInput({ onSubmit }: Props) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await processVideo(url);
      onSubmit(result);
    } catch (error) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };
  
  return (/* JSX */);
}
```

#### Task 3.2: Transcript Display Component
**Subtasks:**
1. Create `apps/web/src/components/TranscriptViewer.tsx`
2. Fetch transcript from backend
3. Display with syntax highlighting
4. Add timestamp markers
5. Make searchable

#### Task 3.3: Event List Component
**Subtasks:**
1. Create `apps/web/src/components/EventList.tsx`
2. Display extracted events
3. Group by type/category
4. Add filtering and sorting
5. Show event metadata

#### Task 3.4: Agent Status Dashboard
**Subtasks:**
1. Create `apps/web/src/components/AgentDashboard.tsx`
2. Show active agents
3. Display execution status
4. Show progress indicators
5. Add real-time updates

#### Task 3.5: Results/Outputs Viewer
**Subtasks:**
1. Create `apps/web/src/components/ResultsViewer.tsx`
2. Display agent outputs
3. Support multiple formats (text, code, JSON)
4. Add download capability
5. Show execution logs

#### Task 3.6: Real-time Progress Updates
**Subtasks:**
1. Create `apps/web/src/hooks/useWebSocket.ts`
2. Connect to backend WebSocket
3. Handle connection lifecycle
4. Subscribe to job updates
5. Update UI reactively

---

### Phase 4: State Management (Priority: MEDIUM)

**Objective:** Manage application state consistently

#### Task 4.1: Setup State Management
**Subtasks:**
1. Choose between Context API or Zustand
2. Create store structure
3. Define actions and selectors

**Recommendation:** Use Zustand for simplicity

**Steps:**
```typescript
// 1. Install: npm install zustand
// 2. Create apps/web/src/store/use-app-store.ts
import create from 'zustand';

interface AppState {
  currentVideo: VideoState | null;
  events: Event[];
  agents: AgentState[];
  setCurrentVideo: (video: VideoState) => void;
  addEvent: (event: Event) => void;
  updateAgent: (agentId: string, status: AgentState) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentVideo: null,
  events: [],
  agents: [],
  setCurrentVideo: (video) => set({ currentVideo: video }),
  addEvent: (event) => set((state) => ({ events: [...state.events, event] })),
  updateAgent: (agentId, status) => set((state) => ({
    agents: state.agents.map(a => a.id === agentId ? status : a)
  })),
}));
```

#### Task 4.2: Video Processing State
**Subtasks:**
1. Track video URL, job ID, status
2. Store transcript and metadata
3. Handle loading/error states

#### Task 4.3: Agent Execution State
**Subtasks:**
1. Track active agents
2. Store execution status
3. Cache results

#### Task 4.4: Loading/Error States
**Subtasks:**
1. Global loading indicator
2. Error boundary component
3. Toast notifications

---

### Phase 5: Testing & Validation (Priority: HIGH)

**Objective:** Ensure 100% functionality with comprehensive tests

#### Task 5.1: Backend API Tests
**Subtasks:**
1. Test video processing endpoint
2. Test event extraction
3. Test agent dispatch
4. Test error handling
5. Test CORS configuration

**Steps:**
```python
# Create tests/api/test_video_endpoints.py
import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_process_video():
    client = TestClient(app)
    response = client.post("/api/v1/videos/process", json={
        "video_url": "https://youtube.com/watch?v=auJzb1D-fag"
    })
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
```

#### Task 5.2: Frontend Component Tests
**Subtasks:**
1. Test VideoInput component
2. Test API service methods
3. Test error handling
4. Test state management

**Steps:**
```bash
# Install testing dependencies
cd apps/web
npm install --save-dev @testing-library/react @testing-library/jest-dom jest
```

#### Task 5.3: Integration Tests (E2E)
**Subtasks:**
1. Setup Playwright or Cypress
2. Test full workflow: URL → Results
3. Test error scenarios
4. Test real-time updates

#### Task 5.4: Manual Testing Workflow
**Process:**
1. Start backend: `uvicorn uvai.api.main:app --reload --port 8000`
2. Start frontend: `cd apps/web && npm run dev`
3. Test workflow:
   - Enter YouTube URL
   - Verify transcript extraction
   - Check event list
   - Monitor agent execution
   - View results

#### Task 5.5: Performance Validation
**Subtasks:**
1. Measure API response times
2. Test concurrent requests
3. Validate WebSocket performance
4. Check memory usage

---

### Phase 6: Documentation & Polish (Priority: MEDIUM)

**Objective:** Complete documentation for developers and users

#### Task 6.1: API Documentation
**Subtasks:**
1. Ensure OpenAPI docs are complete
2. Add example requests/responses
3. Document error codes
4. Create Postman collection

#### Task 6.2: Frontend Usage Guide
**Subtasks:**
1. Create user guide in `docs/USER_GUIDE.md`
2. Add screenshots
3. Document each workflow step
4. Add troubleshooting section

#### Task 6.3: Integration Examples
**Subtasks:**
1. Create example in `examples/basic-integration/`
2. Show minimal integration
3. Add advanced examples

#### Task 6.4: Developer Setup Guide
**Subtasks:**
1. Update README.md
2. Document environment setup
3. Add common issues and solutions

#### Task 6.5: Deployment Instructions
**Subtasks:**
1. Document production deployment
2. Add Docker configuration
3. Create deployment checklist

---

## 🔧 Environment Configuration

### Backend (.env)
```bash
# API Keys
GEMINI_API_KEY=your_key_here
YOUTUBE_API_KEY=your_key_here

# Database
DATABASE_URL=sqlite:///./.runtime/app.db

# Server
APP_PORT=8000
APP_HOST=0.0.0.0

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Frontend (.env.local)
```bash
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# App Config
NEXT_PUBLIC_APP_NAME=EventRelay
```

---

## 🚀 Implementation Order (Critical Path)

1. **Phase 1.1-1.2:** Backend video processing endpoints (MUST DO FIRST)
2. **Phase 2.1-2.4:** Frontend API client and types (MUST DO SECOND)
3. **Phase 3.1:** Video input component (FIRST UI)
4. **Phase 1.3-1.4:** Event and agent endpoints (BACKEND SUPPORT)
5. **Phase 3.2-3.5:** Display components (REST OF UI)
6. **Phase 4.1-4.4:** State management (POLISH)
7. **Phase 5.1-5.4:** Testing (VALIDATION)
8. **Phase 6:** Documentation (FINAL)

---

## ✅ Success Criteria

### Backend
- ✅ All API endpoints return consistent format
- ✅ CORS allows frontend origin
- ✅ Error handling returns user-friendly messages
- ✅ OpenAPI docs are complete and accurate
- ✅ Health endpoint responds correctly

### Frontend
- ✅ Can submit YouTube URL and get job ID
- ✅ Can poll for video processing status
- ✅ Displays transcript when ready
- ✅ Shows extracted events
- ✅ Displays agent execution status
- ✅ Shows final results/outputs
- ✅ Handles errors gracefully
- ✅ UI is responsive and accessible

### Integration
- ✅ Full workflow works end-to-end
- ✅ Real-time updates function correctly
- ✅ No CORS errors
- ✅ API calls succeed with valid data
- ✅ Tests pass at >80% coverage

### Performance
- ✅ API responses < 200ms (p95)
- ✅ Page load < 3s
- ✅ No memory leaks
- ✅ Handles concurrent users

---

## 🔍 Clean-up Tasks

### Remove
- Legacy/duplicate health endpoints
- Mock data in dashboard
- Hardcoded URLs
- Unused imports
- Dead code paths

### Standardize
- Error response format
- Logging format
- API versioning
- Code style

### Document
- Architecture decisions
- API contracts
- Environment variables
- Deployment process

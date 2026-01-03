# EventRelay Architecture Diagrams

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE LAYER                            │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   Next.js Frontend (Port 3000)                    │  │
│  │                                                                    │  │
│  │  Pages:                    Components:                            │  │
│  │  ├── /                     ├── VideoInput.tsx                     │  │
│  │  ├── /dashboard            ├── VideoStatus.tsx                    │  │
│  │  └── /api/*                ├── TranscriptViewer.tsx               │  │
│  │                            ├── EventList.tsx                      │  │
│  │  Services:                 ├── AgentDashboard.tsx                 │  │
│  │  ├── api-client.ts         └── ResultsViewer.tsx                  │  │
│  │  ├── video-service.ts                                             │  │
│  │  ├── event-service.ts      State (Zustand):                       │  │
│  │  └── agent-service.ts      └── useAppStore                        │  │
│  │                                                                    │  │
│  └────────────────────────────┬───────────────────────────────────────┘  │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
                     HTTP REST API │ (JSON over HTTP)
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                                 │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend (Port 8000)                          │  │
│  │                                                                    │  │
│  │  Endpoints:                                                        │  │
│  │  ├── POST   /api/v1/videos/process                               │  │
│  │  ├── GET    /api/v1/videos/{job_id}/status                       │  │
│  │  ├── GET    /api/v1/videos/{video_id}                            │  │
│  │  ├── POST   /api/v1/events/extract                               │  │
│  │  ├── GET    /api/v1/events?video_id={id}                         │  │
│  │  ├── POST   /api/v1/agents/dispatch                              │  │
│  │  ├── GET    /api/v1/agents/{agent_id}/status                     │  │
│  │  ├── GET    /api/v1/agents/{agent_id}/results                    │  │
│  │  └── GET    /api/v1/health                                        │  │
│  │                                                                    │  │
│  │  Middleware:                                                       │  │
│  │  ├── CORS (allow localhost:3000)                                 │  │
│  │  ├── Error Handler (standardized errors)                         │  │
│  │  ├── Request ID (tracking)                                       │  │
│  │  └── Rate Limiting (prevent abuse)                               │  │
│  │                                                                    │  │
│  └────────────────────────────┬───────────────────────────────────────┘  │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER                                    │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │   Video         │  │   Event         │  │   Agent         │        │
│  │   Processing    │  │   Extraction    │  │   Orchestrator  │        │
│  │   Service       │  │   Service       │  │   Service       │        │
│  │                 │  │                 │  │                 │        │
│  │ • Download      │  │ • Parse text    │  │ • Dispatch      │        │
│  │ • Transcribe    │  │ • Classify      │  │ • Monitor       │        │
│  │ • Process       │  │ • Extract       │  │ • Collect       │        │
│  │ • Cache         │  │ • Score         │  │ • Return        │        │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘        │
│           │                    │                    │                  │
└───────────┼────────────────────┼────────────────────┼──────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      INTEGRATION LAYER                                   │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │   YouTube    │  │    Google    │  │    Gemini    │  │   MCP    │  │
│  │   API v3     │  │  Speech-to-  │  │     API      │  │ Protocol │  │
│  │              │  │    Text v2   │  │              │  │          │  │
│  │ • Metadata   │  │ • Transcribe │  │ • Analyze    │  │ • JSON   │  │
│  │ • Download   │  │ • Long videos│  │ • Generate   │  │  -RPC    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘  │
│                                                                          │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                      │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │   SQLite     │  │    Redis     │  │     RAG      │  │   File   │  │
│  │  (dev mode)  │  │   Cache      │  │    Store     │  │  Storage │  │
│  │              │  │ (optional)   │  │              │  │          │  │
│  │ • Jobs       │  │ • Sessions   │  │ • Transcripts│  │ • Videos │  │
│  │ • Events     │  │ • Status     │  │ • Embeddings │  │ • Temp   │  │
│  │ • Agents     │  │ • Results    │  │ • Learning   │  │          │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Sequence

### 1. Video Submission
```
User                Frontend             Backend              YouTube API
 │                    │                    │                     │
 │ Enter URL          │                    │                     │
 ├───────────────────>│                    │                     │
 │                    │ POST /videos/      │                     │
 │                    │     process        │                     │
 │                    ├───────────────────>│                     │
 │                    │                    │ Fetch metadata      │
 │                    │                    ├────────────────────>│
 │                    │                    │<────────────────────┤
 │                    │                    │  (title, duration)  │
 │                    │<───────────────────┤                     │
 │                    │  {job_id, status}  │                     │
 │<───────────────────┤                    │                     │
 │  Show "Processing" │                    │                     │
```

### 2. Transcript Extraction
```
Frontend             Backend              Speech-to-Text       Database
 │                    │                     │                     │
 │ Poll status        │                     │                     │
 ├───────────────────>│                     │                     │
 │ GET /status        │                     │                     │
 │                    │ Check progress      │                     │
 │                    ├────────────────────────────────────────>│
 │                    │<───────────────────────────────────────┤
 │                    │                     │                     │
 │                    │ Process audio       │                     │
 │                    ├────────────────────>│                     │
 │                    │<────────────────────┤                     │
 │                    │  (transcript text)  │                     │
 │                    │                     │                     │
 │                    │ Store transcript    │                     │
 │                    ├────────────────────────────────────────>│
 │<───────────────────┤                     │                     │
 │  {status: "done",  │                     │                     │
 │   transcript: "…"} │                     │                     │
```

### 3. Event Extraction
```
Frontend             Backend              Gemini API          Database
 │                    │                     │                     │
 │ POST /events/      │                     │                     │
 │     extract        │                     │                     │
 ├───────────────────>│                     │                     │
 │ {transcript}       │                     │                     │
 │                    │ Analyze text        │                     │
 │                    ├────────────────────>│                     │
 │                    │<────────────────────┤                     │
 │                    │  (structured events)│                     │
 │                    │                     │                     │
 │                    │ Store events        │                     │
 │                    ├────────────────────────────────────────>│
 │<───────────────────┤                     │                     │
 │  {events: [        │                     │                     │
 │    {type, desc},   │                     │                     │
 │    ...             │                     │                     │
 │  ]}                │                     │                     │
```

### 4. Agent Dispatch
```
Frontend             Backend              MCP Agents          Database
 │                    │                     │                     │
 │ POST /agents/      │                     │                     │
 │     dispatch       │                     │                     │
 ├───────────────────>│                     │                     │
 │ {events, agents}   │                     │                     │
 │                    │ Initialize agents   │                     │
 │                    ├────────────────────>│                     │
 │                    │                     │ Start execution     │
 │                    │                     │                     │
 │<───────────────────┤                     │                     │
 │  {executions: [    │                     │                     │
 │    {agent_id},     │                     │                     │
 │    ...             │                     │                     │
 │  ]}                │                     │                     │
 │                    │                     │                     │
 │ Poll agent status  │                     │                     │
 ├───────────────────>│                     │                     │
 │ GET /agents/{id}/  │                     │                     │
 │     status         │                     │                     │
 │                    │ Check progress      │                     │
 │                    ├────────────────────────────────────────>│
 │<───────────────────┤                     │                     │
 │  {status, progress}│                     │                     │
```

### 5. Results Display
```
Frontend             Backend              Database
 │                    │                     │
 │ GET /agents/{id}/  │                     │
 │     results        │                     │
 ├───────────────────>│                     │
 │                    │ Fetch results       │
 │                    ├────────────────────>│
 │                    │<────────────────────┤
 │<───────────────────┤  (outputs, logs)    │
 │  {outputs: [       │                     │
 │    {type, data},   │                     │
 │    ...             │                     │
 │  ],                │                     │
 │   artifacts: [...]}│                     │
 │                    │                     │
 │ Display to user    │                     │
```

---

## Component Interaction Map

```
┌────────────────────────────────────────────────────────────────┐
│                      Frontend Components                        │
└────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│   VideoInput    │──┐
└─────────────────┘  │
                     │    ┌──────────────────┐
┌─────────────────┐  ├───>│  VideoService    │
│  VideoStatus    │──┤    └──────────────────┘
└─────────────────┘  │              │
                     │              ▼
┌─────────────────┐  │    ┌──────────────────┐
│ TranscriptViewer│──┘    │   APIClient      │────> Backend
└─────────────────┘       └──────────────────┘

┌─────────────────┐       ┌──────────────────┐
│   EventList     │──────>│  EventService    │
└─────────────────┘       └──────────────────┘
                                    │
                                    ▼
┌─────────────────┐       ┌──────────────────┐
│ AgentDashboard  │──┐    │   APIClient      │────> Backend
└─────────────────┘  │    └──────────────────┘
                     │
┌─────────────────┐  │    ┌──────────────────┐
│ ResultsViewer   │──┴───>│  AgentService    │
└─────────────────┘       └──────────────────┘

         All Components Access
                 ▼
        ┌──────────────────┐
        │   useAppStore    │
        │   (Zustand)      │
        └──────────────────┘
```

---

## Type Flow

```
Backend (Python/Pydantic)          Frontend (TypeScript)
─────────────────────────          ────────────────────────

class VideoProcessRequest          interface VideoProcessRequest
  video_url: str             ═══>    video_url: string
  options: dict                      options?: Record<string, any>

class VideoProcessResponse         interface VideoProcessResponse
  job_id: str                ═══>    job_id: string
  video_id: str                      video_id: string
  status: str                        status: string
  created_at: datetime               created_at: string

class Event                        interface Event
  id: str                    ═══>    id: string
  type: EventType                    type: EventType
  description: str                   description: string
  timestamp: float                   timestamp: number
  confidence: float                  confidence: number
  metadata: dict                     metadata: Record<string, any>
```

**Rule:** Frontend types MUST match backend models exactly!

---

## Error Flow

```
Backend                        Frontend
────────                      ─────────

Exception Occurs
    │
    ▼
Error Handler Middleware
    │
    ├─> Map to HTTP Status
    │
    ├─> Create ErrorResponse {
    │     status: "error"
    │     error: "Type"
    │     detail: "Message"
    │     request_id: "..."
    │   }
    │
    ▼
Return JSON ────────────────> APIClient
                                  │
                                  ├─> Parse ErrorResponse
                                  │
                                  ├─> Create APIError
                                  │
                                  ▼
                              Component
                                  │
                                  ├─> Display Error Message
                                  │
                                  ▼
                              User Sees Clear Error
```

---

## State Management Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Zustand Store (Global State)               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Video State    │  │  Event State    │  │ Agent State  │ │
│  │                 │  │                 │  │              │ │
│  │ • job_id        │  │ • events[]      │  │ • agents[]   │ │
│  │ • video_id      │  │ • selected      │  │ • active     │ │
│  │ • status        │  │                 │  │              │ │
│  │ • error         │  │                 │  │              │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘ │
│           │                    │                   │         │
└───────────┼────────────────────┼───────────────────┼─────────┘
            │                    │                   │
            ▼                    ▼                   ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │ VideoInput   │    │  EventList   │    │    Agent     │
    │ Component    │    │  Component   │    │  Dashboard   │
    └──────────────┘    └──────────────┘    └──────────────┘

User Action
    │
    ▼
Component calls action (e.g., setVideoStatus)
    │
    ▼
Store updates state
    │
    ▼
All subscribed components re-render with new state
```

---

## File Structure

```
EventRelay/
├── Backend
│   └── src/youtube_extension/backend/
│       ├── main_v2.py                    # FastAPI app
│       ├── api/
│       │   └── v1/
│       │       ├── models.py             # Pydantic models
│       │       ├── video_routes.py       # Video endpoints
│       │       ├── event_routes.py       # Event endpoints
│       │       └── agent_routes.py       # Agent endpoints
│       ├── services/
│       │   ├── video_service.py
│       │   ├── event_service.py
│       │   └── agent_service.py
│       └── middleware/
│           └── error_handler.py
│
└── Frontend
    └── apps/web/
        ├── src/
        │   ├── app/
        │   │   ├── page.tsx              # Home page
        │   │   └── dashboard/
        │   │       └── page.tsx          # Dashboard
        │   ├── components/
        │   │   ├── VideoInput.tsx
        │   │   ├── VideoStatus.tsx
        │   │   ├── TranscriptViewer.tsx
        │   │   ├── EventList.tsx
        │   │   ├── AgentDashboard.tsx
        │   │   └── ResultsViewer.tsx
        │   ├── services/
        │   │   ├── api-client.ts
        │   │   ├── video-service.ts
        │   │   ├── event-service.ts
        │   │   └── agent-service.ts
        │   ├── types/
        │   │   ├── video.ts
        │   │   ├── event.ts
        │   │   └── agent.ts
        │   └── store/
        │       └── use-app-store.ts
        └── .env.local                    # Config
```

---

## Network Communication

```
HTTP Request/Response Format
─────────────────────────────

Request:
POST /api/v1/videos/process HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Origin: http://localhost:3000

{
  "video_url": "https://youtube.com/watch?v=auJzb1D-fag",
  "options": {}
}

Response:
HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: http://localhost:3000
X-Request-ID: req_123456789

{
  "status": "success",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "video_id": "auJzb1D-fag",
    "status": "pending",
    "created_at": "2024-01-01T12:00:00Z"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456789"
}
```

---

**Visual Summary Complete** ✓

This document provides visual representations of:
- Complete system architecture
- Data flow sequences for each workflow step
- Component interaction patterns
- Type synchronization between backend/frontend
- Error handling flow
- State management architecture
- File structure organization
- Network communication format

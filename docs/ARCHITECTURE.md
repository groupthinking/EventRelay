# EventRelay Architecture Guide

> A deep-dive into how EventRelay transforms YouTube videos into actionable agent-driven workflows.

## What EventRelay Does

EventRelay is an AI-powered video automation platform that:

1. **Captures** word-for-word transcripts from YouTube videos
2. **Extracts** concrete, actionable events from unstructured content
3. **Dispatches** MCP-compliant agents to execute real follow-up actions
4. **Learns** from each run to improve subsequent executions

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EventRelay Platform                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Frontend   │    │   Backend    │    │  Prescient   │                   │
│  │   Next.js    │◄──►│   FastAPI    │◄──►│    Twin      │                   │
│  │   :3000      │    │    :8000     │    │    :8001     │                   │
│  └──────────────┘    └──────┬───────┘    └──────────────┘                   │
│                             │                                                │
│         ┌───────────────────┼───────────────────┐                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │   Service   │     │     AI      │     │    MCP      │                   │
│  │   Layer     │     │   Router    │     │ Orchestrator│                   │
│  └─────────────┘     └─────────────┘     └─────────────┘                   │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────────────────────────────────────────────┐                   │
│  │                  Integration Layer                   │                   │
│  │  YouTube API │ Gemini │ OpenAI │ Claude │ Vercel    │                   │
│  └─────────────────────────────────────────────────────┘                   │
│                             │                                                │
│         ┌───────────────────┼───────────────────┐                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │  SQLite/    │     │    Redis    │     │     GCS     │                   │
│  │  PostgreSQL │     │    Cache    │     │   Buckets   │                   │
│  └─────────────┘     └─────────────┘     └─────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Backend (FastAPI)

**Location:** `src/youtube_extension/backend/`

The backend is a service-oriented FastAPI application with dependency injection.

**Entry Point:** `main.py`
- Creates FastAPI app with CORS, rate limiting, security headers
- Initializes 19 registered services via service container
- Mounts versioned API routers (`/api/v1/*`)

**Service Container Pattern:**
```python
# src/youtube_extension/backend/containers/service_container.py
from dependency_functions import get_service

# Services are lazily initialized singletons
video_service = get_service('video_processing_service')
cache_service = get_service('cache_service')
agent_orchestrator = get_service('agent_orchestrator')
```

**Key Services:**
| Service | Purpose |
|---------|---------|
| `VideoProcessingService` | YouTube processing, transcript extraction |
| `AgentOrchestrator` | Agent selection and dispatch |
| `CacheService` | Result caching with TTL |
| `HealthMonitoringService` | Component health checks |
| `MetricsService` | Performance tracking |
| `WebSocketConnectionManager` | Real-time updates |

### 2. AI Router (Multi-Provider)

**Location:** `src/youtube_extension/services/ai/`

EventRelay uses an intelligent multi-provider AI router with automatic fallback:

```
Request → Cloud AI Router
    ├─ Check provider quota/health
    ├─ Route to optimal provider based on task type
    └─ Fallback chain:
        1. Google Gemini (visual/multimodal tasks)
        2. OpenAI GPT (code/logic tasks)
        3. Claude (reasoning/context tasks)
        4. Grok (realtime/current events)
```

**Provider Selection Logic:**
- `VIDEO_ANALYSIS` → Gemini (best multimodal)
- `CODE_GENERATION` → OpenAI or Claude
- `TREND_ANALYSIS` → Grok (realtime data)
- `STRATEGIC_PLANNING` → Claude (long context)

### 3. Agent System

**Location:** `src/youtube_extension/services/agents/`

Agents follow the MCP (Model Context Protocol) for standardized communication.

**Base Agent Lifecycle:**
```
initialize → analyze → plan → execute → report
```

**Agent Types:**
| Agent | Role |
|-------|------|
| `VideoMasterAgent` | Coordinates multi-agent video analysis |
| `CodeGeneratorAgent` | Generates code from video content |
| `DeploymentAgent` | Deploys to Vercel/GitHub |
| `WorkflowAgent` | Triggers CI/CD pipelines |
| `ContentCreatorAgent` | Creates docs and blog posts |
| `ArchitectureAgent` | Designs system architecture |

**Agent Communication:**
- Protocol: JSON-RPC via MCP
- Memory: Persisted lessons and tool repository
- Execution: E2B sandbox or direct

### 4. Event-Driven Pipeline

The core data flow through EventRelay:

```
YouTube URL
    ↓
┌─────────────────────────────┐
│   Transcription Service     │
│   ├─ youtube-transcript-api │
│   └─ Speech-to-Text v2      │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│   Event Extraction (LLM)    │
│   ├─ Parse structured events│
│   ├─ Classify types         │
│   └─ Store with confidence  │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│   Agent Orchestrator        │
│   ├─ Match agents to events │
│   ├─ Create execution ctx   │
│   └─ Dispatch via MCP       │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│   Agent Execution           │
│   ├─ E2B sandbox (code)     │
│   ├─ GitHub/Vercel (deploy) │
│   └─ Content generation     │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│   Learning Feedback Loop    │
│   ├─ Persist outcomes       │
│   ├─ Update RAG store       │
│   └─ Refine prompts         │
└─────────────────────────────┘
```

### 5. Prescient Twin (Self-Evolving Agents)

**Location:** `prescient-twin/`

A subsystem that allows agents to improve themselves by analyzing EventRelay's own videos and code.

**Components:**
- `main.py` - FastAPI server on port 8001
- `router.py` - Hybrid AI routing (Gemini/Claude/Grok)
- `sandbox_tool.py` - E2B remote execution
- `memory.py` - Tool repository + lesson storage
- `task_loop.py` - Ralph-style automation
- `dogfooding_pipeline.py` - Self-improvement workflow

**Key Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `/evolve` | Route task to best AI brain |
| `/execute` | Execute code in E2B sandbox |
| `/tools` | List evolved tools |
| `/lesson` | Record learning |
| `/dogfood` | Trigger self-improvement |
| `/learn_and_apply` | Learn from video, apply changes |

---

## Directory Structure

```
EventRelay/
├── src/
│   ├── youtube_extension/
│   │   ├── backend/
│   │   │   ├── main.py              # FastAPI entry point
│   │   │   ├── api/v1/
│   │   │   │   ├── router.py        # REST endpoints
│   │   │   │   └── models.py        # Pydantic schemas
│   │   │   ├── services/            # 19 business services
│   │   │   ├── containers/          # Dependency injection
│   │   │   └── migrations/          # Alembic DB migrations
│   │   ├── services/
│   │   │   ├── agents/              # Agent orchestration
│   │   │   ├── ai/                  # AI provider integrations
│   │   │   └── workflows/           # Workflow definitions
│   │   ├── integrations/            # External service adapters
│   │   └── mcp/                     # MCP servers
│   ├── agents/                      # Standalone agents
│   ├── integration/                 # Integration modules
│   ├── connectors/                  # MCP base classes
│   └── unified_ai_sdk/              # Unified AI interface
│
├── prescient-twin/                  # Self-evolving agent subsystem
│
├── apps/web/                        # Next.js frontend
│   └── src/
│       ├── app/                     # App router pages
│       ├── components/              # React components
│       └── services/                # API clients
│
├── mcp-servers/                     # Standalone MCP servers
│   ├── github/                      # GitHub operations
│   ├── genkit-wrapper/              # Google Genkit
│   ├── perplexity-mcp/              # Perplexity search
│   └── unified-analytics/           # Analytics
│
├── packages/                        # Shared packages
│   ├── database/                    # DB utilities
│   ├── state-manager/               # Redis state
│   ├── workflows/                   # Workflow engine
│   └── mcp-connectors/              # MCP connectors
│
├── infrastructure/
│   ├── terraform/                   # IaC configs
│   ├── k8s/                         # Kubernetes manifests
│   └── database/                    # DB schemas
│
├── config/
│   ├── agent_network.json           # Agent definitions
│   ├── api_config.json              # API settings
│   └── feature_flags.json           # Feature toggles
│
└── scripts/                         # Automation scripts
    ├── deployment/                  # Deploy scripts
    ├── development/                 # Dev helpers
    └── testing/                     # Test utilities
```

---

## Request Flow Example

Here's what happens when you submit a YouTube URL:

```
1. User: POST /api/v1/transcript-action
   Body: { "video_url": "https://youtube.com/watch?v=abc123" }

2. Router validates request (Pydantic)
   → TranscriptActionRequest model

3. Dependency injection provides services
   → VideoProcessingService
   → AgentOrchestrator

4. VideoProcessingService.process_video_for_markdown()
   ├─ Fetch video metadata (YouTube API)
   ├─ Extract transcript
   │   ├─ Try youtube-transcript-api (fast)
   │   └─ Fallback: Speech-to-Text v2 + yt-dlp
   ├─ Cache result
   └─ Persist to database

5. AgentOrchestrator.dispatch_agents()
   ├─ Route transcript to AI (Gemini/OpenAI/Claude)
   ├─ Parse events + classify types
   ├─ For each event → select matching agent
   ├─ Create execution context
   └─ Invoke agent via MCP protocol

6. Agents execute
   ├─ CodeGeneratorAgent → E2B sandbox
   ├─ DeploymentAgent → GitHub + Vercel
   └─ ContentCreatorAgent → markdown docs

7. Response returned
   ├─ job_id for polling
   ├─ extracted events
   └─ agent execution status

8. Learning loop (async)
   ├─ Persist outcomes
   ├─ Update RAG store
   └─ Refine agent prompts
```

---

## Technology Stack

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI 0.110+ | Web framework |
| Uvicorn 0.24+ | ASGI server |
| Python 3.9-3.12 | Runtime |
| SQLAlchemy 2.0+ | ORM |
| Pydantic 2.5+ | Validation |
| httpx 0.25+ | HTTP client |

### Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 14+ | React framework |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| Turbo | Monorepo build |

### AI & Integration
| Technology | Purpose |
|------------|---------|
| Google Gemini | Primary AI, multimodal |
| OpenAI GPT | Code generation |
| Anthropic Claude | Reasoning |
| Grok | Realtime data |
| youtube-transcript-api | Fast transcripts |
| google-cloud-speech v2 | Long video fallback |
| yt-dlp | Video download |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Terraform | Infrastructure as code |
| Kubernetes | Orchestration (optional) |
| Redis | Caching, state |
| PostgreSQL | Production database |
| SQLite | Development database |

---

## Key Design Decisions

### 1. Service-Oriented Architecture
**Why:** Enables independent scaling, testing, and deployment of components.

### 2. Multi-Provider AI with Fallback
**Why:** Prevents single-provider outages from breaking the system. Each provider has strengths for different task types.

### 3. MCP for Agent Communication
**Why:** Standardized protocol (JSON-RPC) allows agents to be developed independently and composed dynamically.

### 4. Event-Driven Pipeline
**Why:** Decouples stages, enables async processing, and allows learning loops to feed back into the system.

### 5. Self-Evolving Agents (Prescient Twin)
**Why:** Agents that analyze their own system can identify improvements and apply them automatically.

---

## Configuration

### Environment Variables

**Required (at least one AI provider):**
```bash
GEMINI_API_KEY=your-key      # Google AI Studio
OPENAI_API_KEY=your-key      # OpenAI Platform
```

**Optional:**
```bash
YOUTUBE_API_KEY=your-key     # Enhanced metadata
ANTHROPIC_API_KEY=your-key   # Claude support
GROK_API_KEY=your-key        # Grok support
VERCEL_TOKEN=your-token      # Deployment
GITHUB_TOKEN=your-token      # Code operations
SUPABASE_URL=your-url        # Database
REDIS_URL=your-url           # Caching
```

**Production Settings:**
```bash
REAL_MODE_ONLY=true          # Disable simulations
NODE_ENV=production
```

### MCP Configuration

**Core Config:** `.github/mcp-servers.json`
**VSCode:** `.vscode/mcp.json`
**Cursor:** `.cursor/mcp.json`

```json
{
  "servers": {
    "youtube-extension": {
      "command": "python",
      "args": ["scripts/youtube_innovation_mcp_server.py"],
      "env": { "MCP_TIMEOUT": "300" }
    }
  }
}
```

---

## Scaling Considerations

### Horizontal Scaling
- Backend services are stateless (scale via replicas)
- Use Redis for shared state across instances
- Deploy multiple agent workers for parallel execution

### Vertical Scaling
- AI processing benefits from more memory
- Video processing is CPU-intensive

### Caching Strategy
- Transcript results cached for 24 hours
- AI responses cached with content-based keys
- Use Redis for distributed caching in production

---

## Next Steps

- [API Reference](API_REFERENCE.md) - Detailed endpoint documentation
- [Onboarding Guide](ONBOARDING.md) - Getting started for contributors
- [Documentation Gaps](DOCUMENTATION_GAPS.md) - Areas needing clarification

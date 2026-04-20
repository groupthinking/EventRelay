# EventRelay API Reference

> Complete documentation of REST APIs, services, and functions for developers aged 20-30.

**Base URL:** `http://localhost:8000`
**API Docs:** `http://localhost:8000/docs` (Swagger UI)

---

## Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/v1/transcript-action` | POST | **Main workflow**: video → events → agents |
| `/api/v1/generate` | POST | Revenue pipeline: video → code → deploy |
| `/api/v1/video/process` | POST | Process YouTube video |
| `/api/v1/chat` | POST | Interactive chat |
| `/api/v1/cloud-ai/analyze/video` | POST | Multi-provider video analysis |
| `/api/v1/events` | POST | Ingest events |

---

## Core Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-01-25T12:00:00Z"
}
```

---

### Transcript Action (Primary Workflow)

Transform a YouTube video into extracted events and dispatch agents.

```http
POST /api/v1/transcript-action
Content-Type: application/json

{
  "video_url": "https://www.youtube.com/watch?v=m0XAPRAOJ8A",
  "language": "en"
}
```

**cURL Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/transcript-action \
     -H "Content-Type: application/json" \
     -d '{"video_url":"https://www.youtube.com/watch?v=m0XAPRAOJ8A","language":"en"}'
```

**Response:**
```json
{
  "job_id": "abc123",
  "status": "processing",
  "video_metadata": {
    "title": "Building a React App",
    "duration": "15:42",
    "channel": "Tech Tutorial"
  },
  "events": [
    {
      "type": "ACTION",
      "content": "Create new React project with Vite",
      "timestamp": "00:02:15",
      "confidence": 0.95
    },
    {
      "type": "REFERENCE",
      "content": "React documentation",
      "timestamp": "00:05:30",
      "confidence": 0.88
    }
  ],
  "agents_dispatched": ["CodeGeneratorAgent", "WorkflowAgent"]
}
```

**Event Types:**
- `ACTION` - Concrete step to perform
- `MENTION` - Reference to a tool/concept
- `TOPIC` - Subject being discussed
- `REFERENCE` - External resource mentioned

---

### Generate (Revenue Pipeline)

Convert a YouTube video into deployable code.

```http
POST /api/v1/generate
Content-Type: application/json

{
  "video_url": "https://youtube.com/watch?v=xyz",
  "deployment_target": "vercel",
  "project_type": "web_app"
}
```

**Deployment Targets:**
- `vercel` - Deploy to Vercel
- `github` - Push to GitHub repo
- `netlify` - Deploy to Netlify
- `local` - Generate locally only

**Response:**
```json
{
  "job_id": "gen-456",
  "status": "completed",
  "artifacts": {
    "code_path": "/output/generated-app",
    "files": ["package.json", "src/App.tsx", "src/index.css"],
    "deployment_url": "https://my-app.vercel.app"
  }
}
```

---

### Video Processing

Process a YouTube video for analysis.

```http
POST /api/v1/video/process
Content-Type: application/json

{
  "video_url": "https://youtube.com/watch?v=abc",
  "force_regenerate": false
}
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `video_url` | string | Yes | YouTube video URL |
| `force_regenerate` | boolean | No | Skip cache, reprocess |

---

### Video to Markdown

Generate a learning guide from a video.

```http
POST /api/v1/video/markdown
Content-Type: application/json

{
  "video_url": "https://youtube.com/watch?v=abc"
}
```

**Response:**
```json
{
  "markdown": "# Building a React App\n\n## Key Concepts\n...",
  "metadata": {
    "word_count": 1500,
    "sections": ["Introduction", "Setup", "Implementation"]
  }
}
```

---

### Chat Interface

Interactive Q&A about video content.

```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "What libraries were mentioned in the video?",
  "session_id": "sess-123",
  "context": {
    "video_id": "abc123"
  }
}
```

**Response:**
```json
{
  "response": "The video mentioned React, Vite, and Tailwind CSS...",
  "status": "success",
  "session_id": "sess-123",
  "timestamp": "2025-01-25T12:05:00Z"
}
```

---

## Cloud AI Endpoints

### Provider Status

Check which AI providers are available.

```http
GET /api/v1/cloud-ai/providers/status
```

**Response:**
```json
{
  "providers": {
    "gemini": {
      "status": "available",
      "quota_remaining": 1000,
      "latency_ms": 150
    },
    "openai": {
      "status": "available",
      "quota_remaining": 500,
      "latency_ms": 200
    },
    "claude": {
      "status": "rate_limited",
      "retry_after_seconds": 60
    }
  }
}
```

### Video Analysis (Single Provider)

```http
POST /api/v1/cloud-ai/analyze/video
Content-Type: application/json

{
  "video_url": "https://youtube.com/watch?v=abc",
  "analysis_type": "technical_breakdown",
  "provider": "gemini"
}
```

**Analysis Types:**
- `technical_breakdown` - Extract APIs, endpoints, tech stack
- `content_summary` - High-level overview
- `action_items` - Actionable steps
- `code_extraction` - Code snippets shown

### Batch Analysis (with Fallback)

```http
POST /api/v1/cloud-ai/analyze/batch
Content-Type: application/json

{
  "video_urls": [
    "https://youtube.com/watch?v=abc",
    "https://youtube.com/watch?v=xyz"
  ],
  "analysis_type": "content_summary",
  "fallback_enabled": true
}
```

### Multi-Provider Analysis

Get results from multiple AI providers in parallel.

```http
POST /api/v1/cloud-ai/analyze/multi-provider
Content-Type: application/json

{
  "video_url": "https://youtube.com/watch?v=abc",
  "providers": ["gemini", "openai", "claude"],
  "merge_results": true
}
```

---

## Integration Endpoints

### Gemini Video Analysis

```http
POST /api/v1/integrations/gemini/analyze
Content-Type: application/json

{
  "video_url": "https://youtube.com/watch?v=abc",
  "media_resolution": "high",
  "thinking_level": "detailed"
}
```

### Gemini Technical Breakdown

```http
POST /api/v1/integrations/gemini/technical-breakdown
Content-Type: application/json

{
  "video_url": "https://youtube.com/watch?v=abc"
}
```

**Response:**
```json
{
  "tech_stack": ["React", "Node.js", "PostgreSQL"],
  "apis_mentioned": ["REST API", "GraphQL"],
  "endpoints": ["/api/users", "/api/products"],
  "capabilities": ["CRUD operations", "Authentication"]
}
```

### YouTube Metadata

```http
POST /api/v1/integrations/youtube/metadata
Content-Type: application/json

{
  "video_url": "https://youtube.com/watch?v=abc"
}
```

### Vercel Deployment

```http
POST /api/v1/integrations/vercel/deploy
Content-Type: application/json

{
  "source": "directory",
  "path": "/output/my-app",
  "project_name": "my-app"
}
```

### OpenAI Voice

```http
POST /api/v1/integrations/openai/transcribe
Content-Type: multipart/form-data

audio: <audio file>
```

```http
POST /api/v1/integrations/openai/tts
Content-Type: application/json

{
  "text": "Hello, world!",
  "voice": "alloy"
}
```

---

## Event Ingestion

```http
POST /api/v1/events
Content-Type: application/json

{
  "type": "user_login",
  "data": {
    "user_id": "123",
    "timestamp": "2025-01-25T12:00:00Z"
  },
  "timestamp": "2025-01-25T12:00:00Z"
}
```

---

## Service Classes

### VideoProcessingService

**Location:** `src/youtube_extension/backend/services/video_processing_service.py`

```python
from dependency_functions import get_service

video_service = get_service('video_processing_service')

# Process video and generate markdown
result = await video_service.process_video_for_markdown(
    video_url="https://youtube.com/watch?v=abc",
    force_regenerate=False
)
```

**Methods:**
| Method | Description |
|--------|-------------|
| `process_video_for_markdown(url, force)` | Full video processing pipeline |
| `get_video_processor()` | Get or create processor instance |
| `resolve_deployment_target(target)` | Map deployment target aliases |

### AgentOrchestrator

**Location:** `src/youtube_extension/services/agents/agent_orchestrator.py`

```python
orchestrator = get_service('agent_orchestrator')

# Dispatch agents for events
result = await orchestrator.dispatch_agents(
    events=extracted_events,
    context={"video_id": "abc123"}
)
```

**Methods:**
| Method | Description |
|--------|-------------|
| `dispatch_agents(events, context)` | Select and run agents |
| `get_agent_status(agent_id)` | Check execution status |
| `cancel_agent(agent_id)` | Stop running agent |

### CacheService

```python
cache = get_service('cache_service')

# Get cached result
result = cache.get_cached_result(video_url)

# Save result
cache.save_result(video_url, result, ttl=86400)
```

### StateManager (Redis)

**Location:** `packages/state-manager/src/index.ts`

```typescript
import { StateManager } from '@eventrelay/state-manager';

const state = new StateManager({ keyPrefix: 'eventrelay:' });
await state.initialize();

// Store value
await state.set('my-key', { data: 'value' }, 3600);

// Retrieve value
const value = await state.get('my-key');

// Workflow state
await state.saveWorkflowState({
  id: 'workflow-123',
  status: 'running',
  step: 'processing',
  data: {}
});

// Rate limiting
const { success, remaining } = await state.checkRateLimit('user:123');

// Distributed locking
const acquired = await state.acquireLock('resource:abc', 30);
```

---

## Agent Types

### CodeGeneratorAgent

Generates code from video content.

```python
from src.agents.specialized.code_generator import CodeGeneratorAgent

agent = CodeGeneratorAgent()
result = await agent.execute({
    "intent": "Create REST API endpoint",
    "context": transcript_data
})
```

**Templates:**
- `fastapi_endpoint` - FastAPI route
- `rest_api` - Generic REST endpoint
- `crud_operations` - CRUD boilerplate

### ArchitectureAgent

Designs system architecture.

```python
from src.agents.specialized.architecture_agent import ArchitectureAgent

agent = ArchitectureAgent()
result = await agent.analyze_architecture("/path/to/project")
```

**Message Handlers:**
- `initialize` - Start analysis
- `analyze_project` - Analyze structure
- `create_plan` - Create implementation plan
- `execute_task` - Execute specific task
- `validate_fixes` - Validate changes

### DeploymentAgent

Deploys code to platforms.

```python
from src.agents.specialized.deployment_agent import DeploymentAgent

agent = DeploymentAgent()
result = await agent.deploy({
    "target": "vercel",
    "source_path": "/output/my-app"
})
```

---

## MCP Bridge

**Location:** `src/mcp/bridge.py`

Unified interface for MCP communication.

```python
from src.mcp.bridge import MCPBridge, MCPBridgeRequest, ProcessingPriority

bridge = MCPBridge(config)

request = MCPBridgeRequest(
    request_id="req-123",
    task_type="code_generation",
    content={"prompt": "Create a React component"},
    priority=ProcessingPriority.HIGH,
    preferred_provider="claude",
    use_rag=True
)

result = await bridge.process(request)
```

**System Modes:**
- `AUTONOMOUS` - Agents act independently
- `GUIDED` - Human approval required
- `HYBRID` - Context-dependent
- `EMERGENCY` - Override safety checks

---

## Unified AI SDK

**Location:** `src/unified_ai_sdk/unified_ai_sdk.py`

```python
from src.unified_ai_sdk import UnifiedAISDK, AIRequest, TaskType, ModelProvider

sdk = UnifiedAISDK(config)

request = AIRequest(
    prompt="Explain this code",
    model="gpt-4o-mini",
    provider=ModelProvider.OPENAI,
    task_type=TaskType.CODE_GENERATION,
    temperature=0.7,
    max_tokens=4000,
)

response = await sdk.unified_request(request)
if response.success:
    print(response.content)
else:
    print("error:", response.error)
```

**Providers:**
- `ModelProvider.OPENAI` - OpenAI chat completions
- `ModelProvider.CLAUDE` - Anthropic Messages API
- `ModelProvider.GEMINI` - Google Gemini `generate_content`

API keys are loaded from the `api_keys` config dict (keys: `openai`,
`claude`, `gemini`) or from `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` /
`GEMINI_API_KEY` (with `GOOGLE_API_KEY` as fallback) environment
variables. `unified_request` never raises — on final failure it returns
`AIResponse(success=False, error=..., content="")`.

**Task Types:**
- `VIDEO_ANALYSIS`
- `CODE_GENERATION`
- `TREND_ANALYSIS`
- `STRATEGIC_PLANNING`
- `CONTENT_GENERATION`
- `QUESTION_ANSWERING`
- `SUMMARIZATION`

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid video URL format",
    "details": {
      "field": "video_url",
      "expected": "Valid YouTube URL"
    }
  }
}
```

**Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `PROVIDER_ERROR` | 502 | AI provider failed |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limiting

Default limits per API key:
- 100 requests/minute for standard endpoints
- 10 requests/minute for AI-intensive endpoints
- 1000 requests/hour total

Headers returned:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706184000
```

---

## WebSocket API

Real-time updates for long-running jobs.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/jobs/abc123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Status:', data.status);
  console.log('Progress:', data.progress);
};
```

**Message Types:**
```json
{
  "type": "status_update",
  "job_id": "abc123",
  "status": "processing",
  "progress": 0.45,
  "current_step": "extracting_events"
}
```

---

## SDK Examples

### Python

```python
import httpx

async def process_video(video_url: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/transcript-action",
            json={"video_url": video_url, "language": "en"}
        )
        return response.json()
```

### TypeScript

```typescript
async function processVideo(videoUrl: string) {
  const response = await fetch('http://localhost:8000/api/v1/transcript-action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_url: videoUrl, language: 'en' })
  });
  return response.json();
}
```

### cURL

```bash
# Process video
curl -X POST http://localhost:8000/api/v1/transcript-action \
  -H "Content-Type: application/json" \
  -d '{"video_url":"https://youtube.com/watch?v=abc","language":"en"}'

# Check job status
curl http://localhost:8000/api/v1/jobs/abc123/status

# Get provider status
curl http://localhost:8000/api/v1/cloud-ai/providers/status
```

---

## Next Steps

- [Architecture Guide](ARCHITECTURE.md) - System design overview
- [Onboarding Guide](ONBOARDING.md) - Getting started
- [Documentation Gaps](DOCUMENTATION_GAPS.md) - Areas needing input

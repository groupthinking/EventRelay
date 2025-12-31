# Phase 1: Backend API Standardization - Copilot Prompts

## Overview
These prompts guide the implementation of consistent, production-ready API endpoints for EventRelay's core workflow.

---

## Prompt 1.1: Define API Response Format

```
Create standardized API response models for the EventRelay backend.

Context:
- Working in: src/youtube_extension/backend/api/v1/models.py
- Using: Pydantic v2, Python 3.9+, FastAPI
- Goal: Consistent response format across all endpoints

Requirements:
1. Create base response models with these fields:
   - status: "success" | "error" 
   - data: Any (the actual response payload)
   - timestamp: datetime (when response was generated)
   - request_id: str (unique identifier for tracking)

2. Create specific response types:
   - APIResponse[T]: Generic success response
   - ErrorResponse: Error with detail message
   - PaginatedResponse[T]: For paginated results
   - JobResponse: For async job tracking

3. Add validation using Pydantic validators:
   - Ensure status is valid enum
   - Validate timestamps are in ISO format
   - Generate request_id if not provided

4. Include example responses in docstrings

Example structure:
```python
from pydantic import BaseModel, Field, validator
from typing import Generic, TypeVar, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"

class APIResponse(BaseModel):
    status: ResponseStatus
    data: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {"message": "Operation completed"},
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
```

Constraints:
- Follow existing code style (Black formatter)
- Use Python type hints throughout
- Make all fields immutable where possible
- Add comprehensive docstrings
```

---

## Prompt 1.2: Video Processing Endpoints

```
Implement video processing API endpoints for EventRelay workflow.

Context:
- Working in: src/youtube_extension/backend/api/v1/video_routes.py (create new file)
- Using: FastAPI, async/await, existing video processor services
- Goal: Enable frontend to submit YouTube URLs and track processing

Requirements:

1. Create POST /api/v1/videos/process endpoint:
   - Accept VideoProcessRequest model with video_url and options
   - Validate YouTube URL format
   - Create async processing job
   - Return job_id immediately (don't block)
   - Store job status in database or cache

2. Create GET /api/v1/videos/{job_id}/status endpoint:
   - Accept job_id path parameter
   - Return processing status: "pending", "processing", "completed", "failed"
   - Include progress percentage (0-100)
   - Return transcript when available
   - Return extracted events when available

3. Create GET /api/v1/videos/{video_id} endpoint:
   - Retrieve processed video by video_id (YouTube ID)
   - Return cached results if available
   - Include metadata (title, duration, channel)

4. Add proper error handling:
   - 400 for invalid URLs
   - 404 for job not found
   - 500 for processing errors
   - Include helpful error messages

Request/Response models:
```python
class VideoProcessRequest(BaseModel):
    video_url: str = Field(..., description="YouTube video URL")
    options: Optional[dict] = Field(default_factory=dict)
    
    @validator('video_url')
    def validate_youtube_url(cls, v):
        if not ('youtube.com' in v or 'youtu.be' in v):
            raise ValueError('Must be a valid YouTube URL')
        return v

class VideoProcessResponse(BaseModel):
    job_id: str
    video_id: str
    status: str
    created_at: datetime

class VideoStatusResponse(BaseModel):
    job_id: str
    video_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    transcript: Optional[str] = None
    events: Optional[List[dict]] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None
```

Implementation steps:
1. Import existing video processor from video_processor_factory
2. Create background task for async processing
3. Store job status in shared cache/database
4. Update status as processing progresses
5. Handle cleanup for failed jobs

Router setup:
```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])

@router.post("/process", response_model=APIResponse[VideoProcessResponse])
async def process_video(
    request: VideoProcessRequest,
    background_tasks: BackgroundTasks
):
    # Implementation here
    pass

@router.get("/{job_id}/status", response_model=APIResponse[VideoStatusResponse])
async def get_video_status(job_id: str):
    # Implementation here
    pass
```

Connect to main_v2.py:
- Import router: `from .api.v1.video_routes import router as video_router`
- Include in app: `app.include_router(video_router)`

Testing:
- Test with video ID: auJzb1D-fag
- Verify async job creation
- Test status polling
- Confirm transcript return
```

---

## Prompt 1.3: Event Extraction Endpoints

```
Create event extraction API endpoints for EventRelay.

Context:
- Working in: src/youtube_extension/backend/api/v1/event_routes.py (create new file)
- Using: FastAPI, event extraction services
- Goal: Allow frontend to extract/view events from transcripts

Requirements:

1. Create POST /api/v1/events/extract endpoint:
   - Accept transcript text OR video_id
   - Use AI to extract structured events
   - Return list of Event objects with:
     * id (unique identifier)
     * type (action, mention, topic, decision, etc.)
     * description (what happened)
     * timestamp (relative to video)
     * confidence (0.0-1.0)
     * metadata (additional context)

2. Create GET /api/v1/events endpoint:
   - List events for a video_id
   - Support filtering by event type
   - Support pagination
   - Return in chronological order

3. Create GET /api/v1/events/{event_id} endpoint:
   - Get detailed information about specific event
   - Include full context and metadata
   - Show related events

Request/Response models:
```python
class EventType(str, Enum):
    ACTION = "action"
    MENTION = "mention"
    TOPIC = "topic"
    DECISION = "decision"
    QUESTION = "question"
    INSTRUCTION = "instruction"

class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    video_id: str
    type: EventType
    description: str
    timestamp: float  # seconds from start
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ExtractEventsRequest(BaseModel):
    transcript: Optional[str] = None
    video_id: Optional[str] = None
    
    @validator('transcript', 'video_id')
    def check_one_provided(cls, v, values):
        if not v and not values.get('video_id'):
            raise ValueError('Must provide either transcript or video_id')
        return v

class ExtractEventsResponse(BaseModel):
    events: List[Event]
    total_count: int
    processing_time_ms: float
```

Implementation notes:
- Use existing AI services for extraction
- Cache extracted events for video_id
- Apply rate limiting (prevent abuse)
- Log extraction requests for monitoring

Router:
```python
router = APIRouter(prefix="/api/v1/events", tags=["events"])

@router.post("/extract", response_model=APIResponse[ExtractEventsResponse])
async def extract_events(request: ExtractEventsRequest):
    # Implementation
    pass

@router.get("", response_model=APIResponse[PaginatedResponse[Event]])
async def list_events(
    video_id: str,
    event_type: Optional[EventType] = None,
    page: int = 1,
    limit: int = 50
):
    # Implementation
    pass
```
```

---

## Prompt 1.4: Agent Dispatch Endpoints

```
Implement agent dispatch and tracking API endpoints.

Context:
- Working in: src/youtube_extension/backend/api/v1/agent_routes.py (create new file)
- Using: FastAPI, MCP agent coordinator
- Goal: Enable frontend to dispatch agents and track execution

Requirements:

1. Create POST /api/v1/agents/dispatch endpoint:
   - Accept list of events
   - Accept agent configuration (which agents to use)
   - Dispatch appropriate specialized agents via MCP
   - Return list of agent execution IDs
   - Start async execution

2. Create GET /api/v1/agents/{agent_id}/status endpoint:
   - Return current status: "queued", "running", "completed", "failed"
   - Include progress information
   - Show execution logs/steps
   - Return partial results if available

3. Create GET /api/v1/agents/{agent_id}/results endpoint:
   - Return final agent outputs
   - Include generated artifacts (code, content, etc.)
   - Provide download links for large outputs
   - Show execution metadata

4. Create GET /api/v1/agents endpoint:
   - List all agents for a video_id or job_id
   - Show summary status for each
   - Support filtering by status

Request/Response models:
```python
class AgentType(str, Enum):
    CODE_GENERATOR = "code_generator"
    CONTENT_CREATOR = "content_creator"
    WORKFLOW_TRIGGER = "workflow_trigger"
    DATA_ANALYZER = "data_analyzer"

class AgentConfig(BaseModel):
    agent_type: AgentType
    parameters: dict = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)

class DispatchAgentsRequest(BaseModel):
    video_id: str
    events: List[str]  # Event IDs
    agents: List[AgentConfig]
    options: dict = Field(default_factory=dict)

class AgentExecution(BaseModel):
    agent_id: str
    agent_type: AgentType
    status: str  # queued, running, completed, failed
    progress: int  # 0-100
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class DispatchAgentsResponse(BaseModel):
    executions: List[AgentExecution]
    dispatch_id: str

class AgentResults(BaseModel):
    agent_id: str
    outputs: List[dict]
    artifacts: List[str]  # URLs or file paths
    logs: List[str]
    execution_time_ms: float
```

Router:
```python
router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

@router.post("/dispatch", response_model=APIResponse[DispatchAgentsResponse])
async def dispatch_agents(
    request: DispatchAgentsRequest,
    background_tasks: BackgroundTasks
):
    # Use MCP coordinator to dispatch agents
    pass

@router.get("/{agent_id}/status", response_model=APIResponse[AgentExecution])
async def get_agent_status(agent_id: str):
    pass

@router.get("/{agent_id}/results", response_model=APIResponse[AgentResults])
async def get_agent_results(agent_id: str):
    pass
```

Integration:
- Connect to existing MCP coordinator
- Use agent registry for available agents
- Implement proper error handling for agent failures
- Add monitoring/telemetry
```

---

## Prompt 1.5: Health & Monitoring Endpoints

```
Create comprehensive health check and monitoring endpoints.

Context:
- Working in: src/youtube_extension/backend/api/v1/health_routes.py (create new file)
- Using: FastAPI, system monitoring libraries
- Goal: Production-ready health checks and metrics

Requirements:

1. Create GET /api/v1/health endpoint:
   - Return 200 if system is healthy
   - Check critical dependencies (database, cache, AI APIs)
   - Return 503 if any critical component is down
   - Include component-level status

2. Create GET /api/v1/status endpoint:
   - Return detailed system status
   - Include version information
   - Show uptime
   - Report resource usage (CPU, memory)
   - Include active job counts

3. Create GET /api/v1/metrics endpoint:
   - Return Prometheus-compatible metrics
   - Include request counts, latency, errors
   - Track video processing metrics
   - Track agent execution metrics

Response models:
```python
class ComponentHealth(BaseModel):
    name: str
    status: str  # healthy, degraded, unhealthy
    message: Optional[str] = None
    latency_ms: Optional[float] = None

class HealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    version: str
    components: List[ComponentHealth]
    timestamp: datetime

class SystemStatus(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    cpu_percent: float
    memory_mb: float
    active_jobs: int
    active_agents: int
    cache_size: int
    
class Metrics(BaseModel):
    requests_total: int
    requests_per_minute: float
    average_latency_ms: float
    error_rate: float
    videos_processed_total: int
    agents_executed_total: int
```

Implementation:
```python
import psutil
from datetime import datetime

start_time = datetime.utcnow()

router = APIRouter(prefix="/api/v1", tags=["monitoring"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    components = []
    
    # Check database
    try:
        # Test database connection
        components.append(ComponentHealth(
            name="database",
            status="healthy",
            latency_ms=5.2
        ))
    except Exception as e:
        components.append(ComponentHealth(
            name="database",
            status="unhealthy",
            message=str(e)
        ))
    
    # Check AI API
    # Check cache
    # etc.
    
    overall_status = "healthy" if all(c.status == "healthy" for c in components) else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        version="2.0.0",
        components=components,
        timestamp=datetime.utcnow()
    )

@router.get("/status", response_model=APIResponse[SystemStatus])
async def system_status():
    uptime = (datetime.utcnow() - start_time).total_seconds()
    
    return APIResponse(
        status="success",
        data=SystemStatus(
            status="operational",
            version="2.0.0",
            uptime_seconds=uptime,
            cpu_percent=psutil.cpu_percent(),
            memory_mb=psutil.virtual_memory().used / 1024 / 1024,
            active_jobs=0,  # Get from job tracker
            active_agents=0,  # Get from agent coordinator
            cache_size=0  # Get from cache service
        )
    )
```

Clean up:
- Remove legacy /health endpoint from root
- Remove duplicate health checks
- Standardize on /api/v1/health
```

---

## Prompt 1.6: Error Handling Middleware

```
Implement comprehensive error handling middleware for FastAPI backend.

Context:
- Working in: src/youtube_extension/backend/middleware/error_handler.py (create new file)
- Using: FastAPI exception handlers, logging
- Goal: Consistent error responses across all endpoints

Requirements:

1. Create global exception handler:
   - Catch all unhandled exceptions
   - Map to appropriate HTTP status codes
   - Return ErrorResponse format
   - Log errors with full context

2. Handle specific exception types:
   - ValidationError (Pydantic) → 422
   - HTTPException (FastAPI) → specified code
   - PermissionError → 403
   - FileNotFoundError → 404
   - ValueError → 400
   - Generic Exception → 500

3. Add request ID tracking:
   - Generate unique ID per request
   - Include in response headers
   - Include in error logs
   - Allow client to reference in support

4. Implement error logging:
   - Log all errors with context
   - Include request path, method, params
   - Include user/session info if available
   - Don't log sensitive data

Implementation:
```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import uuid
import traceback

logger = logging.getLogger(__name__)

class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    detail: Optional[str] = None
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None

async def add_request_id_middleware(request: Request, call_next):
    """Add unique request ID to each request"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(f"Validation error [{request_id}]: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            detail=str(exc.errors()),
            request_id=request_id,
            path=request.url.path
        ).dict()
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log full traceback
    logger.error(
        f"Unhandled exception [{request_id}]: {str(exc)}\n"
        f"Path: {request.url.path}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    # Don't expose internal errors in production
    detail = str(exc) if os.getenv("DEBUG") else "Internal server error"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=detail,
            request_id=request_id,
            path=request.url.path
        ).dict()
    )

# Map Python exceptions to HTTP status codes
EXCEPTION_STATUS_MAP = {
    PermissionError: status.HTTP_403_FORBIDDEN,
    FileNotFoundError: status.HTTP_404_NOT_FOUND,
    ValueError: status.HTTP_400_BAD_REQUEST,
    TimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
}

def setup_error_handlers(app: FastAPI):
    """Register all error handlers with FastAPI app"""
    app.middleware("http")(add_request_id_middleware)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    for exc_class, status_code in EXCEPTION_STATUS_MAP.items():
        app.add_exception_handler(
            exc_class,
            lambda req, exc: JSONResponse(
                status_code=status_code,
                content=ErrorResponse(
                    error=exc_class.__name__,
                    detail=str(exc),
                    request_id=getattr(req.state, "request_id", "unknown")
                ).dict()
            )
        )
```

Add to main_v2.py:
```python
from .middleware.error_handler import setup_error_handlers

# After app creation
setup_error_handlers(app)
```
```

---

## Testing Checklist

After implementing Phase 1:

- [ ] All endpoints return APIResponse format
- [ ] Request IDs are in response headers
- [ ] CORS allows http://localhost:3000
- [ ] OpenAPI docs are complete at /docs
- [ ] Health endpoint returns component status
- [ ] Video processing creates async jobs
- [ ] Status endpoint shows processing progress
- [ ] Events can be extracted from transcript
- [ ] Agents can be dispatched with events
- [ ] Error responses are consistent
- [ ] Validation errors return 422
- [ ] All exceptions are caught and logged

Test with:
```bash
# Start backend
uvicorn uvai.api.main:app --reload --port 8000

# Test health
curl http://localhost:8000/api/v1/health

# Test video processing
curl -X POST http://localhost:8000/api/v1/videos/process \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://youtube.com/watch?v=auJzb1D-fag"}'

# View docs
open http://localhost:8000/docs
```

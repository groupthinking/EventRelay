# Cloud-Native Architecture: Vertex AI Agent Builder + Cloud Run

## Overview

This implementation provides a fully cloud-native architecture for the UVAI YouTube Extension using Google Cloud Platform services:

- **Vertex AI Agent Builder**: Advanced agent reasoning replacing direct Gemini API calls
- **Cloud Firestore**: Shared state management across pipeline stages
- **Cloud Tasks**: Async video processing queue
- **Cloud Run**: Serverless auto-scaling deployment (0→N instances)
- **Google Embedded 2**: Text embeddings for semantic search

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Request                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                Cloud Run (Auto-scaling 0→100)                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │          FastAPI Backend (cloud_api_endpoints.py)        │  │
│  │  - /api/v3/process-video (sync/async)                   │  │
│  │  - /api/v3/process-video-task (Cloud Tasks handler)     │  │
│  │  - /api/v3/videos/{id}/status (check progress)          │  │
│  │  - /api/v3/queue/stats (queue metrics)                  │  │
│  └─────────────────────────────────────────────────────────┘  │
└───┬─────────────┬─────────────┬─────────────┬──────────────────┘
    │             │             │             │
    ▼             ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│Firestore│  │Cloud     │  │Vertex AI │  │Secret        │
│(State)  │  │Tasks     │  │Agent     │  │Manager       │
│         │  │(Queue)   │  │Builder   │  │(API Keys)    │
└────────┘  └──────────┘  └──────────┘  └──────────────┘
```

## Components

### 1. Firestore State Service
**File**: `src/youtube_extension/services/cloud/firestore_state.py`

Manages shared state across Cloud Run instances and pipeline stages:

```python
from youtube_extension.services.cloud import get_firestore_service

# Create processing state
firestore_service = await get_firestore_service()
state = await firestore_service.create_state(
    video_id="abc123",
    video_url="https://youtube.com/watch?v=abc123"
)

# Update state as pipeline progresses
await firestore_service.update_state(
    video_id="abc123",
    status="processing",
    current_stage="transcript",
    metadata={"title": "My Video"}
)

# Get current state
state = await firestore_service.get_state("abc123")
```

**Features**:
- Persistent state across restarts
- Local caching with TTL (300s default)
- Concurrent access control
- State history tracking

### 2. Cloud Tasks Queue Service
**File**: `src/youtube_extension/services/cloud/cloud_tasks_queue.py`

Manages async video processing queue:

```python
from youtube_extension.services.cloud import (
    get_cloud_tasks_service,
    VideoProcessingTask
)

# Enqueue video for processing
tasks_service = get_cloud_tasks_service()
task = VideoProcessingTask(
    video_id="abc123",
    video_url="https://youtube.com/watch?v=abc123",
    priority=5
)

task_id = await tasks_service.enqueue_video_processing(task)
```

**Features**:
- Automatic retry with exponential backoff
- Priority-based ordering
- Concurrency control (max 50 concurrent)
- Rate limiting (100 tasks/second)

### 3. Vertex AI Agent Service
**File**: `src/youtube_extension/services/cloud/vertex_ai_agent.py`

Provides AI reasoning via Vertex AI Agent Builder:

```python
from youtube_extension.services.cloud import get_vertex_ai_service

vertex_service = get_vertex_ai_service()

# Analyze transcript
response = await vertex_service.analyze_transcript(
    transcript="Video transcript here...",
    video_metadata={"title": "My Video"}
)

# Generate embeddings (Google Embedded 2)
embeddings = await vertex_service.generate_embeddings(
    texts=["Text 1", "Text 2"],
    model_name="text-embedding-004"
)
```

**Features**:
- Agent-based reasoning (replaces direct Gemini API)
- Multi-turn conversations
- Structured output generation
- Text embeddings (Google Embedded 2)
- Batch processing with concurrency control

### 4. Cloud Video Processor
**File**: `src/youtube_extension/services/cloud/cloud_video_processor.py`

Orchestrates video processing with cloud services:

```python
from youtube_extension.services.cloud.cloud_video_processor import (
    get_cloud_video_processor
)

processor = get_cloud_video_processor()

# Async processing (non-blocking)
task_id = await processor.process_video_async(
    video_url="https://youtube.com/watch?v=abc123",
    priority=5
)

# Sync processing (blocking)
result = await processor.process_video_sync(
    video_url="https://youtube.com/watch?v=abc123"
)
```

**Pipeline Stages**:
1. **Metadata**: Fetch video metadata (YouTube API)
2. **Transcript**: Extract transcript
3. **Analysis**: AI analysis via Vertex AI
4. **Complete**: Final state update

## Deployment

### Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and configured
3. **Docker** installed
4. **Required APIs** enabled (done by setup script)

### Set up infrastructure

Provision resources through reviewed infrastructure changes and the manual
prerequisites in `docs/deployment/API_COST_POSTGRESQL_RUNBOOK.md`. The former
setup script is retired because it granted project-wide secret access and could
silently change a production identity. Existing Firestore, Cloud Tasks, Vertex
AI, service-account, and Cloud SQL configuration must be inventoried before the
first substrate release.

### Deploy to Cloud Run

Run the protected `.github/workflows/deploy-cloud-run.yml` workflow for an
exact tested SHA. Direct builds and deploys are retired because the canonical
workflow must migrate shared PostgreSQL before deploying the dedicated worker
and API. See `docs/deployment/API_COST_POSTGRESQL_RUNBOOK.md`.

## Configuration

### Environment Variables

Set through the protected deployment workflow and Secret Manager:

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1

# Enable cloud services
ENABLE_CLOUD_SERVICES=true
ENABLE_FIRESTORE=true
ENABLE_CLOUD_TASKS=true
ENABLE_VERTEX_AI=true

# Firestore
FIRESTORE_COLLECTION=video_processing_state

# Cloud Tasks
CLOUD_TASKS_QUEUE=video-processing-queue
CLOUD_RUN_SERVICE_URL=https://your-service-url.run.app

# Vertex AI
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-2.0-flash-exp
```

### Auto-Scaling Configuration

In the protected Cloud Run deployment workflow:

```yaml
annotations:
  autoscaling.knative.dev/minScale: "0"  # Scale to zero
  autoscaling.knative.dev/maxScale: "100"  # Max 100 instances
  autoscaling.knative.dev/target: "80"  # 80 concurrent requests/instance
```

### Resource Limits

```yaml
resources:
  limits:
    cpu: "2000m"  # 2 vCPU
    memory: "4Gi"  # 4GB RAM
```

## API Endpoints

### Process Video (Async)

```bash
curl -X POST https://your-service.run.app/api/v3/process-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=abc123",
    "priority": 5,
    "async_processing": true
  }'
```

Response:
```json
{
  "video_id": "abc123",
  "video_url": "https://youtube.com/watch?v=abc123",
  "success": true,
  "task_id": "task-uuid",
  "status": "queued"
}
```

### Check Status

```bash
curl https://your-service.run.app/api/v3/videos/abc123/status
```

Response:
```json
{
  "video_id": "abc123",
  "status": "processing",
  "current_stage": "analysis",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:05:00Z"
}
```

### Get Result

```bash
curl https://your-service.run.app/api/v3/videos/abc123/result
```

Response:
```json
{
  "video_id": "abc123",
  "video_url": "https://youtube.com/watch?v=abc123",
  "status": "completed",
  "metadata": {...},
  "transcript": {...},
  "ai_analysis": {...},
  "processing_time": 45.2
}
```

### Queue Stats

```bash
curl https://your-service.run.app/api/v3/queue/stats
```

### Cloud Status

```bash
curl https://your-service.run.app/api/v3/cloud-status
```

## Testing

Run tests:

```bash
# Install test dependencies
pip install -e .[dev,cloud]

# Run cloud services tests
pytest tests/test_firestore_state.py -v

# Run with coverage
pytest tests/test_firestore_state.py --cov=src/youtube_extension/services/cloud
```

## Monitoring

### View Logs

```bash
# Cloud Run logs
gcloud run services logs read uvai-backend --region us-central1

# Cloud Tasks logs
gcloud logging read "resource.type=cloud_tasks_queue"

# Firestore logs
gcloud logging read "resource.type=datastore_database"
```

### Metrics

View in Google Cloud Console:
- **Cloud Run**: Request count, latency, error rate, instance count
- **Cloud Tasks**: Queue depth, task execution time, retry rate
- **Firestore**: Read/write operations, storage usage
- **Vertex AI**: API calls, token usage, latency

## Cost Optimization

### Cloud Run

- **Scale to zero**: No cost when idle
- **Request-based billing**: Pay only for actual requests
- **CPU allocation**: Only during request processing (with CPU throttling)

### Firestore

- **Free tier**: 1GB storage, 50K reads, 20K writes per day
- **Caching**: Reduces read operations via local TTL cache

### Cloud Tasks

- **Free tier**: 1 million tasks per month
- **Queue rate limiting**: Prevents runaway costs

### Vertex AI

- **Model selection**: Use `gemini-2.0-flash-exp` for cost efficiency
- **Batch processing**: Process multiple items together
- **Token optimization**: Use concise prompts

## Acceptance Criteria ✅

- [x] Pipeline stages communicate via shared state (Firestore), not in-memory
- [x] Video processing is queued via Cloud Tasks (not blocking)
- [x] Cloud Run scales 0→N based on load
- [x] Vertex AI handles agent reasoning
- [x] Google Embedded 2 integration for embeddings
- [x] Auto-scaling configuration with concurrency limits
- [x] Shared state between pipeline stages
- [x] Async video processing queue

## Migration Guide

### From Direct Gemini API to Vertex AI

**Before**:
```python
import google.generativeai as genai

model = genai.GenerativeModel('gemini-2.0-flash-exp')
response = model.generate_content(prompt)
```

**After**:
```python
from youtube_extension.services.cloud import get_vertex_ai_service

vertex_service = get_vertex_ai_service()
response = await vertex_service.process_text(prompt)
```

### From In-Memory to Firestore State

**Before**:
```python
# In-memory dict
video_state = {"status": "processing"}
```

**After**:
```python
from youtube_extension.services.cloud import get_firestore_service

firestore_service = await get_firestore_service()
await firestore_service.update_state(
    video_id="abc123",
    status="processing"
)
```

## Troubleshooting

### Service won't start

Check logs:
```bash
gcloud run services logs read uvai-backend --region us-central1 --limit 50
```

Common issues:
- Missing environment variables
- Invalid API keys in Secret Manager
- Insufficient IAM permissions

### Tasks not processing

Check queue:
```bash
gcloud tasks queues describe video-processing-queue --location us-central1
```

Check task handler logs for errors.

### Firestore connection errors

Verify:
- Firestore is initialized in project
- Service account has `roles/datastore.user`
- Environment variable `GOOGLE_CLOUD_PROJECT` is set

## References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Agent Builder](https://cloud.google.com/vertex-ai/docs/agent-builder)
- [Cloud Firestore](https://cloud.google.com/firestore/docs)
- [Cloud Tasks](https://cloud.google.com/tasks/docs)
- [Gemini API via Vertex AI](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)

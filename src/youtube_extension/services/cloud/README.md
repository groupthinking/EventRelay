# Cloud Services

Google Cloud Platform services for cloud-native deployment.

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .[cloud]
```

This installs:
- `google-cloud-aiplatform` (Vertex AI)
- `google-cloud-firestore` (State management)
- `google-cloud-tasks` (Job queue)
- `google-cloud-storage` (Storage)
- `google-cloud-logging` (Logging)
- `google-cloud-monitoring` (Monitoring)

### 2. Setup Infrastructure

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
./infrastructure/cloudrun/setup.sh
```

### 3. Deploy to Cloud Run

```bash
./infrastructure/cloudrun/deploy.sh
```

## Services

### Firestore State Service

Manages shared state across Cloud Run instances:

```python
from youtube_extension.services.cloud import get_firestore_service

# Initialize
firestore_service = await get_firestore_service()

# Create state
state = await firestore_service.create_state(
    video_id="abc123",
    video_url="https://youtube.com/watch?v=abc123"
)

# Update state
await firestore_service.update_state(
    video_id="abc123",
    status="processing",
    metadata={"title": "My Video"}
)

# Get state
state = await firestore_service.get_state("abc123")
```

### Cloud Tasks Queue Service

Manages async video processing:

```python
from youtube_extension.services.cloud import (
    get_cloud_tasks_service,
    VideoProcessingTask
)

# Initialize
tasks_service = get_cloud_tasks_service()

# Enqueue task
task = VideoProcessingTask(
    video_id="abc123",
    video_url="https://youtube.com/watch?v=abc123",
    priority=5
)
task_id = await tasks_service.enqueue_video_processing(task)
```

### Vertex AI Agent Service

AI reasoning and embeddings:

```python
from youtube_extension.services.cloud import get_vertex_ai_service

# Initialize
vertex_service = get_vertex_ai_service()

# Process text
response = await vertex_service.process_text(
    prompt="Analyze this video transcript...",
    context="Video context..."
)

# Generate embeddings
embeddings = await vertex_service.generate_embeddings(
    texts=["Text 1", "Text 2"],
    model_name="text-embedding-004"
)
```

### Cloud Video Processor

Orchestrates video processing:

```python
from youtube_extension.services.cloud.cloud_video_processor import (
    get_cloud_video_processor
)

processor = get_cloud_video_processor()

# Async processing
task_id = await processor.process_video_async(
    video_url="https://youtube.com/watch?v=abc123",
    priority=5
)

# Sync processing
result = await processor.process_video_sync(
    video_url="https://youtube.com/watch?v=abc123"
)
```

## Configuration

Set environment variables:

```bash
# Required
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Optional
export GOOGLE_CLOUD_REGION="us-central1"
export FIRESTORE_COLLECTION="video_processing_state"
export CLOUD_TASKS_QUEUE="video-processing-queue"
export VERTEX_AI_MODEL="gemini-2.0-flash-exp"
```

## Testing

Run tests:

```bash
pytest tests/test_firestore_state.py -v
```

## Documentation

See [Cloud-Native Architecture Guide](../../docs/cloud-native-architecture.md) for complete documentation.

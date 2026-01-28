# Advanced Video Analysis Features

## Overview

EventRelay now includes advanced video analysis capabilities:

1. **Gemini Direct YouTube URL Ingestion** - Native YouTube URL support with file_data/file_uri
2. **Temporal Prompts with Timestamps** - Time-based analysis and reasoning
3. **Structured JSON Output/Schema** - Enforced response schemas
4. **EventMesh CloudEvents Publishing** - Standardized event publishing with OpenWhisk routing

## 1. Gemini Direct YouTube URL Ingestion

### Implementation Location
- **Service**: `src/integration/gemini_video.py`
- **Class**: `GeminiVideoService`

### Features
- Direct YouTube URL support (passed as text per Google's documentation)
- File URI support with `file_data/file_uri` for uploaded videos
- Automatic format detection and routing

### Usage

```python
from src.integration.gemini_video import GeminiVideoService

service = GeminiVideoService(api_key="YOUR_API_KEY")

# YouTube URL (direct)
result = await service.analyze_video(
    video_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
    prompt="Analyze this video",
    media_resolution="high",  # Use 'high' for text-heavy content
    thinking_level="high"     # Use 'high' for complex reasoning
)

# File URI (uploaded videos)
result = await service.analyze_video(
    video_url="gs://bucket/video.mp4",
    prompt="Analyze this video"
)

await service.close()
```

### API Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/integrations/gemini/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=example",
    "prompt": "Extract key events",
    "media_resolution": "high",
    "thinking_level": "high"
  }'
```

## 2. Temporal Prompts with Timestamps

### Implementation Location
- **Service**: `src/integration/temporal_video_analysis.py`
- **Class**: `TemporalVideoAnalyzer`
- **API Routes**: `src/youtube_extension/backend/api/advanced_video_routes.py`

### Features
- Analyze specific time segments
- Extract timestamped events
- Temporal question answering
- Create detailed timelines
- Compare multiple segments
- Extract tutorial steps with timestamps

### Usage

#### Analyze a Time Segment

```python
from src.integration.temporal_video_analysis import TemporalVideoAnalyzer

analyzer = TemporalVideoAnalyzer()

result = await analyzer.analyze_segment(
    video_url="https://youtube.com/watch?v=example",
    start_time="2:30",
    end_time="5:45",
    focus="code"  # Optional: "code", "speaker", "slides"
)

print(result.summary)
await analyzer.close()
```

#### Extract Timestamped Events

```python
events = await analyzer.extract_temporal_events(
    video_url="https://youtube.com/watch?v=example",
    event_types=["code_change", "api_call", "deployment"]
)

for event in events:
    print(f"{event.timestamp}: {event.description}")
```

#### Temporal Question Answering

```python
answer = await analyzer.temporal_question(
    video_url="https://youtube.com/watch?v=example",
    question="What API endpoint is called?",
    time_context="between 2:30 and 5:00"
)

print(answer)
```

#### Create Timeline

```python
timeline = await analyzer.create_timeline(
    video_url="https://youtube.com/watch?v=example",
    granularity="medium"  # "fine", "medium", or "coarse"
)

for marker in timeline:
    print(f"{marker['timestamp']}: {marker['section_title']}")
```

#### Extract Tutorial Steps

```python
steps = await analyzer.extract_tutorial_steps(
    video_url="https://youtube.com/watch?v=example"
)

for step in steps:
    print(f"Step {step['step_number']} at {step['timestamp']}: {step['title']}")
    print(f"  Instructions: {step['instructions']}")
```

### API Endpoints

#### Analyze Segment
```bash
curl -X POST http://localhost:8000/api/v1/video/temporal/segment \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=example",
    "start_time": "2:30",
    "end_time": "5:45",
    "focus": "code"
  }'
```

#### Extract Events
```bash
curl -X POST http://localhost:8000/api/v1/video/temporal/events \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=example",
    "event_types": ["code_change", "api_call"],
    "publish_events": true
  }'
```

#### Create Timeline
```bash
curl -X POST http://localhost:8000/api/v1/video/temporal/timeline \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=example",
    "granularity": "medium"
  }'
```

## 3. Structured JSON Output/Schema

### Implementation Location
- **Service**: `src/youtube_extension/services/ai/gemini_service.py`
- **Config**: `GeminiConfig.response_schema`
- **API Route**: `src/youtube_extension/backend/api/advanced_video_routes.py`

### Features
- Enforce JSON schema on Gemini responses
- Guaranteed output structure
- Type validation
- Schema-driven parsing

### Usage

```python
from src.youtube_extension.services.ai.gemini_service import GeminiService, GeminiConfig

# Define schema
schema = {
    "type": "object",
    "properties": {
        "apis": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "endpoint": {"type": "string"},
                    "method": {"type": "string"}
                },
                "required": ["name", "endpoint", "method"]
            }
        }
    },
    "required": ["apis"]
}

config = GeminiConfig(
    response_schema=schema,
    response_mime_type="application/json"
)

service = GeminiService(config)

result = await service.generate_content_async(
    [
        {"text": "https://youtube.com/watch?v=example"},
        {"text": "Extract all APIs mentioned"}
    ],
    response_schema=schema
)

# Result is guaranteed to match schema
import json
structured_data = json.loads(result.response)
print(structured_data["apis"])
```

### API Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/video/analyze/structured \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=example",
    "prompt": "Extract all APIs and their endpoints",
    "schema": {
      "type": "object",
      "properties": {
        "apis": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "endpoint": {"type": "string"},
              "method": {"type": "string"}
            }
          }
        }
      }
    },
    "publish_result": true
  }'
```

## 4. EventMesh CloudEvents Publishing

### Implementation Location
- **Service**: `src/integration/cloudevents_publisher.py`
- **Class**: `CloudEventsPublisher`
- **API Route**: `src/youtube_extension/backend/api/advanced_video_routes.py`

### Features
- CloudEvents v1.0 compliant
- Multiple backends:
  - Google Cloud Pub/Sub
  - HTTP webhooks
  - Apache OpenWhisk triggers
  - File (for testing)
- OpenWhisk action routing
- Extension attributes support

### CloudEvents Structure

```json
{
  "specversion": "1.0",
  "id": "unique-event-id",
  "source": "/video-analyzer/gemini",
  "type": "com.eventrelay.video.analyzed",
  "datacontenttype": "application/json",
  "time": "2025-01-28T12:00:00Z",
  "subject": "https://youtube.com/watch?v=example",
  "data": {
    "video_url": "https://youtube.com/watch?v=example",
    "summary": "Analysis results...",
    "events": []
  }
}
```

### Usage

#### Basic Publishing

```python
from src.integration.cloudevents_publisher import create_publisher

publisher = create_publisher(backend="pubsub")

event_id = await publisher.publish(
    source="/video-analyzer/gemini",
    type="com.eventrelay.video.analyzed",
    data={
        "video_url": "https://youtube.com/watch?v=example",
        "summary": "Analysis complete",
        "events": []
    },
    subject="https://youtube.com/watch?v=example"
)

print(f"Published event: {event_id}")
await publisher.close()
```

#### OpenWhisk Integration

```python
# Configure OpenWhisk backend
publisher = create_publisher(backend="openwhisk")

# This will trigger the "analyzed_trigger" in OpenWhisk
event_id = await publisher.publish(
    source="/video-analyzer/gemini",
    type="com.eventrelay.video.analyzed",
    data={"video_url": "..."}
)

await publisher.close()
```

#### HTTP Webhook

```python
publisher = create_publisher(
    backend="http",
    webhook_url="https://example.com/webhook"
)

event_id = await publisher.publish(
    source="/video-analyzer",
    type="com.eventrelay.video.processed",
    data={"status": "complete"}
)

await publisher.close()
```

### Environment Configuration

```bash
# Backend selection
CLOUDEVENTS_BACKEND=pubsub  # or "http", "openwhisk", "file"

# Pub/Sub
GOOGLE_CLOUD_PROJECT=your-project-id
PUBSUB_TOPIC=video-events

# HTTP Webhook
WEBHOOK_URL=https://example.com/webhook

# OpenWhisk
OPENWHISK_API_HOST=https://openwhisk.ng.bluemix.net
OPENWHISK_AUTH=username:password
OPENWHISK_NAMESPACE=your-namespace

# File (testing)
EVENTS_FILE_PATH=/tmp/cloudevents.jsonl
```

### API Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/video/publish-event \
  -H "Content-Type: application/json" \
  -d '{
    "source": "/video-processor/gemini",
    "event_type": "com.eventrelay.video.processed",
    "data": {
      "video_url": "https://youtube.com/watch?v=example",
      "status": "complete"
    },
    "subject": "https://youtube.com/watch?v=example",
    "backend": "pubsub"
  }'
```

### OpenWhisk Trigger Naming

The publisher automatically derives trigger names from event types:
- `com.eventrelay.video.analyzed` → `analyzed_trigger`
- `com.eventrelay.video.processed` → `processed_trigger`

### Setting Up OpenWhisk Actions

```bash
# Create a trigger
wsk trigger create analyzed_trigger

# Create an action
wsk action create process-video action.js

# Create a rule to connect trigger to action
wsk rule create video-analysis-rule analyzed_trigger process-video
```

## Integration Example: Full Workflow

```python
from src.integration.temporal_video_analysis import TemporalVideoAnalyzer
from src.integration.cloudevents_publisher import create_publisher

# 1. Analyze video with temporal prompts
analyzer = TemporalVideoAnalyzer()
events = await analyzer.extract_temporal_events(
    video_url="https://youtube.com/watch?v=example",
    event_types=["code_change", "api_call"]
)

# 2. Publish each event to EventMesh
publisher = create_publisher(backend="openwhisk")

for event in events:
    await publisher.publish(
        source="/video-analyzer/temporal",
        type=f"com.eventrelay.video.event.{event.event_type}",
        data={
            "timestamp": event.timestamp,
            "description": event.description,
            "confidence": event.confidence
        },
        subject="https://youtube.com/watch?v=example"
    )

await analyzer.close()
await publisher.close()
```

## Testing

Run the test suites:

```bash
# CloudEvents tests
pytest tests/unit/test_cloudevents_publisher.py -v

# Temporal analysis tests
pytest tests/unit/test_temporal_video_analysis.py -v
```

## File Locations Summary

| Feature | File Path |
|---------|-----------|
| Gemini YouTube URL Support | `src/integration/gemini_video.py` |
| Temporal Analysis | `src/integration/temporal_video_analysis.py` |
| CloudEvents Publisher | `src/integration/cloudevents_publisher.py` |
| Advanced API Routes | `src/youtube_extension/backend/api/advanced_video_routes.py` |
| CloudEvents Tests | `tests/unit/test_cloudevents_publisher.py` |
| Temporal Tests | `tests/unit/test_temporal_video_analysis.py` |
| Documentation | `docs/ADVANCED_VIDEO_FEATURES.md` (this file) |

## Next Steps

1. Configure environment variables for your backend
2. Test with sample videos
3. Set up OpenWhisk triggers and actions
4. Monitor events in your EventMesh
5. Integrate with downstream consumers

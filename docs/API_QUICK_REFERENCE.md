# Quick Reference: Advanced Video Analysis APIs

## Temporal Analysis Endpoints

### 1. Analyze Time Segment
**Endpoint**: `POST /api/v1/video/temporal/segment`

```bash
curl -X POST http://localhost:8000/api/v1/video/temporal/segment \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "start_time": "1:30",
    "end_time": "3:45",
    "focus": "code"
  }'
```

**Response**:
```json
{
  "segment": {
    "start_time": "1:30",
    "end_time": "3:45",
    "focus": "code"
  },
  "analysis": {
    "summary": "Code demonstration showing API implementation",
    "key_events": [...],
    "timestamps": [...]
  }
}
```

---

### 2. Extract Timestamped Events
**Endpoint**: `POST /api/v1/video/temporal/events`

```bash
curl -X POST http://localhost:8000/api/v1/video/temporal/events \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "event_types": ["code_change", "api_call", "deployment"],
    "publish_events": true
  }'
```

**Response**:
```json
{
  "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "events_count": 5,
  "events": [
    {
      "timestamp": "1:30",
      "type": "code_change",
      "description": "Added error handling",
      "confidence": 0.95,
      "metadata": {}
    }
  ],
  "published": true,
  "published_event_ids": ["event-id-1", "event-id-2"]
}
```

---

### 3. Temporal Question Answering
**Endpoint**: `POST /api/v1/video/temporal/question`

```bash
curl -X POST http://localhost:8000/api/v1/video/temporal/question \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "question": "What API endpoint is called?",
    "time_context": "between 2:30 and 5:00"
  }'
```

**Response**:
```json
{
  "question": "What API endpoint is called?",
  "time_context": "between 2:30 and 5:00",
  "answer": "Answer: POST /api/users\nEvidence at 3:15: HTTP POST request visible on screen\nEvidence at 3:45: Response received from endpoint"
}
```

---

### 4. Create Video Timeline
**Endpoint**: `POST /api/v1/video/temporal/timeline`

```bash
curl -X POST http://localhost:8000/api/v1/video/temporal/timeline \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "granularity": "medium"
  }'
```

**Granularity Options**:
- `"fine"`: Every 5-10 seconds
- `"medium"`: Every 30-60 seconds (default)
- `"coarse"`: Major section boundaries

**Response**:
```json
{
  "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "granularity": "medium",
  "timeline": [
    {
      "timestamp": "0:00",
      "section_title": "Introduction",
      "description": "Overview of the API",
      "key_visuals": ["Title slide", "Speaker"],
      "key_audio": "Welcome to the API tutorial"
    },
    {
      "timestamp": "2:00",
      "section_title": "Setup",
      "description": "Environment configuration"
    }
  ]
}
```

---

### 5. Compare Segments
**Endpoint**: `POST /api/v1/video/temporal/compare-segments`

```bash
curl -X POST http://localhost:8000/api/v1/video/temporal/compare-segments \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "segments": [["1:00", "2:00"], ["3:00", "4:00"], ["5:00", "6:00"]],
    "comparison_focus": "code quality"
  }'
```

**Response**:
```json
{
  "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "segments_compared": 3,
  "comparison_focus": "code quality",
  "comparison": {
    "segments_analyzed": 3,
    "comparisons": [
      {
        "aspect": "Error handling",
        "segment_1": "No error handling",
        "segment_2": "Try-catch blocks added",
        "difference": "Improved robustness"
      }
    ]
  }
}
```

---

### 6. Extract Tutorial Steps
**Endpoint**: `POST /api/v1/video/temporal/tutorial-steps`

```bash
curl -X POST http://localhost:8000/api/v1/video/temporal/tutorial-steps \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ"
  }'
```

**Response**:
```json
{
  "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "steps_count": 5,
  "steps": [
    {
      "step_number": 1,
      "timestamp": "0:30",
      "title": "Install dependencies",
      "instructions": "Run npm install to install packages",
      "code_snippets": ["npm install express"],
      "expected_result": "Packages installed successfully",
      "common_errors": ["Network timeout", "Permission denied"]
    }
  ]
}
```

---

## Structured Output Endpoint

### 7. Analyze with JSON Schema
**Endpoint**: `POST /api/v1/video/analyze/structured`

```bash
curl -X POST http://localhost:8000/api/v1/video/analyze/structured \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "prompt": "Extract all APIs mentioned with their endpoints",
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
            },
            "required": ["name", "endpoint", "method"]
          }
        }
      },
      "required": ["apis"]
    },
    "publish_result": true
  }'
```

**Response**:
```json
{
  "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "structured_result": {
    "apis": [
      {
        "name": "Users API",
        "endpoint": "/api/users",
        "method": "POST"
      },
      {
        "name": "Auth API",
        "endpoint": "/api/auth/login",
        "method": "POST"
      }
    ]
  },
  "schema": {...},
  "published": true,
  "event_id": "event-id-123"
}
```

---

## CloudEvents Publishing Endpoint

### 8. Publish CloudEvent
**Endpoint**: `POST /api/v1/video/publish-event`

```bash
curl -X POST http://localhost:8000/api/v1/video/publish-event \
  -H "Content-Type: application/json" \
  -d '{
    "source": "/video-processor/gemini",
    "event_type": "com.eventrelay.video.analyzed",
    "data": {
      "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
      "summary": "API tutorial video",
      "events": []
    },
    "subject": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "backend": "pubsub"
  }'
```

**Backend Options**:
- `"pubsub"`: Google Cloud Pub/Sub
- `"http"`: HTTP webhook
- `"openwhisk"`: Apache OpenWhisk
- `"file"`: Local file (testing)

**Response**:
```json
{
  "status": "published",
  "event_id": "abc-123-def",
  "backend": "pubsub"
}
```

---

## Python SDK Usage

### Temporal Analysis

```python
from src.integration.temporal_video_analysis import TemporalVideoAnalyzer

analyzer = TemporalVideoAnalyzer()

# Segment analysis
result = await analyzer.analyze_segment(
    "https://youtube.com/watch?v=example",
    "1:30", "3:45", focus="code"
)

# Extract events
events = await analyzer.extract_temporal_events(
    "https://youtube.com/watch?v=example",
    event_types=["code_change", "api_call"]
)

# Timeline
timeline = await analyzer.create_timeline(
    "https://youtube.com/watch?v=example",
    granularity="medium"
)

await analyzer.close()
```

### CloudEvents Publishing

```python
from src.integration.cloudevents_publisher import create_publisher

# Pub/Sub
publisher = create_publisher(backend="pubsub")

# OpenWhisk
publisher = create_publisher(backend="openwhisk")

# HTTP Webhook
publisher = create_publisher(
    backend="http",
    webhook_url="https://example.com/webhook"
)

event_id = await publisher.publish(
    source="/video-analyzer",
    type="com.eventrelay.video.processed",
    data={"video_url": "...", "status": "complete"},
    subject="https://youtube.com/watch?v=example"
)

await publisher.close()
```

### Structured Output

```python
from src.youtube_extension.services.ai.gemini_service import (
    GeminiService, GeminiConfig
)

schema = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "apis": {"type": "array"}
    }
}

config = GeminiConfig(
    response_schema=schema,
    response_mime_type="application/json"
)

service = GeminiService(config)

result = await service.generate_content_async(
    [
        {"text": "https://youtube.com/watch?v=example"},
        {"text": "Extract APIs"}
    ],
    response_schema=schema
)
```

---

## Environment Configuration

```bash
# Required
GEMINI_API_KEY=your_gemini_key

# CloudEvents Backend (choose one)
CLOUDEVENTS_BACKEND=pubsub  # or http, openwhisk, file

# Pub/Sub Backend
GOOGLE_CLOUD_PROJECT=your-project-id
PUBSUB_TOPIC=video-events

# HTTP Webhook Backend
WEBHOOK_URL=https://your-webhook.com/events

# OpenWhisk Backend
OPENWHISK_API_HOST=https://openwhisk.ng.bluemix.net
OPENWHISK_AUTH=username:password
OPENWHISK_NAMESPACE=your-namespace

# File Backend (testing)
EVENTS_FILE_PATH=/tmp/cloudevents.jsonl
```

---

## Common Patterns

### Pattern 1: Extract Events and Publish

```bash
# Extract events with auto-publish
curl -X POST http://localhost:8000/api/v1/video/temporal/events \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=example",
    "event_types": ["code_change"],
    "publish_events": true
  }'
```

### Pattern 2: Structured Analysis with Publishing

```bash
# Analyze with schema and publish result
curl -X POST http://localhost:8000/api/v1/video/analyze/structured \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=example",
    "prompt": "Extract APIs",
    "schema": {...},
    "publish_result": true
  }'
```

### Pattern 3: Timeline + Segment Analysis

```bash
# 1. Get timeline
curl -X POST http://localhost:8000/api/v1/video/temporal/timeline \
  -d '{"video_url": "...", "granularity": "coarse"}'

# 2. Analyze specific segments from timeline
curl -X POST http://localhost:8000/api/v1/video/temporal/segment \
  -d '{
    "video_url": "...",
    "start_time": "2:00",
    "end_time": "5:00"
  }'
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid parameters)
- `500`: Server error (analysis failed)

Error response format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limits

Be aware of:
- Gemini API rate limits (per your API key tier)
- YouTube API quotas (if metadata fetching is enabled)
- Pub/Sub quotas (if using pubsub backend)
- OpenWhisk rate limits (if using openwhisk backend)

---

## Related Documentation

- [Advanced Video Features Guide](ADVANCED_VIDEO_FEATURES.md) - Detailed documentation
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md) - Technical details
- [README.md](../README.md) - Project overview
- [API Reference](API_REFERENCE.md) - Full API documentation

---

## Support

For issues or questions:
1. Check [Advanced Video Features Guide](ADVANCED_VIDEO_FEATURES.md)
2. Review test files for usage examples
3. File an issue in the repository

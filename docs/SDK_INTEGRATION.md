# EventRelay SDK Integration

This document describes the type-safe SDK generation for EventRelay using Stainless.

## Overview

EventRelay provides official SDKs for Python and TypeScript, automatically generated from our OpenAPI specification using [Stainless](https://www.stainless.com). These SDKs provide:

- 🔒 **Type-safe** client libraries with full IDE autocomplete
- 🚀 **Idiomatic** code that feels hand-crafted for each language
- ⚡ **Advanced features** including retries, pagination, and streaming
- 📦 **Easy installation** via PyPI (Python) and npm (TypeScript)

## Quick Start

### Python SDK

```bash
pip install eventrelay-sdk
```

```python
from eventrelay import EventRelay

# Initialize client
client = EventRelay(
    api_key="your-api-key",
    base_url="https://api.uvai.io"  # Optional
)

# Process a video
result = client.videos.process(
    video_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
    language="en"
)

# Check job status
status = client.videos.get_status(job_id=result.job_id)

# Extract events from transcript
events = client.events.extract(
    transcript=status.transcript,
    video_metadata=status.metadata
)

# Dispatch agents
for event in events.events:
    agent = client.agents.dispatch(
        event_type=event.type,
        payload=event.payload
    )
    print(f"Agent {agent.agent_id} dispatched: {agent.status}")
```

### TypeScript SDK

```bash
npm install @groupthinking/eventrelay
```

```typescript
import { EventRelay } from '@groupthinking/eventrelay';

// Initialize client
const client = new EventRelay({
  apiKey: process.env.EVENTRELAY_API_KEY,
  baseURL: 'https://api.uvai.io' // Optional
});

// Process a video
const result = await client.videos.process({
  video_url: 'https://youtube.com/watch?v=dQw4w9WgXcQ',
  language: 'en'
});

// Check job status
const status = await client.videos.getStatus(result.job_id);

// Extract events
const events = await client.events.extract({
  transcript: status.transcript,
  video_metadata: status.metadata
});

// Dispatch agents
for (const event of events.events) {
  const agent = await client.agents.dispatch({
    event_type: event.type,
    payload: event.payload
  });
  console.log(`Agent ${agent.agent_id} dispatched: ${agent.status}`);
}
```

## SDK Features

### Type Safety

Both SDKs provide full type definitions:

**Python:**
```python
from eventrelay.types import VideoProcessJobRequest, VideoJobStatusResponse

request: VideoProcessJobRequest = {
    "video_url": "https://youtube.com/watch?v=...",
    "language": "en",
    "options": {"enable_cache": True}
}
```

**TypeScript:**
```typescript
import type { VideoProcessJobRequest, VideoJobStatusResponse } from '@groupthinking/eventrelay';

const request: VideoProcessJobRequest = {
  video_url: 'https://youtube.com/watch?v=...',
  language: 'en',
  options: { enable_cache: true }
};
```

### Error Handling

SDKs include comprehensive error handling:

```python
from eventrelay import EventRelay, APIError, RateLimitError

try:
    result = client.videos.process(video_url="...")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
```

### Async Support (Python)

```python
import asyncio
from eventrelay import AsyncEventRelay

async def process_video():
    async with AsyncEventRelay(api_key="...") as client:
        result = await client.videos.process(video_url="...")
        return result

asyncio.run(process_video())
```

### Pagination

Both SDKs support automatic pagination:

```python
# Python - auto-pagination
for video in client.videos.list():
    print(f"Video {video.video_id}: {video.title}")

# TypeScript - auto-pagination
for await (const video of client.videos.list()) {
  console.log(`Video ${video.video_id}: ${video.title}`);
}
```

### Streaming

Support for streaming responses:

```python
# Python streaming
for chunk in client.chat.stream(messages=[...]):
    print(chunk.content, end="")
```

## Development

### Generating OpenAPI Spec

The OpenAPI specification is automatically generated from the FastAPI backend:

```bash
python scripts/generate_openapi.py
```

This creates `openapi.yaml` from the FastAPI app routes and Pydantic models.

### Generating SDKs

SDKs are generated using Stainless:

1. **Via Stainless CLI** (requires Stainless account):
```bash
npx stainless generate
```

2. **Via GitHub Actions** (automated):
   - Push changes to `openapi.yaml`
   - GitHub Actions workflow automatically generates and publishes SDKs

### Stainless Configuration

SDK generation is configured in `.stainless.yaml`:

```yaml
sdks:
  python:
    package_name: eventrelay
    output_dir: ./sdks/python
  typescript:
    package_name: "@groupthinking/eventrelay"
    output_dir: ./sdks/typescript
```

### Publishing

#### Python (PyPI)

```bash
cd sdks/python
python -m build
python -m twine upload dist/*
```

#### TypeScript (npm)

```bash
cd sdks/typescript
npm publish --access public
```

## Architecture

### SDK Generation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EventRelay Architecture                          │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  FastAPI Backend │  Pydantic models + routes
│  (Python)        │
└────────┬─────────┘
         │
         │ Auto-generate
         ▼
┌──────────────────┐
│  OpenAPI 3.1     │  openapi.yaml
│  Specification   │
└────────┬─────────┘
         │
         │ Stainless SDK Generator
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Generated SDKs                                │
├─────────────────────────────────────┬───────────────────────────────┤
│  Python SDK                         │  TypeScript SDK               │
│  • Sync & Async clients             │  • Promise-based client       │
│  • Pydantic models                  │  • TypeScript types           │
│  • Type hints                       │  • IntelliSense support       │
│  • Published to PyPI                │  • Published to npm           │
└─────────────────────────────────────┴───────────────────────────────┘
         │                                       │
         │                                       │
         ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     External Applications                            │
│  Developers integrate EventRelay into their apps via SDKs           │
└─────────────────────────────────────────────────────────────────────┘
```

### API Versioning

- **OpenAPI Spec**: Generated from `/api/v1/` routes
- **SDK Version**: Follows semantic versioning (1.0.0)
- **Breaking Changes**: Major version bump (2.0.0)
- **New Features**: Minor version bump (1.1.0)
- **Bug Fixes**: Patch version bump (1.0.1)

## CI/CD Integration

### GitHub Actions Workflow

The `.github/workflows/stainless-sdk.yml` workflow:

1. Triggers on changes to `openapi.yaml` or manual dispatch
2. Validates OpenAPI specification
3. Generates Python and TypeScript SDKs via Stainless
4. Runs tests on generated SDKs
5. Publishes to PyPI and npm (on release tags)

## Testing SDKs

### Python SDK Tests

```bash
cd sdks/python
pip install -e ".[dev]"
pytest tests/
```

### TypeScript SDK Tests

```bash
cd sdks/typescript
npm install
npm test
```

## Troubleshooting

### OpenAPI Spec Issues

If SDK generation fails, validate the OpenAPI spec:

```bash
npm install -g @apidevtools/swagger-cli
swagger-cli validate openapi.yaml
```

### Type Errors

Ensure your FastAPI routes use Pydantic models for request/response types:

```python
@router.post("/videos/process", response_model=ApiResponse[VideoProcessJobResponse])
async def process_video(request: VideoProcessJobRequest):
    ...
```

### Stainless Configuration

Verify `.stainless.yaml` configuration:

```bash
npx stainless validate-config
```

## Resources

- [Stainless Documentation](https://www.stainless.com/docs)
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)
- [FastAPI OpenAPI Support](https://fastapi.tiangolo.com/advanced/extending-openapi/)
- [EventRelay API Documentation](https://api.uvai.io/docs)

## Support

- **Issues**: [GitHub Issues](https://github.com/groupthinking/EventRelay/issues)
- **Discussions**: [GitHub Discussions](https://github.com/groupthinking/EventRelay/discussions)
- **Email**: team@uvai.com

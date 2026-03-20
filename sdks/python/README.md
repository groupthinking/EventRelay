# EventRelay Python SDK

Typed Python client for the EventRelay API. Generated from the FastAPI OpenAPI schema and aligned with Stainless configuration.

## Installation

```bash
pip install .
```

## Usage

```python
from eventrelay_sdk.client import EventRelayClient, TranscriptActionRequest

client = EventRelayClient(base_url="https://api.eventrelay.io", api_key="your-key")

health = client.health()
result = client.transcript_action(
    TranscriptActionRequest(video_url="https://youtu.be/auJzb1D-fag")
)
```

## Regenerate with Stainless

```bash
python ../../scripts/export_openapi.py
npx stainless generate --config ../../stainless.config.ts
```

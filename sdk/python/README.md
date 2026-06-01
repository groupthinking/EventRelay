# EventRelay Python SDK

Type-safe Python client for the [EventRelay API](https://github.com/groupthinking/EventRelay).

Generated via [Stainless](https://stainlessapi.com) from the EventRelay OpenAPI spec.

## Installation

```bash
pip install eventrelay-sdk
```

## Quick Start

```python
from eventrelay_sdk import EventRelayClient

client = EventRelayClient(
    api_key="your-api-key",  # optional; reads EVENTRELAY_API_KEY from env
    base_url="https://api.uvai.io",  # optional; defaults to production
)

# Process a YouTube video
job = client.videos.process(video_url="https://www.youtube.com/watch?v=auJzb1D-fag")
print(job.job_id)

# Poll status
status = client.videos.get_status(job_id=job.job_id)
print(status.status)

# Extract events from transcript
events = client.events.extract(transcript="The speaker discussed building a React app...")
for event in events.events:
    print(event.type, event.title)

# Dispatch agents for events
dispatch = client.agents.dispatch(events=[e.model_dump() for e in events.events])
for execution in dispatch.executions:
    print(execution.agent_type, execution.status)
```

## Async Usage

```python
import asyncio
from eventrelay_sdk import AsyncEventRelayClient

async def main():
    async with AsyncEventRelayClient(api_key="...") as client:
        job = await client.videos.process(
            video_url="https://www.youtube.com/watch?v=auJzb1D-fag"
        )
        print(job.job_id)

asyncio.run(main())
```

## Resources

- **`client.videos`** — Process YouTube videos, poll job status, manage video library
- **`client.events`** — Extract structured events from transcripts
- **`client.agents`** — Dispatch and monitor AI agents
- **`client.transcript`** — Transcript-action workflow
- **`client.chat`** — Conversational AI assistant
- **`client.health`** — Health and readiness checks

## Publishing to PyPI

```bash
cd sdk/python
python -m build
twine upload dist/*
```

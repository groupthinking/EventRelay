# EventRelay TypeScript SDK

Type-safe TypeScript/JavaScript client for the [EventRelay API](https://github.com/groupthinking/EventRelay).

Generated via [Stainless](https://stainlessapi.com) from the EventRelay OpenAPI spec.

## Installation

```bash
npm install @eventrelay/sdk
# or
yarn add @eventrelay/sdk
```

## Quick Start

```ts
import { EventRelayClient } from "@eventrelay/sdk";

const client = new EventRelayClient({
  apiKey: "your-api-key",       // optional; reads EVENTRELAY_API_KEY from env
  baseUrl: "https://api.uvai.io",  // optional; defaults to production
});

// Process a YouTube video
const job = await client.videos.process({
  video_url: "https://www.youtube.com/watch?v=auJzb1D-fag",
});
console.log(job.job_id);

// Poll status
const status = await client.videos.getStatus(job.job_id);
console.log(status.status);

// Extract events from transcript
const events = await client.events.extract({
  transcript: "The speaker discussed building a React app...",
});
for (const event of events.events) {
  console.log(event.type, event.title);
}

// Dispatch agents for events
const dispatch = await client.agents.dispatch({ events: events.events });
for (const execution of dispatch.executions) {
  console.log(execution.agent_type, execution.status);
}
```

## Resources

| Resource | Description |
|---|---|
| `client.videos` | Process YouTube videos, poll job status, manage video library |
| `client.events` | Extract structured events from transcripts |
| `client.agents` | Dispatch and monitor AI agents |
| `client.transcript` | Transcript-action workflow |
| `client.chat` | Conversational AI assistant |
| `client.health` | Health and readiness checks |

## Building

```bash
npm install
npm run build
```

## Publishing to npm

```bash
cd sdk/typescript
npm run build
npm publish --access public
```

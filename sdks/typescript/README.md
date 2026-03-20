# EventRelay TypeScript SDK

Type-safe client for the EventRelay API. This package can be generated automatically with Stainless from `openapi/eventrelay.openapi.json` and includes a lightweight hand-authored client for the core video-to-software workflow.

## Usage

```bash
npm install eventrelay-sdk
```

```ts
import { EventRelayClient } from "eventrelay-sdk";

const client = new EventRelayClient({
  baseUrl: "https://api.eventrelay.io",
  apiKey: process.env.EVENTRELAY_API_KEY,
});

const health = await client.health();
const result = await client.transcriptAction({ video_url: "https://youtu.be/auJzb1D-fag" });
```

## Regenerating with Stainless

1. Export the OpenAPI schema:
   ```bash
   python ../../scripts/export_openapi.py
   ```
2. Generate SDKs (requires `npx stainless`):
   ```bash
   npx stainless generate --config ../../stainless.config.ts
   ```
3. Build:
   ```bash
   npm run build
   ```

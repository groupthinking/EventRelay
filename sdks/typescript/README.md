# EventRelay TypeScript SDK

> **Note**: This SDK is automatically generated from the EventRelay OpenAPI specification using [Stainless](https://www.stainless.com).

## Installation

```bash
npm install @groupthinking/eventrelay
```

Or with yarn:

```bash
yarn add @groupthinking/eventrelay
```

## Quick Start

```typescript
import { EventRelay } from '@groupthinking/eventrelay';

// Initialize client
const client = new EventRelay({
  apiKey: process.env.EVENTRELAY_API_KEY,
  baseURL: 'https://api.uvai.io'
});

// Process a YouTube video
const result = await client.videos.process({
  video_url: 'https://youtube.com/watch?v=...',
  language: 'en'
});

console.log(`Job ID: ${result.job_id}`);
```

## Features

- ✅ **Type-safe** - Full TypeScript types and IntelliSense
- ✅ **Promise-based** - Modern async/await API
- ✅ **Automatic retries** - Built-in retry logic with exponential backoff
- ✅ **Pagination** - Auto-pagination for list endpoints
- ✅ **Streaming** - Support for streaming responses
- ✅ **Error handling** - Comprehensive exception hierarchy

## Documentation

Full documentation is available at:
- [SDK Integration Guide](../../docs/SDK_INTEGRATION.md)
- [Stainless Setup](../../docs/STAINLESS_SETUP.md)
- [API Reference](https://api.uvai.io/docs)

## Examples

See [examples/sdk_usage_typescript.ts](../../examples/sdk_usage_typescript.ts) for comprehensive usage examples.

## Development

This SDK is generated automatically. Do not edit the generated code directly.

To regenerate:

```bash
# From repository root
python scripts/generate_openapi.py
stainless generate --language typescript --output ./sdks/typescript
```

## Support

- **Issues**: [GitHub Issues](https://github.com/groupthinking/EventRelay/issues)
- **Discussions**: [GitHub Discussions](https://github.com/groupthinking/EventRelay/discussions)

## License

MIT License - see [LICENSE](../../LICENSE) for details.

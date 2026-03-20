# EventRelay Python SDK

> **Note**: This SDK is automatically generated from the EventRelay OpenAPI specification using [Stainless](https://www.stainless.com).

## Installation

```bash
pip install eventrelay-sdk
```

## Quick Start

```python
from eventrelay import EventRelay

# Initialize client
client = EventRelay(
    api_key="your-api-key",
    base_url="https://api.uvai.io"
)

# Process a YouTube video
result = client.videos.process(
    video_url="https://youtube.com/watch?v=...",
    language="en"
)

print(f"Job ID: {result.job_id}")
```

## Features

- ✅ **Type-safe** - Full type hints and IDE autocomplete
- ✅ **Async support** - Both sync and async clients
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

See [examples/sdk_usage_python.py](../../examples/sdk_usage_python.py) for comprehensive usage examples.

## Development

This SDK is generated automatically. Do not edit the generated code directly.

To regenerate:

```bash
# From repository root
python scripts/generate_openapi.py
stainless generate --language python --output ./sdks/python
```

## Support

- **Issues**: [GitHub Issues](https://github.com/groupthinking/EventRelay/issues)
- **Discussions**: [GitHub Discussions](https://github.com/groupthinking/EventRelay/discussions)

## License

MIT License - see [LICENSE](../../LICENSE) for details.

## 2024-05-15 - Prevent Event Loop Blocking in Third-Party Requests

**Learning:** Synchronous HTTP libraries like `requests` can block the entire async event loop in Python, preventing background tasks and other async calls from progressing. This is especially dangerous when API requests have timeouts up to 60 seconds.
**Action:** Use async libraries like `httpx.AsyncClient` inside `async def` methods instead of `requests` whenever making outgoing HTTP calls to ensure the event loop yields correctly.

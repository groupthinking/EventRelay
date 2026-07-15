## 2026-07-12 - Refactored complex stream handler
**Learning:** Complex route handlers for streams can grow large, making them difficult to maintain. Inline functions like `schedulePostProcessing` and inline strategy implementations (Gemini vs Backend) add significant indentation and cognitive load.
**Action:** Extract inline functions to the top level, and separate different execution strategies into top-level helper functions, drastically reducing the size of the route handler itself while maintaining the exact same logic and asynchronous behavior.

## 2026-07-13 - Optimize batch query execution using asyncio.gather
**Learning:** Using conditional `executemany` checks in batch processing (especially when mocked or falling back to sequential loops) can create N+1 execution bottlenecks. Calling `asyncio.gather` for all grouped queries avoids sequential blocking and preserves expected return types while maintaining centralized logging and metrics.
**Action:** Always prefer `asyncio.gather` over `executemany` or sequential looping for parallelizing independent queries in async database layers within this codebase.

## 2026-07-13 - Pre-compiled regexes in database_optimizer.py
**Learning:** Frequent query analysis paths in `database_optimizer.py` were compiling identical regular expressions for parameter sanitization (`_get_query_hash`) and SQL pattern detection (`_get_query_pattern`) inline via `re.sub` and `re.search` on every query execution. This resulted in unnecessary compilation overhead during high-throughput database interactions.
**Action:** Extract all regular expressions used in hot paths to module-level `re.compile()` constants. When making modifications to high-frequency loop routines, look for string literal regex operations and lift them into module scope for better internal caching and execution speeds.

## 2026-07-15 - Prevent Event Loop Blocking in Third-Party Requests

**Learning:** Synchronous HTTP libraries like `requests` can block the entire async event loop in Python, preventing background tasks and other async calls from progressing. This is especially dangerous when API requests have timeouts up to 60 seconds.
**Action:** Use async libraries like `httpx.AsyncClient` inside `async def` methods instead of `requests` whenever making outgoing HTTP calls to ensure the event loop yields correctly.

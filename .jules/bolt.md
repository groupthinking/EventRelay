## 2026-07-12 - Refactored complex stream handler
**Learning:** Complex route handlers for streams can grow large, making them difficult to maintain. Inline functions like `schedulePostProcessing` and inline strategy implementations (Gemini vs Backend) add significant indentation and cognitive load.
**Action:** Extract inline functions to the top level, and separate different execution strategies into top-level helper functions, drastically reducing the size of the route handler itself while maintaining the exact same logic and asynchronous behavior.

## 2026-07-13 - Optimize batch query execution using asyncio.gather
**Learning:** Using conditional `executemany` checks in batch processing (especially when mocked or falling back to sequential loops) can create N+1 execution bottlenecks. Calling `asyncio.gather` for all grouped queries avoids sequential blocking and preserves expected return types while maintaining centralized logging and metrics.
**Action:** Always prefer `asyncio.gather` over `executemany` or sequential looping for parallelizing independent queries in async database layers within this codebase.

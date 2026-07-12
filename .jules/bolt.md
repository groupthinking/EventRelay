## 2026-07-12 - Refactored complex stream handler
**Learning:** Complex route handlers for streams can grow large, making them difficult to maintain. Inline functions like `schedulePostProcessing` and inline strategy implementations (Gemini vs Backend) add significant indentation and cognitive load.
**Action:** Extract inline functions to the top level, and separate different execution strategies into top-level helper functions, drastically reducing the size of the route handler itself while maintaining the exact same logic and asynchronous behavior.

## 2026-07-12 - Consistently use asyncio.gather over sequential iterations
**Learning:** In `database_optimizer.py`, attempting to use `executemany` for batch processing can inadvertently introduce sequential bottlenecks (N+1 execution) if the fallback implementation simply loops over queries instead of executing them concurrently.
**Action:** Use `asyncio.gather` consistently for all batch queries over trying to use `executemany`. This preserves expected return types, executes centralized logging/metrics logic embedded in individual query methods, and resolves sequential execution bottlenecks.

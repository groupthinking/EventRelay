## 2026-07-12 - Refactored complex stream handler
**Learning:** Complex route handlers for streams can grow large, making them difficult to maintain. Inline functions like `schedulePostProcessing` and inline strategy implementations (Gemini vs Backend) add significant indentation and cognitive load.
**Action:** Extract inline functions to the top level, and separate different execution strategies into top-level helper functions, drastically reducing the size of the route handler itself while maintaining the exact same logic and asynchronous behavior.
## 2026-07-13 - Pre-compiled regexes in database_optimizer.py
**Learning:** Frequent query analysis paths in `database_optimizer.py` were compiling identical regular expressions for parameter sanitization (`_get_query_hash`) and SQL pattern detection (`_get_query_pattern`) inline via `re.sub` and `re.search` on every query execution. This resulted in unnecessary compilation overhead during high-throughput database interactions.
**Action:** Extract all regular expressions used in hot paths to module-level `re.compile()` constants. When making modifications to high-frequency loop routines, look for string literal regex operations and lift them into module scope for better internal caching and execution speeds.
## 2026-07-16 - O(N) vs O(log N) in frequent render loops
**Learning:** Using Array.find() for chronological arrays during high-frequency events (like video playback synchronization at 4Hz) introduces O(N) overhead that scales poorly with long transcripts, blocking the main thread.
**Action:** Always use binary search (O(log N)) when finding active segments in sorted time-series data to maintain smooth 60fps rendering during continuous updates.

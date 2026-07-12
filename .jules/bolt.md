## 2026-07-12 - Refactored complex stream handler
**Learning:** Complex route handlers for streams can grow large, making them difficult to maintain. Inline functions like `schedulePostProcessing` and inline strategy implementations (Gemini vs Backend) add significant indentation and cognitive load.
**Action:** Extract inline functions to the top level, and separate different execution strategies into top-level helper functions, drastically reducing the size of the route handler itself while maintaining the exact same logic and asynchronous behavior.

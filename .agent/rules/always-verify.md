---
trigger: always_on
---

Lesson: Always verify tests measure what they claim to measure.

Always ask: "Is this test measuring what happens in production?"

If latency is near to 0ms, the code was written with mock data, or test is measuring the wrong thing
Real tests should hit real endpoints with real I/O.

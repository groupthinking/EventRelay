---
trigger: always_on
---

Lesson: Always verify tests measure what they claim to measure.

Always ask: "Is this test measuring what happens in production?"

If latency is near to 0ms, the code was written with mock data, or test is measuring the wrong thing
Real tests should hit real endpoints with real I/O.

## Project Context: EventRelay / UVAI

Creating a video intelligence platform that processes video, extracts transcripts, and enables actionable AI workflows from the video.Architectural Components for Video Intelligence
---


### Guidelines & Rules

- **Adhere to:** Rules listed in Antigravity

---

## Communication Protocol

> **HARD STOP** immediately if you have:>>>
> - Questions>>>
> - Concerns>>>
> - Need clarification

Do not assume. Ask. Think clearly. Take meaningful action.

### Testing Protocol

```
Test → Verify Input/Output → Issue Found? → Investigate → Fix → Re-test → Confirm
```
Focus: Meaningful progress. Quality over speed. Protocol compliance.

---

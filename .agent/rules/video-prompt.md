---
trigger: model_decision
description: PRIOR TO PROCESSING A VIDEO
---

# Video Processing Rule

> **When to use**: Before processing any video URL or video content analysis task.

## Quick Reference

**Full catalog**: `docs/video-prompts-catalog.md`

## Pre-Processing Checklist

1. **Identify Input Type**
   - YouTube URL → Use transcript extraction + multimodal analysis
   - Local video file → Use Gemini native video understanding
   - Video with code → Prioritize CSDAA agent patterns

2. **Select Agent Pattern**
   | Task Type | Primary Agent | Secondary |
   |-----------|---------------|-----------|
   | Transcription | VTTA | - |
   | Code extraction | CSDAA | VTTA |
   | Full analysis | OFSA | VTTA + CSDAA |

3. **Memory Architecture**
   - Working Memory: Current prompt context
   - Session Memory: Conversation history (SessionManager)
   - Long-Term: User preferences, past analyses (LongTermMemoryDB)

## Core Agents

### VTTA (Video Transcription & Timing Agent)

- Capture all dialogue with timestamps
- Note subject shifts and key events
- Tools: Transcript Generation

### CSDAA (Code Structure & Diff Analysis Agent)

- Extract terminal commands and outputs
- Document error-handling sequences
- Tools: Terminal Output Capture, Diff Analysis

### OFSA (Output Formatting & Synthesis Agent)

- Synthesize VTTA + CSDAA outputs
- Maintain chronological order
- Tools: Markdown Engine, Mirrored Version Output

## Gemini Video Processing (Preferred)

```typescript
// Direct multimodal analysis - no download required
const videoFile = await ai.files.upload({
  file: createPartFromUri(videoUrl, "video/mp4"),
});

const result = await model.generateContent([
  videoFile,
  "Analyze this video and extract: transcript, key concepts, code snippets, actionable steps",
]);
```

## Fallback: yt-dlp Extraction

```bash
# Only if direct analysis fails
yt-dlp --no-download --write-auto-sub --sub-lang en --skip-download "$VIDEO_URL"
```

## Output Structure

```markdown
## Video Analysis: [Title]

### Metadata

- Duration: X:XX
- Source: [URL]
- Analyzed: [Timestamp]

### Transcript (Timestamped)

[00:00] Opening...
[00:30] Main content...

### Key Technical Operations

- Commands executed
- Code changes
- Error handling

### Actionable Insights

1. Step-by-step replication guide
2. Required tools/dependencies
3. Potential pitfalls
```

## Anti-Patterns

❌ **Don't** skip transcript generation for code-heavy videos
❌ **Don't** assume video content from title alone
❌ **Don't** use yt-dlp when Gemini direct analysis is available
❌ **Don't** proceed without establishing memory context

## See Also

- `docs/video-prompts-catalog.md` - Full prompt catalog (13 sections)
- `docs/hallucination_hazard_empty_transcript.md` - Error handling patterns

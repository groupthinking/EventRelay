---
description: Process video URL through standardized UVAI pipeline with enforced agent routing
---

# /video-analysis Workflow

> **Enforced Pipeline**: All video processing MUST follow this workflow. No ad-hoc configuration.

## Prerequisites

- Video URL (YouTube, direct, or GitHub asset)
- Reference: `docs/video-prompts-catalog.md`

## Workflow Steps

// turbo-all

### Step 1: Input Validation

Validate the video URL format and detect source type:

```bash
# Check if URL is accessible
curl -sI "$VIDEO_URL" | head -1
```

**Classification:**

- YouTube: `youtube.com` or `youtu.be`
- GitHub Asset: `github.com/user-attachments/assets`
- Direct: All other video URLs

### Step 2: Route to Agent Pipeline

Based on the rules in `.agent/rules/video-prompt.md`:

| Task Type          | Agent Chain         | Output                     |
| ------------------ | ------------------- | -------------------------- |
| Transcription Only | VTTA                | Timestamped transcript     |
| Code Extraction    | VTTA → CSDAA        | Transcript + code/commands |
| Full Analysis      | VTTA → CSDAA → OFSA | Complete mirrored output   |

### Step 3: Execute VTTA (Video Transcription & Timing Agent)

```markdown
## VTTA Instructions

Analyze the video at: $VIDEO_URL

1. Transcribe ALL spoken content with timestamps [MM:SS]
2. Note major topic transitions
3. Capture key terminology and proper nouns
4. Flag any code demonstrations or terminal usage

Output format:

- Timestamped transcript blocks
- Topic markers for major shifts
- Technical operation flags
```

### Step 4: Execute CSDAA (Code Structure & Diff Analysis Agent)

```markdown
## CSDAA Instructions

Using VTTA output, extract technical content:

1. All terminal commands executed
2. All code snippets shown/typed
3. File paths and directory structures
4. Error messages and their resolutions
5. Dependencies and package installations

Output format:

- Command logs with context
- Code blocks with language tags
- Error→Fix pairs
```

### Step 5: Execute OFSA (Output Formatting & Synthesis Agent)

```markdown
## OFSA Instructions

Synthesize VTTA + CSDAA outputs into actionable format:

1. Maintain strict chronological order
2. Interleave transcript with technical operations
3. Generate step-by-step replication guide
4. List all required tools/dependencies
5. Document potential pitfalls observed

Output format: AgenticOutput JSON schema
```

### Step 6: Validate Output

Ensure output matches `AgenticOutput` schema:

```typescript
interface AgenticOutput {
  summary: {
    title: string;
    description: string;
    keyInsights: string[];
  };
  generatedWorkflow: {
    steps: WorkflowStep[];
  };
  codeArtifacts?: CodeArtifact[];
}
```

### Step 7: Store Results

- Save to job store via orchestrator
- Update job status to COMPLETED
- Format output via `formatAgenticOutput()`

## Memory Context

Before processing, retrieve from LongTermMemoryDB:

- User's previous video analysis preferences
- Common patterns from past jobs
- Tool efficiency constraints

After processing, store to LongTermMemoryDB:

- New facts discovered (technologies, patterns)
- Tool performance metrics
- User preference signals

## Error Handling

| Error            | Recovery                                                 |
| ---------------- | -------------------------------------------------------- |
| Download fails   | Fallback to yt-dlp with `--no-download --write-auto-sub` |
| Empty transcript | See `docs/hallucination_hazard_empty_transcript.md`      |
| Analysis timeout | Chunk video, process segments                            |
| Invalid output   | Re-run OFSA with explicit schema                         |

## Anti-Patterns (BLOCKED)

❌ Skipping VTTA for any video processing
❌ Generating code without CSDAA extraction
❌ Ad-hoc output formats (must use AgenticOutput)
❌ Processing without memory context retrieval

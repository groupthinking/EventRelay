# ChatGPT Export — Video Intelligence / see-script-ship

**Source:** ChatGPT conversation export saved to `~/Downloads/chatgpt_conversation_export`
**Exported (UTC):** 2026-06-16T14:11:46Z
**Filed into EventRelay:** 2026-06-16

This folder is **reference material**, not executable code. It captures a ChatGPT
thread that turns an Apple WWDC26 session ("Build real-time apps and services with
gRPC and Swift", https://developer.apple.com/videos/play/wwdc2026/265/) into a worked
example of the **video → buildable-project** pipeline that EventRelay / see-script-ship
is built to perform.

## Contents

- `chatgpt_conversation_export_2026-06-16.zip` — master archive (faithful backup of the original download).
- `conversation-current-thread.md` — readable copy of the full thread (with mermaid diagrams).
- `assets/image.png` — the architecture screenshot supplied in the chat.

The original `.zip` also contains `conversation-current-thread.json`, `manifest.json`,
and `manifest.sha256.txt`. The original download's `assets/WWDC26 gRPC with Swift.txt`
(WWDC transcript) is preserved inside the zip.

## Why it's relevant to EventRelay

The thread proposes a first-class **video intelligence** capability:

> Take a video URL, profile URL, transcript, or screenshot context and convert it into
> a locked software blueprint.

Pipeline: `video → transcript → protocol/requirement extraction → architecture diagram → task graph → repo scaffold → testable deployment plan`.

### Proposed contract (`video_intelligence.skill.ts`)

```ts
export type VideoSourceKind =
  | "youtube" | "apple_developer" | "profile"
  | "webpage" | "manual_transcript" | "screenshot_context";

export interface VideoIntelligenceInput {
  sourceKind: VideoSourceKind;
  url?: string;
  transcript?: string;
  screenshotNotes?: string;
  userGoal: "explain" | "diagram" | "blueprint" | "build" | "compare";
  preferredOutput?: "markdown" | "json" | "mermaid" | "task_graph";
}

export interface VideoIntelligenceOutput {
  sourceSummary: string;
  confirmedFacts: string[];
  inferredIdeas: string[];
  architectureDiagram: string;
  projectBlueprint: {
    appType: string;
    frontend?: string[]; backend?: string[]; dataLayer?: string[];
    protocols?: string[]; deployment?: string[];
  };
  taskGraph: Array<{ id: string; title: string; dependsOn: string[]; outputContract: string }>;
  missingDetails: string[];
  validationChecklist: string[];
}
```

### Proposed structure (suggestion from the thread — NOT yet created)

```
/providers/video/apple-developer-provider.ts
/providers/video/youtube-provider.ts
/packages/video-intelligence
/packages/prompt-compiler
/packages/blueprint-lock
/packages/task-graph
```

Core principle the thread highlights: just as gRPC's `.proto` is a contract that
services pass through before any networking code, EventRelay's **Agent Lock** should be
the contract that AI software generation passes through first — "no vague execution;
everything passes through a contract first."

## Integrity note

The original export's `manifest.json` lists a `README.md` (441 bytes) as an included
file, but that file is **missing from the saved download** (`~/Downloads/chatgpt_conversation_export`).
All other listed files were verified — their SHA-256 hashes match the manifest:
- `assets/image.png` — a11d52ad…
- `assets/WWDC26 gRPC with Swift.txt` — 64fbcaa9…
- `conversation-current-thread.md` — a6822a3f…
- `conversation-current-thread.json` — abe2e601…

## Proposed next steps (not executed — needs your review)

1. Scaffold `packages/video-intelligence` with the `VideoIntelligenceInput/Output`
   types above as the public contract.
2. Add `providers/video/{apple-developer,youtube}-provider.ts` implementing a shared
   transcript-extraction interface.
3. Stub `packages/{prompt-compiler,blueprint-lock,task-graph}` as contract boundaries.

These would introduce new TypeScript code into the repo, so per ops discipline they are
left as a proposal for your explicit review rather than auto-generated.

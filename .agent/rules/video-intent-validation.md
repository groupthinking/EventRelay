---
trigger: model_decision
description: Before processing ANY video
---

# Intent-Driven Video Action Framework

## Core Principle

Before processing ANY video, ask:

1. **What is the actionable outcome?** - What workflow/code/documentation will be generated?
2. **Can this video produce that outcome?** - Does it contain demonstrable, replicable steps?
3. **Who are the sub-agents and what are their contracts?** - Clear task delegation with expected outputs

## Video Validation Checklist

Before dispatching a job, verify:

- [ ] Video contains **demonstrable workflow** (not just entertainment)
- [ ] **Technical content** is present (code, config, or process)
- [ ] Actions are **replicable** (commands, clicks, procedures)
- [ ] **Clear outcome** exists that system can generate

## NEVER Download Videos

The UVAI platform operates via **API-first** approach:

- ❌ NO `yt-dlp` or video downloading
- ❌ NO local file storage for video/audio
- ✅ YES: Google Video Intelligence API (URL analysis)
- ✅ YES: Gemini multimodal API (direct URL processing)
- ✅ YES: Claude Vision API (frame-by-frame analysis)

## Invalid Video Examples

These should be **rejected** at intake:

- Music videos (no actionable steps)
- Entertainment content (movies, TV clips)
- Videos without technical demonstration
- Placeholder test URLs (e.g., Rick Roll)

## Valid Video Examples

These should be **accepted**:

- Tutorials: "How to deploy to Cloud Run"
- Demos: "Building a REST API with FastAPI"
- Walkthroughs: "Setting up Firebase Data Connect"
- Conference talks with code demonstrations

## Job Contract Structure

```typescript
interface JobContract {
  // 1. INTENT
  intent: {
    desiredOutcome: string; // "Replicate the deployment workflow"
    successMetrics: string[]; // ["Generate valid Dockerfile", "Steps executable"]
  };

  // 2. VALIDATION (Before dispatch)
  videoValidation: {
    hasActionableContent: boolean;
    contentType: "tutorial" | "demo" | "walkthrough" | "presentation";
    estimatedSteps: number;
    canGenerateWorkflow: boolean;
  };

  // 3. AGENT ASSIGNMENT
  agentContracts: {
    agentId: "VTTA" | "CSDAA" | "OFSA";
    task: string;
    expectedOutput: string;
    deadline: Date;
  }[];

  // 4. TRACKING
  tracking: {
    dispatchedAt: Date;
    status: "pending" | "in_progress" | "completed" | "failed";
    communications: AuditEntry[];
  };
}
```

## Delegation Best Practices (Eisenhower Matrix)

1. **Focus on outcomes, not just tasks** - Define what success looks like
2. **Balance autonomy with guidance** - Give agents freedom but clear boundaries
3. **Document all dispatched contracts** - Audit trail in `job_event` table
4. **Track progress against metrics** - Verify each agent's output meets contract

## When Unclear, Ask NotebookLM

Use the NotebookLM MCP to:

- Clarify ambiguous requirements
- Cross-reference against existing documentation
- Validate assumptions before proceeding
- Get domain knowledge for unfamiliar topics
---
trigger: always_on
---

https://github.com/groupthinking/EventRelay.git

# EventRelay Project — CURRENT Work Session

**Project:** `dev/projects/EventRelay` (Antigravity)
**Priority:** Correctness over velocity (YOLO Ultra Mode)
START NOW /yolo-claude.md

**Session Duration:** 5 hours focused work

---

## Project Context: EventRelay / UVAI

Creating a video intelligence platform that processes video, extracts transcripts, and enables actionable AI workflows from the video.Architectural Components for Video Intelligence

Real limitations involve multi-modal video input (beyond YouTube) and low-latency edge cases. Incorporating streaming and multi-modal training architectures, like CLIP or MediaPipe, would be next steps. Start here: ai-edge-torch, accessible through gcp project - just1-482108, request api when ready.

Think:
**NotebookLM Copilot:** [https://notebooklm.google.com/notebook/20b0b5c2-1eb8-4955-bee5-6cac10fdefb2](https://notebooklm.google.com/notebook/20b0b5c2-1eb8-4955-bee5-6cac10fdefb2)

Should We Integrate These Repositories?

Repository\

NVIDIA-AI-IOT/deepstream_tao_apps Yes DeepStream is ideal for video input pipelines, object detection, and real-time AI event streaming.

NVIDIA/DALI Yes DALI specializes in data loading and augmentation pipelines for video, perfect for optimizing inputs/platform scalability.

NVIDIA-AI-IOT/inference_builder Case-Specific Use to deploy pipeline-ready, scalable models depending on real-time deployment speed requirements.

---

EventRelay is well-suited to form the basis of a video intelligence platform but would greatly benefit from:
Expanding Modalities
Leveraging repositories like DALI and DeepStream can enable edge-case and non-YouTube source video processing (security, enterprise feeds).

High-Performance Inference
The inference_builder repository can manage real-time video data at scale, notably for rapid-trigger action workflows.

Enhanced NLP Pipelines
Integrating voicevibe may augment the transcription and voice-processing layers, ensuring Agent-Orchestration includes audio (e.g. task delegation in meetings).


## Phase 1: Verification & Testing

### Immediate Actions

- [ ] Run **actual tests WITHOUT mocking inputs** on all work completed to this point
- [ ] Evaluate test results thoroughly
- [ ] If issues arise → **Investigate root cause → Implement fix → Re-test**
- [ ] Do not proceed until current work is verified functional

### Testing Protocol

```
Test → Verify Input/Output → Issue Found? → Investigate → Fix → Re-test → Confirm
```

---

## Phase 2: Organization & Setup

- [ ] Review current todo/task list — Is it accurate? Does it need updates?
- [ ] Clear unused MCP tools from workspace
- [ ] Download and test **Google Stitch MCP**
- [ ] Download and test **Google NotebookLM MCP**


### Project Archives

- **Old project files:** `/Users/garvey/arch/action-genai-video-issue-analyzer`
  - Pull any previously worked files as needed

### Guidelines & Rules

- **Follow:** `/Users/garvey/.gemini/antigravity/knowledge`
- **Adhere to:** Rules listed in Antigravity

---

## Communication Protocol

> **HARD STOP** immediately if you have:>>>
>
> - Questions>>>
> - Concerns>>>
> - Need for clarification

Do not assume. Ask. Think clearly. Take meaningful action.

---

## Execution Order

1. ✅ Follow protocols correctly
2. ✅ Test current work (no mocks)
3. ✅ Verify → Fix any issues
4. ✅ Review/update todo list
5. ✅ Organize workspace (clear unused MCPs)
6. ✅ Download & test new MCPs
7. ✅ Review competitor repos
8. ✅ Continue remaining todo items
9. ✅ Address any queued ARM64/x86_64 fixes

---

_Focus: Meaningful progress. Quality over speed. Protocol compliance._

---

## 📋 TASK TODO LIST — Current State

### ✅ COMPLETED: Phase 0 — Define YOLO Ultra Mode

Document what YOLO Ultra Mode actually means (correctness over velocity)

List protocol violations from previous session

Establish operating rules for this session

### ⏸️ IN PROGRESS: Phase 1 — MCP Tool Audit & Setup

- [] List all available MCP servers and their purposes
- [] Identify which tools are relevant vs. unused — **NO ACTION TAKEN YET**
- [ ] **Test Google Stitch MCP**
- Read setup docs: [https://stitch.withgoogle.com/docs/mcp/setup](https://stitch.withgoogle.com/docs/mcp/setup)
- Verify connection and test a simple prompt
- Document capabilities for frontend design delegation
- - [ ] **Test NotebookLM MCP**
  - Check if already installed and connected
  - Run a test research query
  - Document as "Claude's Copilot" for research delegation

### 🔲 NOT STARTED: Phase 2 — Reference Research & Market Analysis

- [ ] Explore existing reference projects:
- `/Users/garvey/Vision-Agents` — understand structure
- `/Users/garvey/Dev/projects/video-to-learning-app` — analyze approach
- Check moved project: `/Users/garvey/arch/action-genai-video-issue-analyzer`
  - Video intelligence platform UI patterns
  - Conversion marketing approaches
  - Find actual terminal screenshots
  - Identify data-dense dashboard patterns
  - Document applicable UI principles

### 🔲 NOT STARTED: Phase 3 — Functional Verification (Remaining)

- [ ] Submit a real non-music video
- [ ] Verify agent workflow output is produced
- [ ] Document the complete flow with evidence

### 🔲 NOT STARTED: Phase 4 — Design Rebuild with Stitch

- [ ] Create design brief based on research
- [ ] Use Google Stitch MCP for frontend design
- [ ] Import and integrate Stitch output
- [ ] Verify responsive design (mobile + desktop)
- [ ] Compare against competitor references

### 🔲 NOT STARTED: Phase 5 — Production Sandbox Testing

- [ ] Run full application in production-like environment
- [ ] Test all features end-to-end
- [ ] Document any failures and fixes
- [ ] Only mark complete when all tests pass

---

## Session Protocol Reminders

Rule Meaning**YOLO Ultra Mode**Move slow, promote correctness over velocity**Never skip validation**Test theories before committing**Research before executing**Use NotebookLM as copilot**Sub-agents**Create for specific tasks

### Key Resources

- **NotebookLM Copilot:** [https://notebooklm.google.com/notebook/20b0b5c2-1eb8-4955-bee5-6cac10fdefb2]
- **Stitch for Design:** [https://stitch.withgoogle.com/docs/mcp/setup](https://stitch.withgoogle.com/docs/mcp/setup)
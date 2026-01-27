# UVAI Video-to-Agent Platform - Remaining Tasks

**Project:** Video-Instruction-to-Agent Pipeline Application
**Generated:** 2026-01-09T11:27:47

---

## ✅ COMPLETED (This Session)

- [x] **Stitch MCP Configuration**: Recovered config from archive and added to `.github/mcp-servers.json` (Requires `STITCH_ACCESS_TOKEN`).
- [x] **VibeVoice Evaluation**: Completed. See `docs/VIBEVOICE_EVALUATION.md`.
- [x] MCP import path configuration fixed (`a2a.py`, `video_subagents.py`, `code_analysis_subagents.py`)
- [x] Installed `mcp` package in venv
- [x] Fixed `real_mcp_client.py` default server path
- [x] `verify_integration.py` passes for all 3 servers
- [x] Installed video/AI dependencies (`openai`, `youtube-transcript-api`, etc.)
- [x] Added `YOUTUBE_API_KEY` to `.env`
- [x] Fixed .env garbage text causing parse warnings
- [x] Created `shared/__init__.py` and `shared/libs/__init__.py` (fixed `No module named 'shared.libs'`)
- [x] Migrated 6 files from deprecated `google.generativeai` to `google.genai` SDK

---

## 🔴 CRITICAL - Blocking Execution

### 1. State Coordinator Not Running

- WebSocket server expected at `localhost:8005`
- Required for MCP shared state coordination
- **File:** `mcp-servers/shared-state/`

---

## 🟡 CODE FIXES REQUIRED

### 4. Deprecated API Usage (`datetime.utcnow()`)

**Affects:** 8+ locations in `video_subagents.py`, `code_analysis_subagents.py`

```python
# Old (deprecated in Python 3.12+):
datetime.utcnow()
# New:
datetime.now(datetime.UTC)
```

### 5. Deprecated Google AI Package

**File:** `src/agents/gemini_video_master_agent.py:25`

```python
# Migrate from:
import google.generativeai as genai
# To:
import google.genai as genai
```

### 6. Missing Module: `shared.libs`

**Error:** `No module named 'shared.libs'`

- Need to create or fix import path for shared library

### 7. Unused Imports (Lint Cleanup)

- `a2a.py`: `json`, `time`, `MCPClient` unused
- `video_subagents.py`: `hashlib`, `base64`, `Optional`, `timedelta`, `MessagePriority` unused
- Multiple `Dict` → `dict`, `List` → `list` modernization needed

---

## 🟠 INFRASTRUCTURE - Setup Required

### 8. MCP Servers Not Running at Runtime

The test scripts try to spawn MCP servers but fail. Need either:

- Running MCP server instances, OR
- Mock/stub implementation for testing

### 9. Documentation Update

- Update `mcp-servers/README.md` with new `lib/` structure
- Document required environment variables
- Document startup sequence

---

## 🔵 MISSION BLUEPRINT - Full System Roadmap

### 10. Vision-Reasoning Stack (Per Blueprint)

- [ ] Video Processing Pipeline (FFmpeg + keyframe extraction)
- [ ] Integration with Gemini 1.5 Pro (2M token context)
- [ ] Vector Database setup (LanceDB or Pinecone for Visual RAG)

### 11. Multi-Agent Council System

| Agent                      | Purpose                         |
| -------------------------- | ------------------------------- |
| Watcher (Perception)       | Scan video, create Visual Log   |
| Contextualizer (Knowledge) | Cross-reference external data   |
| Analyst (Reasoning)        | Pattern detection across videos |
| Reporter (Node.js)         | Real-time WebSocket alerts      |

### 12. Scaling Infrastructure

- [ ] Modal.com or RunPod GPU orchestration
- [ ] Parallel video chunking pipeline
- [ ] FastStream + Kafka for live feeds

### 13. Hybrid Node.js + Python Architecture

Per blueprint:

- **Node.js (Fastify):** Orchestrator, uploads, auth, alerts
- **Python (LangGraph):** Agent logic, cyclic reasoning
- **Redis:** Frame data buffer between Node/Python

---

## 🟣 CONSOLIDATION - Still Pending

### 14. Project Cleanup (From Blueprint)

| Item                                   | Status     | Action                 |
| -------------------------------------- | ---------- | ---------------------- |
| `genkit-mcp/`                          | ⚠️ Bloated | Reduce to wrapper only |
| `self-correcting-executor-PRODUCTION/` | Unknown    | Archive or merge       |
| `software-on-demand/`                  | Unknown    | Investigate            |
| `Zero to Launch Bundle/`               | Unknown    | Investigate            |
| Express v4/v5 inconsistency            | Mixed      | Standardize            |

---

## Priority Order (Suggested)

1. **Install missing dependencies** (5 min)
2. **Set `YOUTUBE_API_KEY` in `.env`** (1 min)
3. **Start state coordinator** (`mcp-servers/shared-state/`) (2 min)
4. **Fix `datetime.utcnow()` deprecations** (10 min)
5. **Migrate `google.generativeai` → `google.genai`** (15 min)
6. **Create/fix `shared.libs` module** (varies)
7. **Run full test suite again**
8. **Begin Vision-Reasoning Stack implementation**

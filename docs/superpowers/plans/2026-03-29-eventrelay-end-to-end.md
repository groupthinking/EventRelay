# EventRelay End-to-End Pipeline Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the EventRelay pipeline flawless end-to-end: YouTube URL in browser -> FastAPI backend processes -> structured analysis returned -> CloudEvents emitted -> deployable to Cloud Run.

**Architecture:** The pipeline already works when run with `PYTHONPATH=src`. The fixes are plumbing: (1) install the package properly so PYTHONPATH isn't needed, (2) fix the APIKeyMiddleware class name mismatch, (3) wire CloudEvents into the correct import path, (4) fix the Dockerfile, (5) add .env.local for frontend-to-backend connectivity.

**Tech Stack:** Python 3.14 / FastAPI / Gemini API / Next.js 14 / Docker / Cloud Run

---

### Task 1: Fix Python Package Installation

The package has a `pyproject.toml` with `[tool.setuptools.packages.find] where = ["src"]` but was never installed in the venv. The `egg-info` exists at `src/youtube_extension.egg-info` (suggesting a prior partial install), but the venv doesn't have it on its path.

**Files:**
- Modify: `pyproject.toml` (no changes needed, already correct)
- Verify: `.venv/` (pip install -e . into it)

- [ ] **Step 1: Install the package in editable mode**

```bash
source .venv/bin/activate
pip install -e ".[youtube]"
```

Expected: Installation succeeds. The `youtube` extra pulls in `youtube-transcript-api`, `google-api-python-client`, etc.

- [ ] **Step 2: Verify imports work without PYTHONPATH**

```bash
source .venv/bin/activate
python -c "from youtube_extension.main import app; print('OK')"
python -c "from youtube_extension.backend.containers.service_container import get_service_container; print('OK')"
python -c "from youtube_extension.services.workflows.transcript_action_workflow import TranscriptActionWorkflow; print('OK')"
```

Expected: All three print `OK` with no `ModuleNotFoundError`.

- [ ] **Step 3: Commit**

No code changes — just verifying the install. No commit needed.

---

### Task 2: Fix APIKeyMiddleware Import Mismatch

`main.py:69` imports `APIKeyMiddleware` but the class in `api_key_auth.py:18` is named `APIKeyAuthMiddleware`. The app starts anyway (graceful degradation), but auth middleware silently never loads.

**Files:**
- Modify: `src/youtube_extension/main.py:69-71`

- [ ] **Step 1: Write the failing test**

```bash
source .venv/bin/activate
python -c "from youtube_extension.backend.middleware.api_key_auth import APIKeyMiddleware" 2>&1
```

Expected: `ImportError: cannot import name 'APIKeyMiddleware'`

- [ ] **Step 2: Fix the import in main.py**

In `src/youtube_extension/main.py`, change line 69 from:
```python
from .backend.middleware.api_key_auth import APIKeyMiddleware
```
to:
```python
from .backend.middleware.api_key_auth import APIKeyAuthMiddleware as APIKeyMiddleware
```

This aliases the correctly-named class to `APIKeyMiddleware` so line 71 (`app.add_middleware(APIKeyMiddleware)`) still works.

- [ ] **Step 3: Verify the import succeeds**

```bash
source .venv/bin/activate
python -c "
from youtube_extension.main import app
# Check middleware is actually loaded (not just silently skipped)
middles = [type(m).__name__ for m in getattr(app, 'user_middleware', [])]
print('Middleware stack:', middles)
" 2>&1
```

Expected: No warning about "API key auth middleware not available". Middleware stack includes `APIKeyAuthMiddleware`.

- [ ] **Step 4: Commit**

```bash
git add src/youtube_extension/main.py
git commit -m "fix: correct APIKeyAuthMiddleware import name in main.py"
```

---

### Task 3: Fix CloudEvents Publisher Import Path

`router.py:26` imports from `youtube_extension.integration.cloudevents_publisher` but the module lives at `src/integration/cloudevents_publisher.py` (a sibling package, not inside `youtube_extension`). The import silently fails and `_ce_publisher` is `None`, so no events are ever emitted.

**Files:**
- Create: `src/youtube_extension/integration/__init__.py`
- Create: `src/youtube_extension/integration/cloudevents_publisher.py` (re-export from `integration`)

- [ ] **Step 1: Verify the current failure**

```bash
source .venv/bin/activate
python -c "from youtube_extension.integration.cloudevents_publisher import create_publisher" 2>&1
```

Expected: `ModuleNotFoundError: No module named 'youtube_extension.integration'`

- [ ] **Step 2: Create the integration bridge package**

Create `src/youtube_extension/integration/__init__.py`:
```python
"""Bridge to top-level integration package."""
```

Create `src/youtube_extension/integration/cloudevents_publisher.py`:
```python
"""Re-export CloudEvents publisher from the top-level integration package."""
from integration.cloudevents_publisher import (
    CloudEvent,
    CloudEventsPublisher,
    create_publisher,
)

__all__ = ["CloudEvent", "CloudEventsPublisher", "create_publisher"]
```

- [ ] **Step 3: Verify the import succeeds**

```bash
source .venv/bin/activate
python -c "
from youtube_extension.integration.cloudevents_publisher import create_publisher
pub = create_publisher(backend='file')
print(f'Publisher created: {type(pub).__name__}')
"
```

Expected: `Publisher created: CloudEventsPublisher`

- [ ] **Step 4: Run the server and verify CloudEvents emit**

```bash
source .venv/bin/activate
uvicorn youtube_extension.main:app --port 8765 &
sleep 3
curl -s -X POST http://localhost:8765/api/v1/transcript-action \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' > /dev/null
sleep 2
# Check the file sink for emitted events
cat /tmp/cloudevents.jsonl 2>/dev/null || cat events.jsonl 2>/dev/null || echo "Check EVENTS_FILE_PATH env var"
kill %1
```

Expected: At least one CloudEvent JSON line with `type: "com.eventrelay.video.received"`.

- [ ] **Step 5: Commit**

```bash
git add src/youtube_extension/integration/__init__.py src/youtube_extension/integration/cloudevents_publisher.py
git commit -m "fix: bridge CloudEvents publisher into youtube_extension namespace"
```

---

### Task 4: Fix Dockerfile.cloudrun

The Dockerfile doesn't set `PYTHONPATH` and uses `youtube_extension.main:app` which requires the package to be importable. The `pip install -e .` in the builder stage should handle this, but the `--user` flag installs to `/root/.local` which gets copied to `/home/appuser/.local` — the editable install's `.pth` file may reference `/app/src` which is correct.

**Files:**
- Modify: `Dockerfile.cloudrun`

- [ ] **Step 1: Verify the current Dockerfile builds**

```bash
docker build -f Dockerfile.cloudrun -t uvai-test . 2>&1 | tail -20
```

Expected: Likely succeeds (the build installs the package). If it fails, note the error.

- [ ] **Step 2: Add PYTHONPATH as safety net and fix the install**

In `Dockerfile.cloudrun`, make these changes:

1. After `ENV PATH=/home/appuser/.local/bin:$PATH` (line 48), change:
```dockerfile
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app/src:$PYTHONPATH
```

2. In the builder stage, change the pip install from editable to regular (editable installs don't work well in multi-stage Docker builds because the `.pth` file points to the builder's `/app/src`):

Change line 21 from:
```dockerfile
RUN pip install --no-cache-dir --user -e .[youtube,ml,cloud,postgres]
```
to:
```dockerfile
RUN pip install --no-cache-dir --user .[youtube,cloud,postgres]
```

Remove `ml` extra — it pulls PyTorch (~2GB) which bloats the Cloud Run image. ML inference should use a separate service. Also remove `-e` since editable installs don't survive multi-stage copies.

- [ ] **Step 3: Verify the image runs correctly**

```bash
docker build -f Dockerfile.cloudrun -t uvai-test .
docker run --rm -p 8765:8000 -e GEMINI_API_KEY="${GEMINI_API_KEY}" uvai-test &
sleep 5
curl -s http://localhost:8765/health
docker stop $(docker ps -q --filter ancestor=uvai-test)
```

Expected: `{"status":"healthy","service":"uvai-youtube-extension"}`

- [ ] **Step 4: Commit**

```bash
git add Dockerfile.cloudrun
git commit -m "fix: set PYTHONPATH and remove editable install in Cloud Run Dockerfile"
```

---

### Task 5: Add Frontend .env.local for Local Development

The frontend has no `BACKEND_URL` in `.env.local`, so during local dev the `BACKEND_AVAILABLE` flag is `false` and routes skip the backend entirely. The fallback to Gemini works but loses the 3-agent analysis.

**Files:**
- Modify: `apps/web/.env.local`

- [ ] **Step 1: Add BACKEND_URL to .env.local**

Append to `apps/web/.env.local`:
```
# Local backend (run: uvicorn youtube_extension.main:app --reload --port 8000)
BACKEND_URL=http://localhost:8000
```

- [ ] **Step 2: Verify frontend connects to backend**

Terminal 1 (backend):
```bash
source .venv/bin/activate
uvicorn youtube_extension.main:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd apps/web
npm run dev
```

Open `http://localhost:3000`, paste a YouTube URL, verify the dashboard shows:
- Transcript tab with segments
- Actions tab with task board
- Personality and Strategy analysis

Expected: Full 3-agent analysis displayed (not just Gemini summary fallback).

- [ ] **Step 3: Commit**

```bash
git add apps/web/.env.local
git commit -m "feat: add BACKEND_URL to .env.local for local development"
```

Note: `.env.local` is typically gitignored. Check `.gitignore` first — if it's ignored, add a `.env.local.example` instead.

---

### Task 6: End-to-End Smoke Test

Verify the complete pipeline works flawlessly with no warnings or errors.

**Files:**
- No new files — verification only

- [ ] **Step 1: Start backend with clean output**

```bash
source .venv/bin/activate
uvicorn youtube_extension.main:app --port 8000 2>&1 | tee /tmp/uvai-startup.log &
sleep 3
# Verify no WARNING or ERROR lines (except optional ones like OpenTelemetry)
grep -E 'WARNING|ERROR' /tmp/uvai-startup.log | grep -v 'OpenTelemetry\|Transformers'
```

Expected: No unexpected warnings. Specifically:
- No "API key auth middleware not available" (fixed in Task 2)
- No import errors for CloudEvents (fixed in Task 3)

- [ ] **Step 2: Test health endpoints**

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
curl -s http://localhost:8000/api/v1/capabilities | python3 -m json.tool
```

Expected: All return `200` with `"status": "healthy"`.

- [ ] **Step 3: Test transcript-action pipeline**

```bash
curl -s -X POST http://localhost:8000/api/v1/transcript-action \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}' \
  | python3 -c "
import json, sys
r = json.load(sys.stdin)
print(f'Success: {r[\"success\"]}')
print(f'Transcript source: {r[\"transcript\"][\"source\"]}')
print(f'Transcript segments: {len(r[\"transcript\"][\"segments\"])}')
print(f'Agents used: {r[\"orchestration_meta\"][\"agents_used\"]}')
print(f'Agent outputs: {list(r[\"outputs\"].keys())}')
print(f'All agents succeeded: {all(o[\"success\"] for o in r[\"outputs\"].values())}')
"
```

Expected output:
```
Success: True
Transcript source: youtube_transcript_api
Transcript segments: > 0
Agents used: ['transcript_action', 'personality_agent', 'strategy_agent']
Agent outputs: ['transcript_action', 'personality_agent', 'strategy_agent']
All agents succeeded: True
```

- [ ] **Step 4: Test video-to-software pipeline**

```bash
curl -s -X POST http://localhost:8000/api/v1/video-to-software \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "project_type": "web"}' \
  | python3 -c "
import json, sys
r = json.load(sys.stdin)
print(f'Status: {r.get(\"status\", \"unknown\")}')
print(f'Keys: {list(r.keys())}')
" 2>&1
```

Expected: Returns a response (may be partial if no GitHub/Vercel tokens configured, but should not 500).

- [ ] **Step 5: Verify CloudEvents were emitted**

```bash
# Check file sink (default backend)
ls -la /tmp/cloudevents*.jsonl 2>/dev/null
cat /tmp/cloudevents*.jsonl 2>/dev/null | python3 -c "
import json, sys
for line in sys.stdin:
    e = json.loads(line)
    print(f'{e[\"type\"]} — {e.get(\"subject\", \"no subject\")}')
" 2>/dev/null
```

Expected: CloudEvent lines for `com.eventrelay.video.received` and `com.eventrelay.pipeline.completed`.

- [ ] **Step 6: Run pytest**

```bash
source .venv/bin/activate
pytest tests/ -v --tb=short -x 2>&1 | tail -30
```

Expected: Tests pass (or fail only due to missing test fixtures, not import errors).

- [ ] **Step 7: Stop server and clean up**

```bash
kill %1 2>/dev/null
```

---

## Summary of Fixes

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | Package not importable | Never installed with `pip install -e .` | Run install in venv |
| 2 | APIKeyMiddleware silently skipped | Class name mismatch (`APIKeyAuthMiddleware` vs `APIKeyMiddleware`) | Alias import in main.py |
| 3 | CloudEvents never emitted | Import path wrong (`youtube_extension.integration` doesn't exist) | Bridge package re-exporting from `integration` |
| 4 | Docker image may fail | No PYTHONPATH, editable install in multi-stage build | Add PYTHONPATH, use non-editable install |
| 5 | Frontend skips backend in dev | No BACKEND_URL in .env.local | Add localhost:8000 to .env.local |
| 6 | No verification | — | End-to-end smoke test |

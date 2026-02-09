# Repository Cleanup Plan

## Phase 1: Fix Broken Import Shims ✅ IN PROGRESS

### Files to Fix:

1. `src/backend/main_v2.py` - Update import path to correct location
2. `src/uvai/main_v2.py` - Update import path to correct location

**Issue:** Both files import from `youtube_extension.backend.main_v2` which doesn't exist.
**Solution:** Update to import from `youtube_extension.backend.main:app`

## Phase 2: Consolidate Root Documentation

### Current State:

- `AGENTS.md` (4.3KB) - Agent architecture docs
- `GEMINI.md` (648B) - Gemini-specific rules
- `CLAUDE.md` (4.2KB) - Claude-specific context
- `SKILL.md` (12.8KB) - Large skill documentation
- `README.md` (18KB) - Main readme

### Proposed Structure:

1. Keep `README.md` as the main entry point
2. Move agent-specific docs to `docs/agents/`
3. Move AI assistant rules to `.agent/rules/`
4. Create clear cross-references

## Phase 3: Clean Up Root Files

### Files to Move/Delete:

- `ai-studio-remix.xml` (205KB) → Archive or delete
- `autonomous_processing.log` (826MB) → Delete (logs should be gitignored)
- `backend.log` (11MB) → Delete
- `gemini_master_agent.log` → Delete
- `multi_llm_processor.log` → Delete
- `youtube_extension_api.log` → Delete

### Files to Update:

- `package.json` - Fix broken frontend scripts
- `.gitignore` - Ensure log files are ignored

## Phase 4: Consolidate Dependencies

### Current State:

- Root `pyproject.toml`
- Root `requirements.txt`
- `src/youtube_extension/backend/requirements.txt`
- `src/youtube_extension/backend/requirements.runtime.txt`

### Proposed:

- Keep `pyproject.toml` as the source of truth
- Add note in other requirements files pointing to pyproject.toml
- Consider generating runtime requirements from pyproject.toml

## Phase 5: Clean Up Backend Services (Future)

### Overlapping Services to Review:

- `memory_manager.py` vs `memory_optimizer.py`
- `performance_monitor.py` vs `performance_benchmark_system.py`
- Various video processor implementations

**Note:** This phase requires deeper code review to ensure no breaking changes.

## Execution Order:

1. ✅ Fix import shims (safe, isolated)
2. ✅ Clean up log files (safe, no code impact)
3. ✅ Consolidate documentation (safe, organizational)
4. 🔄 Update package.json scripts (requires testing)
5. 🔄 Consolidate dependencies (requires careful validation)
6. ⏸️ Backend service cleanup (requires deep review)

# UVAI YouTube Extension - Documentation Index

## 📚 Documentation Structure

### Core Documentation
- [README.md](../README.md) - Main project overview & quick start
- [FASTVLM_GEMINI_INTEGRATION.md](../FASTVLM_GEMINI_INTEGRATION.md) - Local FastVLM/Gemma integration roadmap
- [docs/hybrid_gemini_baseline.md](hybrid_gemini_baseline.md) - Gemini/Veo service capabilities and API surface
- [docs/reports/video_transcript_pipeline_status_2025-09-22.md](reports/video_transcript_pipeline_status_2025-09-22.md) - Latest transcript pipeline status and success criteria

### Development Guides
- [ARCHITECTURAL_REFACTORING_ROADMAP.md](development/ARCHITECTURAL_REFACTORING_ROADMAP.md) - System refactoring plan
- [FASTVLM_SETUP.md](development/FASTVLM_SETUP.md) - Local FastVLM integration steps

### Deployment Documentation
- [PRODUCTION_DEPLOYMENT_GUIDE.md](deployment/PRODUCTION_DEPLOYMENT_GUIDE.md) - Production deployment
- [PRODUCTION_STEPS_SUMMARY.md](deployment/PRODUCTION_STEPS_SUMMARY.md) - Deployment steps

### Archive
- [root-level-cleanup-2025-09-17/](archive/root-level-cleanup-2025-09-17/) - Historical documentation from root cleanup

## 🗂️ Script Organization

### Testing Scripts
- `scripts/testing/` - Verification and test utilities
- `scripts/testing/verify_ai_tools.py` - AI tools validation
- `scripts/testing/demonstrate_working_version.py` - System demonstration

### Monitoring Scripts
- `scripts/monitoring/` - System monitoring utilities
- `scripts/monitoring/cursor_monitor.py` - Development monitoring
- `scripts/monitoring/cursor_status_dashboard.py` - Status dashboard

### Maintenance Scripts
- `scripts/maintenance/` - System maintenance utilities
- `scripts/maintenance/auto_recovery_system.py` - Recovery automation
- `scripts/maintenance/backup_api_manager.py` - Backup management

### Utility Scripts
- `scripts/utilities/` - General purpose utilities
- `scripts/utilities/batch_video_processor.py` - Video processing
- `scripts/utilities/enterprise_mcp_server.py` - MCP server utilities

## 🔄 Current Snapshot

- Root directory contains platform entry points (`Dockerfile*`, `Makefile`, `pyproject.toml`), documentation (`README.md`, `FASTVLM_GEMINI_INTEGRATION.md`, `SECURITY.md`, `CLOUD_AI_IMPLEMENTATION_SUMMARY.md`), orchestration assets (`deployment/`, `infrastructure/`), and analysis notebooks (`research/`).
- Active code lives in `src/youtube_extension/` (service + agent implementation) and `frontend/` (React dashboard and extension build).
- Historical or reference material remains under `cursor-styled-docs/`, `research/`, and `docs/archive/` for auditing prior phases.
- Tests are grouped under `tests/` (unit/integration) with selective skipping for optional dependencies (see README Testing section).

Use this index in combination with the main README to locate the latest operational runbooks and architecture notes.

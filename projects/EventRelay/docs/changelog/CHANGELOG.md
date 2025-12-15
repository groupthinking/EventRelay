# Changelog

All notable changes to the UVAI YouTube Extension Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Architecture diagram scaffolding under `docs/visuals/`.
- Hardened security policy detailing support windows and reporting procedure.
- Initial project changelog.

## [1.0.0] - 2025-01-15
### Added
- FastAPI backend delivering transcript → action workflows.
- React dashboard with Gemini/Veo hybrid orchestration.
- Multi-tier transcript fallback pipeline (YouTube captions → Google Speech-to-Text V2 → Gemini video intelligence).
- MCP coordinator and YouTube API proxy with rate limiting and circuit breaker support.
- Docker Compose stacks for backend, orchestrator, MCP server, frontend, and dependencies.
- CLI tooling (`youtube-extension`) for serving, testing, linting, formatting, and migrations.

### Changed
- Standardised project layout under `src/youtube_extension/` and `frontend/`.

### Fixed
- Resolved initial credential validation issues using `scripts/check_credentials.py`.

[Unreleased]: https://github.com/uvai/youtube-extension/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/uvai/youtube-extension/releases/tag/v1.0.0

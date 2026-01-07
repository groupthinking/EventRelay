# Production Implementation Plan

## Phase 1: Critical Fixes (The "It Runs" Milestone)

- [x] **Fix Docker Compose Paths**: Correct the volume mapping for `infrastructure/database/init.sql` in `docker-compose.full.yml`. <!-- owner: DevOps, effort: S -->
- [x] **Docker Entrypoint Fix**: Update `Dockerfile` to correctly use `$PORT` in `CMD`. <!-- owner: DevOps, effort: S -->
- [x] **Dependency Bootstrap Script**: Create `scripts/dev_services.sh` to start only Postgres/Redis via Docker for local dev. <!-- owner: Backend, effort: S -->
- [x] **Database Initialization**: Ensure `alembic` migrations run automatically on startup or via mapped init script. <!-- owner: Backend, effort: M -->
- [x] **Frontend Verification**: Start and verify `apps/web` frontend application. <!-- owner: Frontend, effort: S -->

## Phase 2: Security & Configuration

- [ ] **Secret Management**: Move from `.env` to Google Secret Manager for production. Update `utils/config.py` to fetch secrets. <!-- owner: DevOps, effort: M -->
- [ ] **Key Validation**: Enforce `API_KEY` validation at startup to prevent runtime failures. <!-- owner: Backend, effort: S -->

## Phase 3: Observability & Quality

- [ ] **Structured Logging**: Verify `structlog` configuration in `src/youtube_extension/backend/main.py`. <!-- owner: Backend, effort: S -->
- [ ] **Health Check Robustness**: Update `/health` to check DB/Redis connectivity, not just API responsiveness. <!-- owner: Backend, effort: M -->
- [ ] **CI/CD Pipeline**: Review `.github/workflows` to ensure `pytest` and `docker build` run on PRs. <!-- owner: DevOps, effort: M -->

## Phase 4: Documentation (Runbooks)

- [ ] **Update README**: Explicitly state dependency requirements (Redis/Postgres) for local run. <!-- owner: TechWriter, effort: S -->

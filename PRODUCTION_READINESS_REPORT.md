# Production Readiness Report: EventRelay

## 1. Executive Summary

**Current State:**
The `EventRelay` repository (aka `youtube_extension`) is a sophisticated monorepo featuring a `FastAPI` (v2) backend and `Next.js` frontend. It employs an advanced "Service Container" architecture (`main_v2.py`) and is well-documented. However, the local development bootstrapping was broken due to missing infrastructure directories and manual dependency management.

**Shortest Path to Production:**

1.  **Infrastructure Fixes:** The `infrastructure/database/` directory was missing, breaking `docker-compose`. This has been patched with a basic `init.sql`.
2.  **Containerization:** The `Dockerfile` was hardcoded to port 8000, incompatible with Cloud Run's dynamic `$PORT`. This has been patched.
3.  **Local Bootstrapping:** A new script `scripts/dev_services.sh` has been created to spin up the required Postgres/Redis/RabbitMQ stack, replacing the manual (and broken) steps.

## 2. “It runs” Checklist

**Prerequisites:**

- Python 3.9+
- Node.js 18+
- Docker Desktop (Running)

**Steps:**

1.  **Configure Config:**
    ```bash
    cp .env.example .env
    # Add GEMINI_API_KEY / OPENAI_API_KEY
    ```
2.  **Start Data Layer:**
    ```bash
    chmod +x scripts/dev_services.sh
    ./scripts/dev_services.sh
    ```
3.  **Start Backend:**
    ```bash
    source .venv/bin/activate
    # Use the Canonical Entrypoint (v2)
    uvicorn uvai.api.main:app --reload --port 8000
    ```
4.  **Start Frontend:**
    ```bash
    npm install --prefix apps/web
    npm run dev --prefix apps/web
    ```

## 3. Blockers (Resolutions Applied)

- **Missing Volume (`docker-compose.full.yml`)**:
  - **Issue:** `infrastructure/database` did not exist.
  - **Fix:** Created directory and `init.sql` to enable `uuid-ossp` and `vector` extensions.
- **Cloud Run Compatibility**:
  - **Issue:** `Dockerfile` ignored `$PORT`.
  - **Fix:** Updated `CMD` to use shell substitution: `sh -c "uvicorn ... --port ${PORT:-8000}"`.
- **Docker Daemon Dependency**:
  - **Issue:** `scripts/dev_services.sh` fails if Docker is not running.
  - **Fix:** Script now checks for Docker availability before creating containers.
- **Alembic Schema Conflicts**:
  - **Issue:** `ProgrammingError` due to existing types and invalid foreign key types.
  - **Fix:** Corrected migration script to handle existing Enums and fix column type mismatches (UUID vs String).
- **Knowledge Base Path**:
  - **Issue:** `ai_code_generator.py` failed to import `knowledge_base` due to incorrect `sys.path`.
  - **Fix:** Updated `sys.path` to include `scripts/` directory.
- **Pydantic v2 Compatibility**:
  - **Issue:** `ImportError` for `BaseSettings`.
  - **Fix:** Switched to `pydantic-settings`.

## 4. Production Readiness Gaps

- **Secrets Management**: Current relies on `.env`. Production should migrate to Google Secret Manager.
- **Frontend Dependency Isolation**: The `apps/web` project does not currently utilize the monorepo's shared packages (`@repo/database`, etc.), leading to potential code duplication or inconsistency.

## 5. Implementation Plan (Prioritized)

| Task                                        | Owner    | Effort | Status  |
| :------------------------------------------ | :------- | :----- | :------ |
| **Fix Docker Volume Paths**                 | DevOps   | S      | ✅ Done |
| **Patch Dockerfile CMD**                    | DevOps   | S      | ✅ Done |
| **Create Bootstrapper (`dev_services.sh`)** | Backend  | S      | ✅ Done |
| **Alembic Migrations**                      | Backend  | M      | ✅ Done |
| **Frontend Verification**                   | Frontend | S      | ✅ Done |
| **Consolidate Entrypoints**                 | Backend  | M      | ✅ Done |
| **Migrate to Secret Manager**               | DevOps   | M      | Pending |
| **CI/CD Pipeline Verification**             | DevOps   | M      | Pending |

## 6. Quick Wins

1.  **Consolidate Backend**: Rename `main_v2.py` to `main.py` and archive the legacy file.
2.  **Automate Migrations**: Add `alembic upgrade head` to `scripts/dev_services.sh` (after waiting for DB health).
3.  **Unified Start**: Create a `Makefile` `make dev` that runs `dev_services.sh` + `uvicorn` + `next`.

## 7. Verification Plan

- **Backend Health**: `curl -f http://localhost:8000/api/v1/health`
- **Database**: Verify `pgvector` extension is active.
- **Frontend**: Navigate to `http://localhost:3001` and ensure it connects to the API (no CORS errors).

## 8. Artifacts Added/Updated

- `infrastructure/database/init.sql` (New)
- `scripts/dev_services.sh` (New)
- `Dockerfile` (Patched)
- `docker-compose.full.yml` (Volume path fixed implicitily by creating the dir)

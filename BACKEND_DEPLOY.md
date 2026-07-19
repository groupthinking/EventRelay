# Backend Deploy Runbook — FastAPI on Cloud Run

Deploys the Python/FastAPI backend so the Pro **agent dispatch** feature works
(the Next.js app calls it at `BACKEND_URL`; without it, `/api/agents/dispatch`
returns 503). Verified against the current repo state — the container artifact
is sound; what's left is GCP provisioning + running the workflow.

## Verified in prep (no action needed)

- **Container path is correct.** `Dockerfile` (root, what the deploy workflow
  builds) uses `PORT` correctly (shell-form `uvicorn --port $PORT`; Cloud Run
  injects `PORT=8080`), runs as non-root, and installs from the complete
  `requirements.txt` (fastapi, uvicorn, aiohttp, google-cloud, youtube-transcript-api, yt-dlp).
- **Health endpoints exist:** `/health` (root app) and `/api/v1/health` (v1 router).
  The workflow's post-deploy check curls `/api/v1/health` then `/health`.
- **Agent dispatch needs no database.** It uses an in-memory TTL store
  (`_agent_executions` in `backend/api/v1/router.py`), so no Postgres/Alembic
  migration is required for this feature. (Postgres is only needed for durable
  job history — out of scope for the agent-dispatch MVP.)
- **`shared.youtube` resolves in the container.** The v1 router imports
  `shared.youtube`, which lives in `src/shared/` and is on `PYTHONPATH=/app/src`.
  (See "Known issue" below — it only bites outside the container.)

## What you need to provide

### 1. GitHub Actions secrets (repo → Settings → Secrets → Actions)
| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_SA_KEY` | JSON key for a deploy service account (see roles below) |

### 2. GCP resources (one-time, `gcloud` or Console)
```bash
PROJECT_ID=<your-project>; REGION=us-central1
gcloud config set project "$PROJECT_ID"

# Enable APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com cloudbuild.googleapis.com

# Artifact Registry repo (name MUST be 'eventrelay-repo' — the workflow expects it)
gcloud artifacts repositories create eventrelay-repo \
  --repository-format=docker --location="$REGION"

# Deploy service account + roles
gcloud iam service-accounts create eventrelay-deployer
SA="eventrelay-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
for role in roles/run.admin roles/artifactregistry.writer \
            roles/iam.serviceAccountUser roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA" --role="$role"
done
gcloud iam service-accounts keys create key.json --iam-account="$SA"   # paste key.json into GCP_SA_KEY

# Secret Manager secrets the service mounts (names are referenced by the workflow)
printf '%s' "<your-gemini-key>" | gcloud secrets create gemini-api-key --data-file=-
printf '%s' "<your-openai-key>" | gcloud secrets create openai-api-key --data-file=-
```
> The running service reads `GEMINI_API_KEY` and `OPENAI_API_KEY` from those
> secrets (see the workflow's `--set-secrets`). That's enough for agent dispatch;
> add `XAI_API_KEY` / `ANTHROPIC_API_KEY` similarly if you want those providers.

### 3. Run the deploy
Actions → **Deploy to Google Cloud Run** → *Run workflow* (it's
`workflow_dispatch`; pick the environment input). It builds the root `Dockerfile`,
pushes to Artifact Registry, and `gcloud run deploy`s `eventrelay-api` with
`--allow-unauthenticated`, 2Gi/2CPU, port 8080.

### 4. Wire the URL into the frontend
After deploy, copy the printed service URL and set in Vercel (or
`apps/web/.env.local`):
```
BACKEND_URL=https://eventrelay-api-XXXX-uc.a.run.app
NEXT_PUBLIC_BACKEND_URL=https://eventrelay-api-XXXX-uc.a.run.app
```
Redeploy the frontend. Verify: `curl $BACKEND_URL/api/v1/health` → 200, then
exercise Pro agent dispatch end to end.

## Known issue (documented, not blocking the deploy)

`shared` is split across two directories: root `./shared/` (has
`libs.youtube_proxy`) and `src/shared/` (has `youtube`). Both have `__init__.py`,
so whichever is on `sys.path` first shadows the other's submodules. Impact:
- **In the container:** only `src/` is copied, so `shared.youtube` resolves and
  the v1 router (health + agent dispatch) loads correctly. ✅
- **Running the backend locally from the repo root:** cwd puts root `./shared`
  first, which lacks `youtube`, so the v1 router fails to load and
  `/api/v1/health` 404s. Work around locally by running from a clean cwd with
  `PYTHONPATH=/abs/path/to/src`, or unify the two `shared` trees.
- The only importers of the root-only `shared.libs.youtube_proxy`
  (`src/agents/markdown_video_processor.py`, `src/mcp/mcp_video_processor.py`)
  guard it with try/except and are **not** on the agent-dispatch path.

Recommended follow-up: consolidate the two `shared/` trees into one package to
remove the shadowing hazard.

## Naming note

The **workflow** (`deploy-cloud-run.yml`) is the canonical path:
`eventrelay-api` / `eventrelay-repo`, secrets `GCP_PROJECT_ID` + `GCP_SA_KEY`.
`infrastructure/cloudrun/service.yaml` is an **older** manifest (`uvai-backend`,
project `uvai-730bb`) and is not used by the workflow — ignore it unless you
deliberately switch to a declarative `gcloud run services replace` flow.

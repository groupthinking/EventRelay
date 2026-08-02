# EventRelay / UVAI - Tech Stack Reference

> Last Updated: 2026-02-04

---

## 🎯 Project Overview

| Attribute          | Value                                           |
| ------------------ | ----------------------------------------------- |
| **Project Name**   | EventRelay (UVAI Platform)                      |
| **Project Type**   | Monorepo (Turborepo)                            |
| **Primary Domain** | AI-Powered Video Intelligence Platform          |
| **Repository**     | https://github.com/groupthinking/EventRelay.git |

---

## 🖥️ Frontend Stack

| Category              | Technology       | Version  | Notes                  |
| --------------------- | ---------------- | -------- | ---------------------- |
| **Framework**         | Next.js          | ^14.2.33 | App Router             |
| **Language**          | TypeScript       | ^5       | Strict mode            |
| **UI Library**        | React            | ^18      |                        |
| **Styling**           | Tailwind CSS     | ^3.4.1   | Custom design system   |
| **Build Tool**        | Turbo            | ^2.0.0   | Monorepo orchestration |
| **State Management**  | Zustand          | ^4.5.0   | Lightweight            |
| **API Client**        | AI SDK (Vercel)  | ^5.0.106 | Streaming AI responses |
| **Icon Set**          | Lucide React     | ^0.300.0 |                        |
| **Package Manager**   | npm              | ^10.8.0  | Workspaces enabled     |
| **Testing Framework** | (Not configured) | -        |                        |

### Frontend Dependencies

- `@ai-sdk/anthropic` - Claude integration
- `@ai-sdk/openai` - OpenAI integration
- `@stripe/stripe-js` + `stripe` - Payments
- `@supabase/supabase-js` - Auth/DB client
- `@upstash/redis` - Edge caching
- `next-auth` - Authentication
- `class-variance-authority` + `clsx` + `tailwind-merge` - CSS utilities

---

## 🔧 Backend Stack

| Category            | Technology      | Version          | Notes               |
| ------------------- | --------------- | ---------------- | ------------------- |
| **Language**        | Python          | ^3.11            | Type hints required |
| **Framework**       | FastAPI         | ^0.110.0         | Async-first         |
| **HTTP Server**     | Uvicorn         | ^0.24.0          | ASGI server         |
| **Package Manager** | pip             | -                | pyproject.toml      |
| **Build System**    | setuptools      | ^61.0            | PEP 517             |
| **ORM**             | SQLAlchemy      | ^2.0.0           | Async support       |
| **Database Driver** | aiosqlite       | ^0.19.0          | Local dev           |
| **Migrations**      | Alembic         | ^1.12.0          |                     |
| **Validation**      | Pydantic        | ^2.5.0           | Settings v2         |
| **HTTP Client**     | httpx + aiohttp | ^0.25.0 / ^3.8.0 | Async               |
| **Testing**         | pytest          | ^7.4.0           | pytest-asyncio      |
| **Linting**         | Ruff + Flake8   | ^0.1.0 / ^6.0.0  |                     |

### Backend AI/ML Dependencies

- `google-generativeai` - Gemini API
- `google-cloud-aiplatform` - Vertex AI
- `google-api-python-client` - YouTube Data API
- `youtube-transcript-api` - Transcript extraction
- `yt-dlp` - Video metadata
- `opencv-python` - Video processing
- `ffmpeg-python` - Media transcoding

### Backend Observability

- `sentry-sdk` - Error tracking
- `ddtrace` - DataDog APM
- `structlog` - Structured logging
- `opentelemetry-*` - Distributed tracing

---

## ☁️ GCP Infrastructure (Existing)

### Cloud Run Services

| Service              | Region      | URL                                                         | Status     |
| -------------------- | ----------- | ----------------------------------------------------------- | ---------- |
| `uvai-api`           | us-central1 | https://uvai-api-688578214833.us-central1.run.app           | ✅ Running |
| `uvai-worker`        | us-central1 | https://uvai-worker-688578214833.us-central1.run.app        | ✅ Running |
| `eventrelay-staging` | us-central1 | https://eventrelay-staging-688578214833.us-central1.run.app | ✅ Running |
| `ralph`              | us-central1 | https://ralph-688578214833.us-central1.run.app              | ✅ Running |

### Cloud SQL Databases

| Instance         | Type       | Version | Region      | Status      |
| ---------------- | ---------- | ------- | ----------- | ----------- |
| `uvai-vector-db` | PostgreSQL | 15      | us-central1 | ✅ Runnable |
| `uvai2`          | MySQL      | 8.0     | us-central1 | ✅ Runnable |

### GKE Clusters

| Cluster          | Location    | Version            | Nodes | Status     |
| ---------------- | ----------- | ------------------ | ----- | ---------- |
| `uvai-cluster-1` | us-central1 | 1.33.5-gke.2118001 | 3     | ✅ Running |

### Artifact Registry

| Repository                | Format | Location             |
| ------------------------- | ------ | -------------------- |
| `cloud-run-source-deploy` | Docker | us-central1          |
| `eventrelay-repo`         | Docker | us-central1          |
| `uvai-backend`            | Docker | us-central1          |
| `gcf-artifacts`           | Docker | us-central1/us-east1 |

### Secret Manager

| Secret            | Created    |
| ----------------- | ---------- |
| `DB_PASSWORD`     | 2025-12-25 |
| `GEMINI_API_KEY`  | 2025-12-25 |
| `JWT_SECRET_KEY`  | 2025-12-25 |
| `OPENAI_API_KEY`  | 2025-12-25 |
| `YOUTUBE_API_KEY` | 2025-12-25 |

### Recent Cloud Builds

| ID          | Status  | Created    | Duration |
| ----------- | ------- | ---------- | -------- |
| 226778d2... | SUCCESS | 2025-12-31 | 24m 40s  |
| 97ebe9d8... | SUCCESS | 2025-12-31 | 23m 42s  |
| fcd79a0a... | SUCCESS | 2025-12-31 | 18m 52s  |

---

## 📦 Deployment Configuration

| Category               | Technology                         |
| ---------------------- | ---------------------------------- |
| **Containerization**   | Docker (multi-stage)               |
| **Container Registry** | Artifact Registry (us-central1)    |
| **Build System**       | Cloud Build                        |
| **Orchestration**      | Cloud Run (serverless) + GKE (k8s) |
| **Secrets**            | Secret Manager                     |
| **Monitoring**         | Cloud Logging + Sentry             |

---

## 🔐 Authentication Stack

| Component            | Technology                |
| -------------------- | ------------------------- |
| **Frontend**         | NextAuth.js               |
| **Backend**          | python-jose (JWT)         |
| **Password Hashing** | passlib[bcrypt]           |
| **Database**         | Supabase (via client SDK) |

---

## 📊 Observability Stack

| Purpose            | Technology                |
| ------------------ | ------------------------- |
| **Error Tracking** | Sentry SDK                |
| **APM**            | DataDog (ddtrace)         |
| **Logging**        | structlog → Cloud Logging |
| **Tracing**        | OpenTelemetry             |

---

## 🧪 Testing Stack

| Layer                   | Technology             | Status        |
| ----------------------- | ---------------------- | ------------- |
| **Backend Unit**        | pytest, pytest-asyncio | ✅ Configured |
| **Backend Integration** | pytest, httpx          | ✅ Configured |
| **Frontend**            | (Not configured)       | ❌ Pending    |
| **E2E**                 | (Not configured)       | ❌ Pending    |

---

## 📁 Directory Structure

```
EventRelay/
├── apps/
│   └── web/                    # Next.js frontend
├── src/
│   └── youtube_extension/
│       └── backend/            # FastAPI backend
├── infrastructure/
│   ├── cloudrun/               # Cloud Run configs
│   └── k8s/                    # Kubernetes manifests
├── packages/                   # Shared packages
├── mcp-servers/                # MCP server configs
└── tests/                      # Test suites
```

---

## 🚀 Quick Commands

```bash
# Frontend
cd apps/web && npm run dev

# Backend (run from the repo root; PYTHONPATH=src is required)
PYTHONPATH=src python -m uvicorn youtube_extension.main:app --reload --port 8000

# Deploy Backend (Cloud Build)
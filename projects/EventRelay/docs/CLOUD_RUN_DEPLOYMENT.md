# 🚀 Google Cloud Run Deployment Guide - EventRelay

## Overview

This guide provides comprehensive instructions for deploying EventRelay to Google Cloud Run. EventRelay is a Python/TypeScript application that includes a FastAPI backend, React frontend, and AI/agent components designed for scalable, serverless deployment.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Environment Variables](#environment-variables)
4. [Pre-Deployment Setup](#pre-deployment-setup)
5. [Deployment Steps](#deployment-steps)
6. [Service Configuration](#service-configuration)
7. [Build Optimization](#build-optimization)
8. [Post-Deployment](#post-deployment)
9. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
10. [Security Considerations](#security-considerations)

---

## Prerequisites

### Required Tools

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize gcloud
gcloud init

# Install additional components
gcloud components install docker-credential-gcr
```

### Required Services

Enable the following Google Cloud APIs:

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  speech.googleapis.com \
  youtube.googleapis.com \
  aiplatform.googleapis.com
```

### Account Requirements

- Google Cloud Project with billing enabled
- Sufficient permissions (Cloud Run Admin, Service Account User, Secret Manager Admin)
- API quotas for AI services (Gemini, Speech-to-Text)

---

## Architecture Overview

### Deployment Target

**Current Configuration:** Backend API only (FastAPI)

The Cloud Run service deploys the backend API that:
- Processes YouTube video transcripts
- Orchestrates AI/ML agents
- Provides REST API endpoints
- Handles video processing workflows

**Frontend Deployment:** The React frontend should be deployed separately to:
- Vercel (recommended for Next.js/React)
- Cloud Storage + Cloud CDN (static hosting)
- Firebase Hosting

### Application Components

```
EventRelay (Cloud Run Service)
├── Backend API (FastAPI on Python 3.11)
│   ├── Main Entry: uvai.api.main:app
│   ├── Port: $PORT (Cloud Run dynamic, default 8000)
│   └── Workers: 1 (Cloud Run handles horizontal scaling)
├── Database: Cloud SQL PostgreSQL or Firestore
│   ├── Connection: Cloud SQL Proxy (recommended)
│   └── Fallback: SQLite (development only)
└── AI Services
    ├── Gemini API (video/text analysis)
    ├── OpenAI API (GPT models)
    ├── Anthropic API (Claude)
    └── Google Speech-to-Text v2 (transcription)
```

### Compute Requirements

**Memory & CPU Allocation:**
- **Recommended:** 2GB memory, 2 vCPU
- **Minimum:** 1GB memory, 1 vCPU (for testing only)
- **High Load:** 4GB memory, 4 vCPU (for heavy AI/VLM processing)

**Rationale:**
- AI/VLM processing requires ≥2GB memory for model inference
- Video processing is CPU-intensive
- Concurrent request handling benefits from multiple vCPUs

---

## Environment Variables

### Core Application Settings

```bash
# Environment identification
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Application server
APP_HOST=0.0.0.0
APP_PORT=8000  # Cloud Run overrides with $PORT
APP_WORKERS=1  # Cloud Run handles scaling
```

### Database Configuration

#### Option 1: Cloud SQL PostgreSQL (Recommended)

```bash
# Cloud SQL connection (using Unix socket)
DATABASE_URL=postgresql://[user]:[password]@/[database]?host=/cloudsql/[INSTANCE_CONNECTION_NAME]

# Connection settings
POSTGRES_USER=eventrelay_user
POSTGRES_PASSWORD=<use-secret-manager>
POSTGRES_DB=eventrelay_production
POSTGRES_HOST=/cloudsql/[PROJECT_ID]:[REGION]:[INSTANCE_NAME]

# Connection pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=30
```

#### Option 2: Firestore (NoSQL)

```bash
# Firestore configuration
FIRESTORE_PROJECT_ID=${PROJECT_ID}
FIRESTORE_DATABASE=(default)
```

### AI Service API Keys

```bash
# Google Services
GEMINI_API_KEY=<secret-manager://gemini-api-key>
GOOGLE_API_KEY=${GEMINI_API_KEY}
YOUTUBE_API_KEY=<secret-manager://youtube-api-key>

# OpenAI
OPENAI_API_KEY=<secret-manager://openai-api-key>
OPENAI_ORG_ID=<your-org-id>

# Anthropic Claude
ANTHROPIC_API_KEY=<secret-manager://anthropic-api-key>

# AssemblyAI (transcription)
ASSEMBLYAI_API_KEY=<secret-manager://assemblyai-api-key>
```

**Documentation Links:**
- [Gemini API](https://ai.google.dev/gemini-api/docs) - Get API key
- [YouTube Data API](https://console.cloud.google.com/apis/library/youtube.googleapis.com) - Enable and get key
- [OpenAI API](https://platform.openai.com/api-keys) - Create API key
- [Anthropic Claude](https://console.anthropic.com/) - Get API key
- [AssemblyAI](https://www.assemblyai.com/dashboard/signup) - Get API key

### Security & Authentication

```bash
# JWT configuration
JWT_SECRET_KEY=<secret-manager://jwt-secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Session management
SESSION_SECRET_KEY=<secret-manager://session-secret>
OAUTH_SECRET_KEY=<secret-manager://oauth-secret>

# Internal services
INTERNAL_API_KEY=<secret-manager://internal-api-key>

# Google OAuth 2.0
GOOGLE_CLIENT_ID=<secret-manager://google-client-id>
GOOGLE_CLIENT_SECRET=<secret-manager://google-client-secret>
GOOGLE_REDIRECT_URI=https://[YOUR_SERVICE_URL]/auth/callback
```

### CORS Configuration

```bash
# Production CORS origins (comma-separated)
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Video Processing

```bash
# Processing configuration
VIDEO_PROCESSOR_TYPE=unified
VIDEO_PROCESSOR_MODE=production
FASTVLM_ENABLED=true

# Storage paths (use Cloud Storage buckets in production)
CACHE_DIR=/tmp/cache
ENHANCED_ANALYSIS_DIR=/tmp/analysis
FEEDBACK_DIR=/tmp/feedback

# Processing limits
MAX_VIDEO_SIZE_MB=500
MAX_VIDEO_DURATION_MINUTES=120
PROCESSING_TIMEOUT_SECONDS=600
```

### Monitoring & Observability

```bash
# Metrics
METRICS_ENABLED=true
METRICS_PORT=9090

# Health checks
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10

# Logging
REMOTE_LOGGING_ENABLED=true
REMOTE_LOGGING_ENDPOINT=https://logs.yourdomain.com/api/ingest

# Error tracking (optional)
SENTRY_DSN=<secret-manager://sentry-dsn>
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Complete Required Variables List

**Minimum Required for Startup:**
1. `GEMINI_API_KEY` or `GOOGLE_API_KEY` - AI processing
2. `DATABASE_URL` - Database connection (or defaults to SQLite)
3. `JWT_SECRET_KEY` - Authentication
4. `SESSION_SECRET_KEY` - Session management

**Recommended for Production:**
- All AI service keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, YOUTUBE_API_KEY)
- Database credentials (Cloud SQL connection)
- OAuth credentials (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
- Monitoring (SENTRY_DSN)

---

## Pre-Deployment Setup

### 1. Create Artifact Registry Repository

```bash
# Create repository for Docker images
gcloud artifacts repositories create eventrelay-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="EventRelay container images"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 2. Set Up Secret Manager

```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Create secrets for sensitive values
echo -n "your-gemini-api-key" | \
  gcloud secrets create gemini-api-key --data-file=-

echo -n "your-openai-api-key" | \
  gcloud secrets create openai-api-key --data-file=-

echo -n "your-jwt-secret" | \
  gcloud secrets create jwt-secret --data-file=-

echo -n "your-session-secret" | \
  gcloud secrets create session-secret --data-file=-

# Generate secrets using openssl
echo -n $(openssl rand -hex 32) | \
  gcloud secrets create oauth-secret --data-file=-

# Grant Cloud Run service account access to secrets
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in gemini-api-key openai-api-key jwt-secret session-secret oauth-secret; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
done
```

### 3. Set Up Cloud SQL (Recommended)

```bash
# Create Cloud SQL PostgreSQL instance
gcloud sql instances create eventrelay-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-type=SSD \
  --storage-size=10GB \
  --backup \
  --backup-start-time=02:00

# Create database
gcloud sql databases create eventrelay_production \
  --instance=eventrelay-db

# Create user (store password in Secret Manager)
gcloud sql users create eventrelay_user \
  --instance=eventrelay-db \
  --password=$(openssl rand -base64 32)

# Get connection name
gcloud sql instances describe eventrelay-db \
  --format="value(connectionName)"
# Save this as: PROJECT_ID:REGION:INSTANCE_NAME
```

### 4. Create Service Account (Optional, for Fine-Grained Permissions)

```bash
# Create dedicated service account
gcloud iam service-accounts create eventrelay-service \
  --display-name="EventRelay Cloud Run Service"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:eventrelay-service@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:eventrelay-service@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Deployment Steps

### Method 1: Direct Deployment (Recommended for Quick Start)

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="eventrelay-api"

# Deploy to Cloud Run (builds and deploys in one command)
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10 \
  --port 8000 \
  --set-env-vars "ENVIRONMENT=production,DEBUG=false,LOG_LEVEL=INFO" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,OPENAI_API_KEY=openai-api-key:latest,JWT_SECRET_KEY=jwt-secret:latest,SESSION_SECRET_KEY=session-secret:latest" \
  --add-cloudsql-instances "${PROJECT_ID}:${REGION}:eventrelay-db"
```

### Method 2: Build and Deploy Separately (Recommended for Production)

#### Step 1: Build Container Image

```bash
# Build using Cloud Build
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/${PROJECT_ID}/eventrelay-repo/eventrelay-api:latest \
  --dockerfile Dockerfile.production

# Or build locally and push
docker build -f Dockerfile.production -t us-central1-docker.pkg.dev/${PROJECT_ID}/eventrelay-repo/eventrelay-api:latest .
docker push us-central1-docker.pkg.dev/${PROJECT_ID}/eventrelay-repo/eventrelay-api:latest
```

#### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy $SERVICE_NAME \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/eventrelay-repo/eventrelay-api:latest \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10 \
  --port 8000 \
  --set-env-vars "ENVIRONMENT=production,DEBUG=false,LOG_LEVEL=INFO,APP_HOST=0.0.0.0" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,OPENAI_API_KEY=openai-api-key:latest,JWT_SECRET_KEY=jwt-secret:latest,SESSION_SECRET_KEY=session-secret:latest,OAUTH_SECRET_KEY=oauth-secret:latest" \
  --add-cloudsql-instances "${PROJECT_ID}:${REGION}:eventrelay-db" \
  --service-account eventrelay-service@${PROJECT_ID}.iam.gserviceaccount.com
```

### Method 3: Using cloudbuild.yaml (CI/CD Pipeline)

Create `cloudbuild.yaml`:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'Dockerfile.production'
      - '-t'
      - 'us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:$SHORT_SHA'
      - '-t'
      - 'us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:latest'
      - '.'

  # Push the container image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - 'us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api'

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'eventrelay-api'
      - '--image'
      - 'us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:$SHORT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'

images:
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:$SHORT_SHA'
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:latest'

options:
  machineType: 'E2_HIGHCPU_8'
  logging: CLOUD_LOGGING_ONLY
```

Deploy using Cloud Build:

```bash
gcloud builds submit --config cloudbuild.yaml
```

---

## Service Configuration

### Resource Allocation

```bash
# Basic configuration (testing/development)
--memory 1Gi
--cpu 1
--min-instances 0
--max-instances 5

# Recommended configuration (production)
--memory 2Gi
--cpu 2
--min-instances 1
--max-instances 10
--concurrency 80

# High-load configuration (heavy AI/VLM processing)
--memory 4Gi
--cpu 4
--min-instances 2
--max-instances 20
--concurrency 50
```

### Port Configuration

The application is configured to bind to the `$PORT` environment variable:

```python
# In Dockerfile.production
CMD uvicorn uvai.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

Cloud Run automatically sets `$PORT` (typically 8080, but can vary). The application defaults to 8000 for local testing.

**Verification:**
```bash
# Check the deployed service listens on the correct port
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format="value(spec.template.spec.containers[0].ports[0].containerPort)"
```

### Scaling Configuration

```bash
# Configure autoscaling
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --min-instances 1 \
  --max-instances 10 \
  --concurrency 80

# Configure CPU allocation (always allocated vs allocated only during request)
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --cpu-throttling  # CPU only during requests (default, cost-effective)
  # OR
  --no-cpu-throttling  # CPU always allocated (better performance, higher cost)
```

### Timeout Configuration

```bash
# Set request timeout (max 3600s for 2nd gen)
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --timeout 300  # 5 minutes for video processing
```

### Update Service with All Configuration

```bash
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --concurrency 80 \
  --timeout 300 \
  --no-cpu-throttling \
  --execution-environment gen2  # Use 2nd generation execution environment
```

---

## Build Optimization

### Dockerfile.production Optimizations

The current `Dockerfile.production` includes:

1. **Minimal Base Image:** `python:3.11-slim` reduces image size
2. **Non-root User:** Security best practice
3. **Health Checks:** Built-in health monitoring
4. **Dynamic PORT Binding:** Cloud Run compatibility
5. **Optimized Dependencies:** Only production packages

### Additional Optimizations

#### Multi-Stage Build (Advanced)

Create `Dockerfile.production.optimized`:

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY pyproject.toml ./
COPY src ./src
RUN pip install --user --no-cache-dir -e .[youtube,ml]

# Stage 2: Runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /build/src ./src

# Copy application code
COPY . .

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || exit 1

EXPOSE 8000

# Start with PORT support
CMD uvicorn uvai.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

#### Cloud Build Optimization

Use Cloud Build with custom machine type for faster builds:

```yaml
options:
  machineType: 'E2_HIGHCPU_8'  # Faster builds
  diskSizeGb: 100
  logging: CLOUD_LOGGING_ONLY
  substitutionOption: ALLOW_LOOSE
```

#### Caching Strategy

```yaml
# Add to cloudbuild.yaml for faster rebuilds
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '--cache-from'
      - 'us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:latest'
      - '-f'
      - 'Dockerfile.production'
      - '-t'
      - 'us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:$SHORT_SHA'
      - '.'
```

### Size Reduction Tips

```bash
# Check image size
docker images us-central1-docker.pkg.dev/${PROJECT_ID}/eventrelay-repo/eventrelay-api:latest

# Remove unnecessary files before building
echo "**/.git" >> .dockerignore
echo "**/node_modules" >> .dockerignore
echo "**/tests" >> .dockerignore
echo "**/__pycache__" >> .dockerignore
echo "**/*.pyc" >> .dockerignore
echo "**/frontend" >> .dockerignore  # Frontend deployed separately
```

---

## Post-Deployment

### Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format="value(status.url)")

echo "Service URL: $SERVICE_URL"

# Test health endpoint
curl $SERVICE_URL/api/v1/health

# Test API documentation
curl $SERVICE_URL/docs
# Open in browser: $SERVICE_URL/docs
```

### Set Up Custom Domain

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service $SERVICE_NAME \
  --domain api.yourdomain.com \
  --region $REGION

# Get DNS records to configure
gcloud run domain-mappings describe \
  --domain api.yourdomain.com \
  --region $REGION
```

### Enable Authentication (Optional)

```bash
# Require authentication
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --no-allow-unauthenticated

# Grant access to specific users
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --region $REGION \
  --member="user:admin@yourdomain.com" \
  --role="roles/run.invoker"
```

### Configure Load Balancing (Optional)

```bash
# Create serverless NEG (Network Endpoint Group)
gcloud compute network-endpoint-groups create eventrelay-neg \
  --region=$REGION \
  --network-endpoint-type=serverless \
  --cloud-run-service=$SERVICE_NAME

# Set up Load Balancer with NEG for advanced routing
# See: https://cloud.google.com/load-balancing/docs/https/setting-up-https-serverless
```

---

## Monitoring & Troubleshooting

### View Logs

```bash
# Stream logs in real-time
gcloud run services logs tail $SERVICE_NAME \
  --region $REGION

# View recent logs
gcloud run services logs read $SERVICE_NAME \
  --region $REGION \
  --limit 50

# Filter by severity
gcloud run services logs read $SERVICE_NAME \
  --region $REGION \
  --filter "severity>=ERROR"
```

### Monitor Metrics

```bash
# View service metrics in Cloud Console
echo "https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}/metrics?project=${PROJECT_ID}"

# Key metrics to monitor:
# - Request count
# - Request latency (p50, p95, p99)
# - Error rate
# - Container instance count
# - CPU utilization
# - Memory utilization
```

### Set Up Alerts

```bash
# Create alert policy for error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="EventRelay High Error Rate" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --condition-display-name="Error rate > 5%" \
  --condition-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="'$SERVICE_NAME'" AND metric.type="run.googleapis.com/request_count"'
```

### Common Issues

#### Issue: Container fails to start

```bash
# Check logs for startup errors
gcloud run services logs read $SERVICE_NAME --region $REGION --limit 100

# Common causes:
# - Missing environment variables
# - Database connection issues
# - Missing dependencies
# - Port binding issues (ensure $PORT is used)
```

**Solution:**
```bash
# Test container locally first
docker run -p 8080:8080 -e PORT=8080 \
  -e GEMINI_API_KEY="your-key" \
  us-central1-docker.pkg.dev/${PROJECT_ID}/eventrelay-repo/eventrelay-api:latest
```

#### Issue: Database connection timeouts

```bash
# Verify Cloud SQL connection
gcloud sql instances describe eventrelay-db

# Check if Cloud SQL API is enabled
gcloud services list --enabled | grep sqladmin

# Verify service account has cloudsql.client role
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:eventrelay-service@${PROJECT_ID}.iam.gserviceaccount.com"
```

#### Issue: High latency or timeouts

```bash
# Increase timeout
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --timeout 600

# Increase resources
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --memory 4Gi \
  --cpu 4

# Enable CPU always allocated
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --no-cpu-throttling
```

#### Issue: Cold start delays

```bash
# Set minimum instances
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --min-instances 1

# Use startup CPU boost
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --cpu-boost
```

---

## Security Considerations

### Best Practices

1. **Never Commit Secrets**
   - Use Secret Manager for all sensitive values
   - Never hardcode API keys in source code
   - Review `.env.production.template` and use placeholders only

2. **Use Service Accounts**
   - Create dedicated service account for Cloud Run
   - Grant minimum required permissions (principle of least privilege)
   - Rotate service account keys regularly

3. **Enable VPC Connector (Optional)**
   ```bash
   # Create VPC connector for private network access
   gcloud compute networks vpc-access connectors create eventrelay-connector \
     --region $REGION \
     --range 10.8.0.0/28

   # Attach to Cloud Run service
   gcloud run services update $SERVICE_NAME \
     --region $REGION \
     --vpc-connector eventrelay-connector
   ```

4. **Enable Binary Authorization**
   ```bash
   # Require signed container images
   gcloud container binauthz policy import policy.yaml
   ```

5. **Configure Security Headers**
   - HSTS enabled in application (see Dockerfile.production)
   - CSP policies configured
   - Rate limiting enabled

6. **Regular Updates**
   ```bash
   # Keep base image updated
   docker pull python:3.11-slim
   
   # Rebuild and redeploy regularly
   gcloud builds submit --config cloudbuild.yaml
   ```

### Network Security

```bash
# Restrict ingress to specific sources
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --ingress internal-and-cloud-load-balancing

# Configure Cloud Armor for DDoS protection (requires Load Balancer)
```

### Audit Logging

```bash
# Enable audit logs
gcloud projects get-iam-policy $PROJECT_ID > policy.yaml
# Add auditConfigs to policy.yaml
gcloud projects set-iam-policy $PROJECT_ID policy.yaml
```

---

## Cost Optimization

### Pricing Factors

Cloud Run charges for:
- **CPU/Memory usage** during request processing
- **Request count**
- **Network egress**

### Optimization Tips

```bash
# Use CPU throttling (default)
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --cpu-throttling

# Set appropriate concurrency
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --concurrency 80  # Higher = more cost-effective

# Use min-instances sparingly
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --min-instances 0  # Scale to zero when idle
```

### Cost Monitoring

```bash
# Set up budget alerts
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="EventRelay Monthly Budget" \
  --budget-amount=100 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

---

## Rollback and Version Management

### Deploy New Version

```bash
# Deploy with traffic splitting (canary deployment)
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/eventrelay-repo/eventrelay-api:v2 \
  --tag canary \
  --no-traffic

# Route 10% traffic to new version
gcloud run services update-traffic $SERVICE_NAME \
  --region $REGION \
  --to-tags canary=10
```

### Rollback

```bash
# List revisions
gcloud run revisions list \
  --service $SERVICE_NAME \
  --region $REGION

# Rollback to previous revision
gcloud run services update-traffic $SERVICE_NAME \
  --region $REGION \
  --to-revisions PREVIOUS_REVISION=100
```

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy-cloud-run.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-central1
  SERVICE_NAME: eventrelay-api

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1

      - name: Configure Docker
        run: gcloud auth configure-docker us-central1-docker.pkg.dev

      - name: Build and Push
        run: |
          docker build -f Dockerfile.production \
            -t us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:${{ github.sha }} \
            -t us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:latest .
          docker push us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:${{ github.sha }}
          docker push us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-api:${{ github.sha }} \
            --region $REGION \
            --platform managed

      - name: Output URL
        run: |
          URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
          echo "Service URL: $URL"
```

---

## Additional Resources

### Documentation Links

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Cloud Build](https://cloud.google.com/build/docs)
- [Artifact Registry](https://cloud.google.com/artifact-registry/docs)

### EventRelay Specific

- [README.md](../README.md) - Project overview and quick start
- [.env.production.template](../.env.production.template) - Environment variables template
- [DEPLOYMENT_README.md](./DEPLOYMENT_README.md) - General deployment architecture
- [pyproject.toml](../pyproject.toml) - Python dependencies

### Support

For issues specific to EventRelay deployment:
1. Check logs using `gcloud run services logs`
2. Review [GitHub Issues](https://github.com/groupthinking/EventRelay/issues)
3. Consult the project documentation

---

## Quick Reference Commands

```bash
# Deploy service
gcloud run deploy eventrelay-api --source . --region us-central1

# View logs
gcloud run services logs tail eventrelay-api --region us-central1

# Update environment variable
gcloud run services update eventrelay-api \
  --region us-central1 \
  --set-env-vars "NEW_VAR=value"

# Update secret
gcloud run services update eventrelay-api \
  --region us-central1 \
  --set-secrets "SECRET_KEY=secret-name:latest"

# Scale service
gcloud run services update eventrelay-api \
  --region us-central1 \
  --min-instances 1 \
  --max-instances 10

# Get service URL
gcloud run services describe eventrelay-api \
  --region us-central1 \
  --format "value(status.url)"

# Delete service
gcloud run services delete eventrelay-api --region us-central1
```

---

**Last Updated:** 2025-10-15  
**Version:** 1.0.0  
**Maintainer:** EventRelay Team

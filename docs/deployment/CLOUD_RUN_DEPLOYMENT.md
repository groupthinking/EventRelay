# Cloud Run Deployment Guide

## Overview

Deploy EventRelay to Google Cloud Run for production workloads.

## Prerequisites

- Google Cloud SDK installed (`gcloud` CLI)
- Docker installed and running
- GCP project configured: `gcloud config set project uvai-730bb`
- Service account with Cloud Run Admin and Secret Manager permissions

## Environment Variables

### Required Variables

| Variable         | Description                       | Example            |
| ---------------- | --------------------------------- | ------------------ |
| `PORT`           | Port Cloud Run assigns (auto-set) | `8080`             |
| `GEMINI_API_KEY` | Google AI API key                 | `AIza...`          |
| `DATABASE_URL`   | Database connection               | `postgresql://...` |

### Optional Variables

| Variable          | Description      |
| ----------------- | ---------------- |
| `OPENAI_API_KEY`  | OpenAI fallback  |
| `YOUTUBE_API_KEY` | YouTube Data API |

Set secrets via Secret Manager (see Security section).

**Note**: Cloud Run provides `$PORT` automatically. Your app MUST bind to this port.

## Deployment Steps

### Quick Deploy

```bash
gcloud run deploy uvai-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Using Cloud Build

```bash
gcloud builds submit --config=cloudbuild.yaml
```

### Using Script

```bash
./scripts/deploy-cloud-run.sh
```

## Service Configuration

### Service YAML (service.yaml)

Configures memory, CPU, scaling, and environment:

```yaml
spec:
  template:
    spec:
      containers:
        - image: gcr.io/uvai-730bb/uvai-api
          resources:
            limits:
              memory: 1Gi
              cpu: 1
```

### Scaling

- Min instances: 0 (for cost savings)
- Max instances: 10 (adjust based on load)

## Build Optimization

### Multi-stage Builds

Use `Dockerfile.production` for optimized images:

- Python 3.11-slim base
- Minimal dependencies
- Non-root user

### .dockerignore

Excludes `node_modules`, `tests`, `.git`, etc.

## Health Checks

- Liveness: `GET /health`
- Readiness: `GET /`

Cloud Run uses these to manage traffic routing.

## Monitoring

### Logs

```bash
gcloud logging read "resource.type=cloud_run_revision"
```

### Metrics

Access via GCP Console → Cloud Run → Metrics

### OpenTelemetry

Set `OTEL_EXPORTER_OTLP_ENDPOINT` for distributed tracing.

## Troubleshooting

### Common Issues

**Container fails to start**

- Check logs: `gcloud run services logs read uvai-api`
- Verify `$PORT` binding

**Cold start latency**

- Set min-instances > 0
- Reduce image size

**Out of memory**

- Increase memory limit
- Check for memory leaks

### Debugging

```bash
gcloud run services describe uvai-api --region=us-central1
```

## Security

### Secret Manager

Store API keys in Secret Manager, NOT in env vars:

```bash
gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"
echo -n "AIza..." | gcloud secrets versions add GEMINI_API_KEY --data-file=-
```

Reference in Cloud Run:

```bash
gcloud run services update uvai-api \
  --set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest
```

### IAM

Use service accounts with least-privilege access.

### Container Security

- Non-root user
- Minimal base image
- No secrets in images

## CI/CD Integration

See `cloudbuild.yaml` and `.github/workflows/deploy-cloud-run.yml`.

## Rollback

```bash
gcloud run services update-traffic uvai-api --to-revisions=REVISION=100
```

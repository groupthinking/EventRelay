# Monitoring & Observability Setup Guide
**Date:** December 22, 2024  
**Status:** 🔧 Configuration Ready  
**Deployment:** Pending Service Setup

---

## Overview

This document provides the complete monitoring strategy for EventRelay production deployment, including infrastructure setup, dashboard configuration, and alerting rules.

---

## Monitoring Stack

### Recommended Services

| Service | Purpose | Tier | Cost/Month |
|---------|---------|------|------------|
| **Sentry** | Error Tracking | Team | $26 |
| **Datadog** | APM & Infrastructure | Pro | $15/host |
| **Uptime Robot** | Uptime Monitoring | Free/Pro | $0-7 |
| **GitHub Actions** | CI/CD Monitoring | Free | $0 |

**Total Estimated Cost:** $41-48/month

---

## 1. Error Tracking (Sentry)

### Setup Instructions

**Installation:**
```bash
# Backend (Python)
cd projects/EventRelay
.venv/bin/pip install sentry-sdk[fastapi]

# Frontend (React)
cd frontend
npm install --save @sentry/react @sentry/vite-plugin
```

**Backend Configuration:**
```python
# src/uvai/api/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "production"),
    traces_sample_rate=1.0,  # Adjust for production (0.1-0.3)
    profiles_sample_rate=1.0,
    integrations=[
        FastApiIntegration(),
        StarletteIntegration(),
    ],
    before_send=filter_sensitive_data,
)
```

**Frontend Configuration:**
```typescript
// frontend/src/main.tsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
  tracesSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
```

### Environment Variables

```bash
# .env
SENTRY_DSN=https://[key]@[org].ingest.sentry.io/[project]
ENVIRONMENT=production
```

---

## 2. Application Performance Monitoring (Datadog)

### Setup Instructions

**Installation:**
```bash
# Backend
pip install ddtrace

# Frontend
npm install --save @datadog/browser-rum
```

**Backend Configuration:**
```python
# Dockerfile.production
ENV DD_SERVICE="eventrelay-api"
ENV DD_ENV="production"
ENV DD_VERSION="2.0.0"
ENV DD_LOGS_INJECTION=true

# Start with ddtrace
CMD ddtrace-run uvicorn uvai.api.main:app --host 0.0.0.0 --port 8000
```

**Frontend Configuration:**
```typescript
// frontend/src/datadog.ts
import { datadogRum } from '@datadog/browser-rum';

datadogRum.init({
  applicationId: import.meta.env.VITE_DD_APPLICATION_ID,
  clientToken: import.meta.env.VITE_DD_CLIENT_TOKEN,
  site: 'datadoghq.com',
  service: 'eventrelay-frontend',
  env: import.meta.env.MODE,
  version: '2.0.0',
  sessionSampleRate: 100,
  sessionReplaySampleRate: 20,
  trackUserInteractions: true,
  trackResources: true,
  trackLongTasks: true,
  defaultPrivacyLevel: 'mask-user-input',
});

datadogRum.startSessionReplayRecording();
```

### Environment Variables

```bash
DD_API_KEY=your_api_key_here
DD_APPLICATION_ID=your_app_id_here
DD_CLIENT_TOKEN=your_client_token_here
```

---

## 3. Dashboard Configuration

### Datadog Dashboard JSON

**Key Metrics:**

```json
{
  "title": "EventRelay Production Dashboard",
  "widgets": [
    {
      "definition": {
        "title": "Request Rate",
        "type": "timeseries",
        "requests": [
          {
            "q": "sum:trace.fastapi.request.hits{env:production}.as_count()",
            "display_type": "line"
          }
        ]
      }
    },
    {
      "definition": {
        "title": "Error Rate",
        "type": "timeseries",
        "requests": [
          {
            "q": "sum:trace.fastapi.request.errors{env:production}.as_count()",
            "display_type": "line"
          }
        ]
      }
    },
    {
      "definition": {
        "title": "Response Time (p95)",
        "type": "timeseries",
        "requests": [
          {
            "q": "p95:trace.fastapi.request.duration{env:production}",
            "display_type": "line"
          }
        ]
      }
    },
    {
      "definition": {
        "title": "API Quota Usage",
        "type": "query_value",
        "requests": [
          {
            "q": "sum:custom.api.quota.usage{service:eventrelay}",
            "aggregator": "last"
          }
        ]
      }
    }
  ]
}
```

---

## 4. Alerting Rules

### Critical Alerts (PagerDuty/Slack)

**High Error Rate:**
```yaml
name: "High Error Rate"
query: "sum(last_5m):sum:trace.fastapi.request.errors{env:production}.as_count() > 50"
message: "@slack-critical API error rate exceeded 50 in 5 minutes"
priority: critical
```

**Service Down:**
```yaml
name: "API Service Down"
query: "avg(last_5m):avg:system.cpu.idle{service:eventrelay} < 1"
message: "@pagerduty-critical EventRelay API is down"
priority: critical
```

**Slow Response Time:**
```yaml
name: "Slow API Response"
query: "avg(last_15m):p95:trace.fastapi.request.duration{env:production} > 2000"
message: "@slack-warning API p95 response time > 2s"
priority: warning
```

### Warning Alerts (Slack)

**High API Quota Usage:**
```yaml
name: "API Quota 80% Used"
query: "avg(last_1h):avg:custom.api.quota.usage{service:eventrelay} > 0.8"
message: "@slack-warning API quota at 80% capacity"
priority: warning
```

**Memory Usage:**
```yaml
name: "High Memory Usage"
query: "avg(last_10m):avg:system.mem.used{service:eventrelay}/avg:system.mem.total{service:eventrelay} > 0.85"
message: "@slack-warning Memory usage > 85%"
priority: warning
```

---

## 5. SLO/SLA Definitions

### Service Level Objectives

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| **Uptime** | 99.5% | 30 days |
| **Error Rate** | <1% | 24 hours |
| **Response Time (p95)** | <500ms | 24 hours |
| **Response Time (p99)** | <1000ms | 24 hours |
| **API Quota** | <90% | Daily |

### SLA Commitments

| Tier | Uptime | Response Time | Support |
|------|--------|---------------|---------|
| **Free** | 99.0% | <2s | Community |
| **Pro** | 99.5% | <500ms | Email 24h |
| **Enterprise** | 99.9% | <300ms | Phone 1h |

---

## 6. Log Aggregation

### Structured Logging (Already Implemented)

```python
# Backend using structlog (DONE)
import structlog

logger = structlog.get_logger()

logger.info(
    "api_request",
    method="POST",
    path="/api/v1/process",
    user_id=user_id,
    duration_ms=duration,
    status_code=200,
)
```

### Log Levels

| Level | Usage | Retention |
|-------|-------|-----------|
| **DEBUG** | Development only | 7 days |
| **INFO** | Normal operations | 30 days |
| **WARNING** | Recoverable issues | 90 days |
| **ERROR** | Application errors | 1 year |
| **CRITICAL** | Service failures | 1 year |

---

## 7. Health Check Endpoints (Already Implemented)

### Liveness Probe

```python
@app.get("/health", tags=["Health"])
@limiter.exempt
async def health_check():
    return JSONResponse(content={
        "status": "ok",
        "service": "uvai-api",
        "timestamp": datetime.utcnow().isoformat(),
    })
```

**Expected Response:**
```json
{
  "status": "ok",
  "service": "uvai-api",
  "timestamp": "2024-12-22T17:00:00Z"
}
```

### Readiness Probe

```python
@app.get("/ready", tags=["Health"])
@limiter.exempt
async def readiness_check():
    # Check database connection
    db_status = await check_database()
    
    # Check external APIs
    api_status = await check_external_apis()
    
    return JSONResponse(content={
        "status": "ready" if all([db_status, api_status]) else "not_ready",
        "checks": {
            "database": "ok" if db_status else "error",
            "external_apis": "ok" if api_status else "error",
        }
    })
```

---

## 8. Deployment Configuration

### Docker Health Checks

```dockerfile
# Dockerfile.production
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### Kubernetes Probes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: eventrelay-api
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
```

---

## 9. Monitoring Checklist

### Pre-Deployment

- [ ] Sentry configured (backend + frontend)
- [ ] Datadog APM installed
- [ ] Dashboards created
- [ ] Alert rules configured
- [ ] SLO/SLA targets defined
- [ ] Health check endpoints tested
- [ ] Log aggregation verified

### Post-Deployment

- [ ] Verify error tracking working
- [ ] Confirm metrics flowing to Datadog
- [ ] Test alert notifications
- [ ] Review dashboard data
- [ ] Validate health check responses
- [ ] Check log collection

---

## 10. Runbook Links

- **Incident Response:** `docs/runbooks/incident-response.md`
- **Scaling Guide:** `docs/runbooks/scaling.md`
- **Database Issues:** `docs/runbooks/database-troubleshooting.md`
- **API Quota Management:** `docs/runbooks/api-quotas.md`

---

## Next Steps

1. **Sign up for Services**
   - Create Sentry account
   - Create Datadog account
   - Configure API keys

2. **Deploy Configuration**
   - Add environment variables
   - Deploy with monitoring enabled
   - Verify data collection

3. **Configure Alerts**
   - Set up Slack/PagerDuty webhooks
   - Test alert delivery
   - Define on-call rotation

4. **Create Runbooks**
   - Document common issues
   - Define escalation paths
   - Create troubleshooting guides

---

**Document Status:** Complete  
**Implementation Status:** Configuration Ready  
**Next Action:** Deploy to staging with monitoring enabled
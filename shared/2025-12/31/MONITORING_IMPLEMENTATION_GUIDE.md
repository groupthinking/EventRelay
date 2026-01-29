# Monitoring Implementation Guide - Day 2
**Date:** December 23, 2024
**Objective:** Set up production monitoring for Cloudflare + GCP deployment
**Estimated Time:** 6-8 hours

---

## 🎯 Overview

We're implementing a dual-platform monitoring strategy:
- **Frontend (Cloudflare):** Sentry + Cloudflare Analytics
- **Backend (GCP):** Sentry + GCP Cloud Monitoring + GCP Cloud Logging
- **Unified View:** Sentry dashboards (errors) + optional Datadog (metrics)

---

## Part 1: Sentry Setup (2-3 hours)

### Step 1: Create Sentry Account

1. **Sign up at https://sentry.io**
   - Use organizational email
   - Choose "Developer" plan (free tier: 5K errors/month)

2. **Create Organization**
   - Name: "EventRelay" or your company name
   - Region: Choose closest to your users

3. **Create Projects**
   - Project 1: `eventrelay-frontend` (Platform: React)
   - Project 2: `eventrelay-backend` (Platform: Python)
   - Project 3: `netmesh-frontend` (Platform: React)

### Step 2: Configure Frontend (netmesh-production)

**Install Sentry SDK:**
```bash
cd projects/netmesh-production
npm install @sentry/react @sentry/cloudflare
```

**Update main.tsx:**
```typescript
// src/main.tsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration({
      maskAllText: false,
      blockAllMedia: false,
    }),
  ],

  // Performance Monitoring
  tracesSampleRate: import.meta.env.PROD ? 0.1 : 1.0,

  // Session Replay
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  // Release tracking
  release: import.meta.env.VITE_APP_VERSION,

  beforeSend(event) {
    // Don't send errors in development
    if (import.meta.env.DEV) {
      return null;
    }
    return event;
  },
});

// Rest of your app initialization
```

**Wrap App with ErrorBoundary:**
```typescript
// src/App.tsx
import * as Sentry from "@sentry/react";

function App() {
  return (
    <Sentry.ErrorBoundary
      fallback={<ErrorFallback />}
      showDialog
    >
      {/* Your app components */}
    </Sentry.ErrorBoundary>
  );
}
```

**Add to .env:**
```bash
# .env.local
VITE_SENTRY_DSN=https://your-dsn@sentry.io/project-id
VITE_APP_VERSION=1.0.0
```

### Step 3: Configure Backend (EventRelay)

**Install Sentry SDK:**
```bash
cd projects/EventRelay
source .venv/bin/activate
pip install sentry-sdk[fastapi]
```

**Update main.py:**
```python
# src/uvai/api/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import os

# Initialize Sentry
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "development"),

    # Performance monitoring
    traces_sample_rate=0.1 if os.getenv("ENVIRONMENT") == "production" else 1.0,

    # Integrations
    integrations=[
        FastApiIntegration(
            transaction_style="endpoint",
        ),
        LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        ),
    ],

    # Release tracking
    release=os.getenv("APP_VERSION", "dev"),

    # Sample rate for profiling
    profiles_sample_rate=0.1,

    # Before send hook
    before_send=lambda event, hint: None if os.getenv("ENVIRONMENT") == "development" else event,
)

# Add to existing FastAPI app
```

**Add to .env:**
```bash
# .env
SENTRY_DSN=https://your-backend-dsn@sentry.io/project-id
ENVIRONMENT=development
APP_VERSION=1.0.0
```

### Step 4: Test Sentry Integration

**Frontend Test:**
```typescript
// Add test button in development
<button onClick={() => {
  throw new Error("Sentry Test Error - Frontend");
}}>
  Test Sentry
</button>
```

**Backend Test:**
```bash
curl -X POST http://localhost:8000/test-sentry
```

```python
# Add test endpoint
@app.post("/test-sentry")
async def test_sentry():
    try:
        1 / 0
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise
```

**Verify in Sentry Dashboard:**
- Go to Issues → Should see test errors
- Check Source Maps uploaded correctly
- Verify stack traces are readable

### Step 5: Configure Source Maps (Frontend)

**Update vite.config.ts:**
```typescript
// vite.config.ts
import { sentryVitePlugin } from "@sentry/vite-plugin";

export default defineConfig({
  build: {
    sourcemap: true,
  },
  plugins: [
    react(),
    sentryVitePlugin({
      org: "your-org",
      project: "netmesh-frontend",
      authToken: process.env.SENTRY_AUTH_TOKEN,
    }),
  ],
});
```

**Add to CI/CD:**
```bash
# In GitHub Actions
- name: Upload Source Maps
  env:
    SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
  run: |
    npm run build
```

---

## Part 2: GCP Cloud Monitoring Setup (2-3 hours)

### Step 1: Enable GCP Services

```bash
# Enable required APIs
gcloud services enable cloudmonitoring.googleapis.com
gcloud services enable cloudlogging.googleapis.com
gcloud services enable clouderrorreporting.googleapis.com
gcloud services enable cloudtrace.googleapis.com
```

### Step 2: Update Backend for GCP Logging

**Install Google Cloud libraries:**
```bash
pip install google-cloud-logging google-cloud-monitoring
```

**Update logging configuration:**
```python
# src/uvai/api/main.py
from google.cloud import logging as cloud_logging
import logging

# Initialize GCP logging
if os.getenv("ENVIRONMENT") == "production":
    client = cloud_logging.Client()
    client.setup_logging()

    # Configure structured logging
    import structlog

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Step 3: Create Custom Metrics

```python
# src/uvai/api/monitoring.py
from google.cloud import monitoring_v3
from datetime import datetime

class MetricsClient:
    def __init__(self):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{os.getenv('GCP_PROJECT_ID')}"

    def record_api_request(self, endpoint: str, duration: float, status_code: int):
        """Record API request metrics."""
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/api/request_duration"
        series.resource.type = "generic_task"

        # Add labels
        series.metric.labels["endpoint"] = endpoint
        series.metric.labels["status_code"] = str(status_code)

        # Add point
        point = monitoring_v3.Point()
        point.value.double_value = duration
        point.interval.end_time.seconds = int(datetime.now().timestamp())
        series.points = [point]

        self.client.create_time_series(name=self.project_name, time_series=[series])
```

**Add middleware:**
```python
from fastapi import Request
import time

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Record metrics
    if os.getenv("ENVIRONMENT") == "production":
        metrics.record_api_request(
            endpoint=request.url.path,
            duration=duration,
            status_code=response.status_code
        )

    return response
```

### Step 4: Create Monitoring Dashboards

**Dashboard JSON (save as `monitoring-dashboard.json`):**
```json
{
  "displayName": "EventRelay Backend Dashboard",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "API Request Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/api/request_duration\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "xPos": 6,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "API Response Times (p95)",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/api/request_duration\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_PERCENTILE_95"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "yPos": 4,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Error Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/api/request_duration\" metric.label.status_code>=500"
                }
              }
            }]
          }
        }
      },
      {
        "xPos": 6,
        "yPos": 4,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Memory Usage",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/container/memory/utilizations\""
                }
              }
            }]
          }
        }
      }
    ]
  }
}
```

**Upload dashboard:**
```bash
gcloud monitoring dashboards create --config-from-file=monitoring-dashboard.json
```

### Step 5: Configure Alerting

**Create alerting policy:**
```bash
# High error rate alert
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --condition-filter='metric.type="custom.googleapis.com/api/request_duration" AND metric.label.status_code>=500'
```

**Alert Policy JSON (`alert-policy.json`):**
```json
{
  "displayName": "EventRelay Critical Alerts",
  "conditions": [
    {
      "displayName": "High Error Rate",
      "conditionThreshold": {
        "filter": "metric.type=\"custom.googleapis.com/api/request_duration\" AND metric.label.status_code>=500",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0.05,
        "duration": "300s",
        "aggregations": [{
          "alignmentPeriod": "60s",
          "perSeriesAligner": "ALIGN_RATE"
        }]
      }
    },
    {
      "displayName": "High Response Time",
      "conditionThreshold": {
        "filter": "metric.type=\"custom.googleapis.com/api/request_duration\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 2.0,
        "duration": "300s",
        "aggregations": [{
          "alignmentPeriod": "60s",
          "perSeriesAligner": "ALIGN_PERCENTILE_95"
        }]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
```

---

## Part 3: Cloudflare Analytics (1 hour)

### Step 1: Enable Cloudflare Web Analytics

1. **Go to Cloudflare Dashboard**
2. **Navigate to Analytics → Web Analytics**
3. **Add site:** netmesh-production.pages.dev
4. **Copy tracking code**

### Step 2: Add to Frontend

**Update index.html:**
```html
<!-- public/index.html -->
<head>
  <!-- Cloudflare Web Analytics -->
  <script defer src='https://static.cloudflareinsights.com/beacon.min.js'
          data-cf-beacon='{"token": "YOUR_TOKEN"}'></script>
</head>
```

### Step 3: Configure Logpush (Optional)

**Send Cloudflare logs to GCP:**
```bash
# Create GCP service account
gcloud iam service-accounts create cloudflare-logpush

# Grant permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:cloudflare-logpush@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"

# Configure in Cloudflare Dashboard
# Analytics → Logs → Logpush → Add destination → GCP Cloud Logging
```

---

## Part 4: Testing & Validation (1-2 hours)

### Checklist

**Sentry Frontend:**
- [ ] Errors appear in Sentry dashboard
- [ ] Source maps working (readable stack traces)
- [ ] Performance traces visible
- [ ] Session replays recording

**Sentry Backend:**
- [ ] Python exceptions captured
- [ ] FastAPI integration working
- [ ] Performance traces visible
- [ ] Breadcrumbs showing request flow

**GCP Monitoring:**
- [ ] Logs appearing in Cloud Logging
- [ ] Custom metrics visible
- [ ] Dashboard displays data
- [ ] Alerts configured and tested

**Cloudflare Analytics:**
- [ ] Page views tracking
- [ ] Performance metrics visible
- [ ] Geographic data showing

---

## Part 5: Documentation & Runbooks

### Create Runbook

**File:** `docs/runbooks/monitoring-playbook.md`

```markdown
# Monitoring Playbook

## Alert Response

### High Error Rate
1. Check Sentry for recent errors
2. Review GCP logs for error patterns
3. Check deployment timeline
4. Rollback if necessary

### High Response Time
1. Check GCP monitoring for resource usage
2. Review slow queries in logs
3. Check external API latencies
4. Scale up if needed

## Daily Checks
- [ ] Review Sentry issues
- [ ] Check error budgets
- [ ] Monitor cost alerts
- [ ] Review performance trends
```

---

## Cost Estimate

| Service | Plan | Monthly Cost |
|---------|------|--------------|
| **Sentry** | Developer (5K errors) | $0 |
| **Sentry** | Team (50K errors) | $26 |
| **GCP Cloud Monitoring** | Free tier + usage | $0-20 |
| **GCP Cloud Logging** | First 50GB free | $0-10 |
| **Cloudflare Analytics** | Included with Pages | $0 |
| **Total (Free tier)** | | **$0** |
| **Total (Paid)** | | **$36-56** |

---

## Next Steps

1. **Today:** Complete Sentry setup (both platforms)
2. **Today:** Configure GCP monitoring
3. **Tomorrow:** Test in staging environment
4. **This Week:** Deploy to production with monitoring
5. **Week 2:** Review metrics and refine alerts

---

**Created:** December 23, 2024
**Status:** Implementation Guide
**Estimated Time:** 6-8 hours total
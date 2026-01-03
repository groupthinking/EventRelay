# Datadog Monitoring Setup
**Date:** December 23, 2024  
**Status:** Configured  
**API Key:** f06361e845d6a6cc30346b5cf52a9475  
**Site:** us5.datadoghq.com

---

## Overview

Datadog is configured for full-stack monitoring:
- **Backend:** APM, traces, logs, metrics (Python/FastAPI)
- **Frontend:** RUM (Real User Monitoring) - Optional
- **Infrastructure:** System metrics via Datadog Agent

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Datadog Platform                │
│  (us5.datadoghq.com)                    │
└─────────────────────────────────────────┘
           ▲           ▲           ▲
           │           │           │
    ┌──────┴──┐  ┌────┴────┐  ┌──┴───┐
    │ Agent   │  │  APM    │  │ Logs │
    │ Metrics │  │ Traces  │  │      │
    └─────────┘  └─────────┘  └──────┘
         │            │           │
    ┌────┴────────────┴───────────┴────┐
    │     EventRelay Backend           │
    │     (FastAPI + ddtrace)          │
    └──────────────────────────────────┘
```

---

## Part 1: System Agent (macOS) ✅

### Installation (Already Done)

You already ran:
```bash
DD_API_KEY=f06361e845d6a6cc30346b5cf52a9475 \
DD_SITE="us5.datadoghq.com" \
bash -c "$(curl -L https://install.datadoghq.com/scripts/install_mac_os.sh)"
```

### Verify Agent is Running

```bash
# Check agent status
datadog-agent status

# Should show:
# - Agent is running
# - API Key valid
# - Sending data to us5.datadoghq.com
```

### Agent Configuration

Edit `/opt/datadog-agent/etc/datadog.yaml` if needed:
```yaml
api_key: f06361e845d6a6cc30346b5cf52a9475
site: us5.datadoghq.com
logs_enabled: true
apm_config:
  enabled: true
  apm_non_local_traffic: true
```

Restart after changes:
```bash
sudo launchctl stop com.datadoghq.agent
sudo launchctl start com.datadoghq.agent
```

---

## Part 2: Backend APM (Python) ✅

### Installation (Already Done)

```bash
cd projects/EventRelay
source .venv/bin/activate
pip install ddtrace  # ✅ Installed: v4.1.0
```

### Configuration Files Created

1. **`src/uvai/api/datadog_config.py`** - APM configuration
2. **`src/uvai/api/main.py`** - Integration point
3. **`.env.local`** - Environment variables

### Running with Datadog

**Option 1: Using ddtrace-run (Recommended)**
```bash
cd projects/EventRelay
source .venv/bin/activate

# Set environment to enable Datadog
export ENVIRONMENT=staging  # or production

# Run with ddtrace wrapper
ddtrace-run uvicorn uvai.api.main:app --host 0.0.0.0 --port 8000
```

**Option 2: Programmatic (Already configured)**
```bash
# Datadog auto-configures on startup via main.py
uvicorn uvai.api.main:app --reload
```

### Verify APM is Working

1. **Start the backend:**
```bash
export ENVIRONMENT=staging
ddtrace-run uvicorn uvai.api.main:app --reload
```

2. **Generate some traffic:**
```bash
# Health check
curl http://localhost:8000/health

# Test endpoint
curl -X POST http://localhost:8000/test-sentry
```

3. **Check Datadog Dashboard:**
   - Go to https://us5.datadoghq.com/apm/traces
   - Should see traces for `eventrelay-backend` service
   - Filter by environment: `development` or `staging`

---

## Part 3: Frontend RUM (Optional)

### Install Datadog Browser SDK

```bash
cd projects/netmesh-production
npm install @datadog/browser-rum
```

### Configure RUM

Create `src/utils/datadog.ts`:
```typescript
import { datadogRum } from '@datadog/browser-rum';

export function initDatadog() {
  const environment = import.meta.env.VITE_ENVIRONMENT || 'development';
  
  if (environment === 'development') {
    console.log('ℹ️  Datadog RUM disabled in development');
    return;
  }

  datadogRum.init({
    applicationId: 'YOUR_APP_ID',
    clientToken: 'YOUR_CLIENT_TOKEN',
    site: 'us5.datadoghq.com',
    service: 'netmesh-frontend',
    env: environment,
    version: import.meta.env.VITE_RELEASE || '1.0.0',
    sessionSampleRate: 100,
    sessionReplaySampleRate: 20,
    trackUserInteractions: true,
    trackResources: true,
    trackLongTasks: true,
    defaultPrivacyLevel: 'mask-user-input',
  });

  datadogRum.startSessionReplayRecording();
}
```

**Note:** Get `applicationId` and `clientToken` from:
https://us5.datadoghq.com/rum/list → Create Application

---

## Part 4: Monitoring Dashboard

### Access Your Dashboard

**Main URL:** https://us5.datadoghq.com

**Key Dashboards:**
- **APM:** https://us5.datadoghq.com/apm/services
- **Infrastructure:** https://us5.datadoghq.com/infrastructure
- **Logs:** https://us5.datadoghq.com/logs
- **RUM:** https://us5.datadoghq.com/rum/sessions

### Create Custom Dashboard

1. Go to **Dashboards → New Dashboard**
2. Add widgets:
   - **APM Request Rate** - Requests/second
   - **APM Latency** - p50, p95, p99
   - **Error Rate** - 5xx errors
   - **Database Queries** - Query performance
   - **Host Metrics** - CPU, Memory, Disk

### Recommended Metrics to Track

**Backend Performance:**
```
avg:trace.fastapi.request.duration{service:eventrelay-backend}
sum:trace.fastapi.request.hits{service:eventrelay-backend}
sum:trace.fastapi.request.errors{service:eventrelay-backend}
```

**Database:**
```
avg:trace.sqlalchemy.query.duration{service:eventrelay-db}
sum:trace.sqlalchemy.query.hits{service:eventrelay-db}
```

**System:**
```
system.cpu.user{host:*}
system.mem.used{host:*}
system.disk.used{device:*}
```

---

## Part 5: Alerting

### Create Alerts

1. **Go to Monitors → New Monitor**

2. **High Error Rate Alert:**
```
Alert when: APM Error Rate
Metric: trace.fastapi.request.errors
Threshold: > 5% for 5 minutes
Service: eventrelay-backend
Environment: production
```

3. **High Latency Alert:**
```
Alert when: APM Latency
Metric: trace.fastapi.request.duration (p95)
Threshold: > 2000ms for 5 minutes
Service: eventrelay-backend
Environment: production
```

4. **System Resource Alert:**
```
Alert when: System CPU
Metric: system.cpu.user
Threshold: > 80% for 10 minutes
Host: all
```

### Notification Channels

Configure in **Integrations:**
- Slack: `#alerts` channel
- Email: your-team@example.com
- PagerDuty: For critical alerts

---

## Part 6: Log Management

### Configure Log Collection

**Backend logs automatically sent via APM integration:**
```python
# Already configured in datadog_config.py
config.logs_injection = True
```

**Manual log forwarding (if needed):**
```python
import logging
from ddtrace import tracer

logger = logging.getLogger(__name__)

# Logs are automatically correlated with traces
logger.info("User action", extra={
    "user_id": user.id,
    "action": "purchase",
    "amount": 100
})
```

### View Logs

1. Go to https://us5.datadoghq.com/logs
2. Filter by:
   - Service: `eventrelay-backend`
   - Environment: `production`
   - Status: `error` or `warning`

---

## Part 7: Production Deployment

### GCP Cloud Run Configuration

Add environment variables to Cloud Run:
```bash
gcloud run deploy eventrelay-backend \
  --update-env-vars \
DD_API_KEY=f06361e845d6a6cc30346b5cf52a9475,\
DD_SITE=us5.datadoghq.com,\
DD_SERVICE=eventrelay-backend,\
DD_ENV=production,\
DD_VERSION=${GIT_COMMIT_SHA},\
DD_LOGS_INJECTION=true,\
DD_TRACE_ANALYTICS_ENABLED=true,\
ENVIRONMENT=production
```

### Dockerfile Update (if needed)

```dockerfile
# Install Datadog tracer
RUN pip install ddtrace

# Use ddtrace-run to start application
CMD ["ddtrace-run", "uvicorn", "uvai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Troubleshooting

### Agent Not Sending Data

```bash
# Check agent logs
tail -f /var/log/datadog/agent.log

# Check agent status
datadog-agent status

# Restart agent
sudo launchctl stop com.datadoghq.agent
sudo launchctl start com.datadoghq.agent
```

### No APM Traces

1. **Verify environment is not 'development':**
```bash
echo $ENVIRONMENT  # Should be staging or production
```

2. **Check ddtrace is installed:**
```bash
pip show ddtrace
```

3. **Verify using ddtrace-run:**
```bash
ddtrace-run uvicorn uvai.api.main:app --reload
```

4. **Check application logs:**
```bash
# Should see: "✅ Datadog APM configured for staging"
```

### High Cardinality Warnings

If you see warnings about high cardinality tags:
```python
# Avoid using unique IDs as tags
# ❌ Bad
span.set_tag("user_id", user.id)

# ✅ Good
span.set_tag("user_type", user.type)
```

---

## Cost Management

### Current Plan

- **Free Tier:** 
  - 1 host
  - 5 containers
  - 150GB logs/month
  - Retained for 15 days

### Monitor Usage

- Dashboard → Usage → Billable Summary
- Set usage alerts at 80% of limits

### Optimize Costs

1. **Reduce trace sampling:**
```python
# In production, sample 10% of traces
config.analytics_sample_rate = 0.1
```

2. **Filter logs:**
```yaml
# Only collect ERROR and above
logs_config:
  log_level: ERROR
```

3. **Use log patterns:**
   - Group similar logs to reduce volume

---

## Next Steps

1. ✅ Verify agent is running on macOS
2. ✅ Test backend APM (generate traffic)
3. ✅ Check traces in Datadog dashboard
4. 🔄 Create custom dashboard
5. 🔄 Set up alerts
6. 🔄 Configure for production deployment

---

**Access:** https://us5.datadoghq.com  
**API Key:** f06361e845d6a6cc30346b5cf52a9475  
**Support:** https://docs.datadoghq.com/
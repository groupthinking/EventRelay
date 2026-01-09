# Monitoring Quick Start Guide
**Date:** December 23, 2024  
**Goal:** Get monitoring running in 5 minutes

---

## Current Status: ✅ Ready to Test

### What's Configured

- ✅ **Sentry** - Error tracking (frontend + backend)
- ✅ **Datadog** - APM, logs, metrics, infrastructure
- ✅ **Health Checks** - `/health` and `/ready` endpoints
- ✅ **Structured Logging** - JSON logs with structlog
- ✅ **Rate Limiting** - slowapi configured

---

## Quick Test (5 Minutes)

### Step 1: Start Datadog Agent (macOS)

```bash
# Check if agent is running
datadog-agent status

# If not running, start it
sudo launchctl start com.datadoghq.agent
```

### Step 2: Start Backend with Monitoring

```bash
cd projects/EventRelay
source .venv/bin/activate

# Set environment to enable monitoring
export ENVIRONMENT=staging

# Option A: With Datadog APM (Recommended)
ddtrace-run uvicorn uvai.api.main:app --host 0.0.0.0 --port 8000

# Option B: Without Datadog (just Sentry + logging)
# export ENVIRONMENT=development
# uvicorn uvai.api.main:app --reload
```

**You should see:**
```
INFO:     Started server process
ℹ️  Datadog APM disabled in development  (if ENV=development)
✅ Datadog APM configured for staging      (if ENV=staging/production)
✅ All required environment variables are set
INFO: startup msg='Production enhancements initialized' features=['sentry', 'structlog', 'rate_limiting', 'health_checks']
```

### Step 3: Generate Test Traffic

```bash
# In another terminal
# Test health checks
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Test Sentry error tracking (will return 500 error)
curl -X POST http://localhost:8000/test-sentry

# Make a few more requests to generate traces
for i in {1..10}; do
  curl http://localhost:8000/health
  sleep 1
done
```

### Step 4: View Results

#### **Datadog Dashboard**
1. Go to https://us5.datadoghq.com/apm/traces
2. Filter by service: `eventrelay-backend`
3. You should see:
   - Traces for `/health`, `/ready` endpoints
   - Database queries (if any)
   - Request latency graphs
   - Error tracking

#### **Sentry Dashboard** (if configured)
1. Go to https://sentry.io
2. Check Issues tab
3. Should see test error from `/test-sentry` endpoint

#### **Logs** (Terminal)
Should see JSON-formatted logs:
```json
{
  "event": "startup",
  "msg": "Production enhancements initialized",
  "features": ["sentry", "structlog", "rate_limiting", "health_checks"],
  "timestamp": "2024-12-23T..."
}
```

---

## What You Can Monitor

### 1. Application Performance (Datadog APM)
- **Request rate** - requests/second
- **Latency** - p50, p95, p99 response times
- **Error rate** - 5xx errors
- **Database queries** - query performance
- **External API calls** - latency to OpenAI, Gemini, etc.

### 2. Errors (Sentry)
- **Stack traces** - detailed error information
- **Breadcrumbs** - user actions leading to error
- **Session replays** - watch what user did
- **Release tracking** - errors by version

### 3. Infrastructure (Datadog Agent)
- **CPU usage** - system.cpu.user
- **Memory** - system.mem.used
- **Disk** - system.disk.used
- **Network** - system.net.bytes_sent

### 4. Logs (Datadog Logs)
- **Structured logs** - JSON format
- **Trace correlation** - logs linked to traces
- **Error logs** - filtered by severity
- **Search & analytics** - query your logs

---

## Next Steps

### 1. Create Dashboards (10 minutes)

**Datadog:**
1. Go to Dashboards → New Dashboard
2. Name it: "EventRelay Production"
3. Add widgets:
   - Timeseries: Request Rate
   - Timeseries: Latency (p95)
   - Query Value: Error Rate
   - Timeseries: CPU Usage
   - Log Stream: Recent Errors

### 2. Configure Alerts (10 minutes)

Create monitors for:
- High error rate (>5% for 5 min)
- High latency (p95 >2s for 5 min)
- High CPU (>80% for 10 min)
- Service down (no traces for 5 min)

### 3. Add Sentry DSN (5 minutes)

If you haven't already:
1. Create Sentry account: https://sentry.io/signup/
2. Create projects: `eventrelay-backend`, `netmesh-frontend`
3. Add DSN to `.env.local` files

### 4. Test in Staging (30 minutes)

Deploy to staging environment and:
- Generate realistic traffic
- Trigger errors intentionally
- Verify dashboards update
- Test alert notifications

---

## Troubleshooting

### "Datadog APM disabled in development"

**Fix:** Set environment variable
```bash
export ENVIRONMENT=staging
ddtrace-run uvicorn uvai.api.main:app --reload
```

### No traces in Datadog

**Check:**
1. Agent is running: `datadog-agent status`
2. Using ddtrace-run: `ddtrace-run uvicorn...`
3. Environment != development
4. Wait 1-2 minutes for traces to appear

### Agent not running

```bash
# Start agent
sudo launchctl start com.datadoghq.agent

# Check status
datadog-agent status
```

### Sentry errors not appearing

**Check:**
1. DSN is set in `.env.local`
2. Environment != development (Sentry disabled in dev)
3. Check network tab in browser for requests to sentry.io

---

## Production Checklist

Before deploying to production:

- [ ] Datadog Agent running on all hosts
- [ ] Environment variables set (DD_API_KEY, DD_SITE, etc.)
- [ ] Sentry DSN configured
- [ ] Custom dashboards created
- [ ] Alerts configured with notifications
- [ ] Tested in staging environment
- [ ] Runbook created for common issues
- [ ] Team has access to Datadog + Sentry

---

## Resources

- **Datadog Setup:** `docs/DATADOG_SETUP.md`
- **Sentry Setup:** `docs/SENTRY_SETUP.md`
- **Datadog Docs:** https://docs.datadoghq.com/
- **Sentry Docs:** https://docs.sentry.io/

**Questions?** Check the detailed setup guides or troubleshooting sections.
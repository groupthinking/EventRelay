# Deployment Platform Strategy
**Date:** December 23, 2024
**Status:** ✅ Decided
**Decision Owner:** Engineering Team

---

## Platform Architecture

### **Frontend Deployment: Cloudflare Pages/Workers**

**Projects:**
- `netmesh-production` → Cloudflare Pages/Workers
- `EventRelay/frontend` → Cloudflare Pages

**Rationale:**
- Edge deployment for low latency
- Excellent DX with Wrangler CLI
- Built-in CDN and caching
- Cost-effective for static sites
- Integrated with Cloudflare ecosystem (D1, R2, KV)

**Configuration:**
```yaml
# wrangler.toml (netmesh-production)
name = "netmesh-production"
compatibility_date = "2024-12-23"
pages_build_output_dir = "dist"
```

---

### **Backend Deployment: Google Cloud Platform (GCP)**

**Projects:**
- `EventRelay/backend` → GCP Cloud Run
- FastAPI services → GCP Cloud Run
- MCP servers → GCP Cloud Run (containerized)

**Rationale:**
- Excellent Python support (Cloud Run)
- Auto-scaling with pay-per-use
- Integrated monitoring (Cloud Logging, Cloud Monitoring)
- Good for containerized workloads
- Strong AI/ML ecosystem (if needed later)

**Configuration:**
```yaml
# cloudbuild.yaml (EventRelay)
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-f', 'Dockerfile.production', '-t', 'gcr.io/$PROJECT_ID/eventrelay:$COMMIT_SHA', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/eventrelay:$COMMIT_SHA']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'eventrelay-backend'
      - '--image'
      - 'gcr.io/$PROJECT_ID/eventrelay:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
```

---

## Consistency Strategy

### **Cross-Platform Considerations**

**Monitoring:**
- Use **Sentry** for error tracking (works with both Cloudflare + GCP)
- Use **GCP Cloud Monitoring** for backend metrics
- Use **Cloudflare Analytics** for frontend metrics
- Consider unified dashboard in Datadog (optional)

**Logging:**
- Backend: GCP Cloud Logging (structured JSON)
- Frontend: Cloudflare Logpush → GCP Cloud Logging (unified)
- Format: Structured JSON for both platforms

**Authentication:**
- Shared JWT tokens
- GCP backend issues tokens
- Cloudflare Workers validate tokens

**Database:**
- Option 1: GCP Cloud SQL (PostgreSQL) - Backend primary
- Option 2: Cloudflare D1 (SQLite) - Frontend data
- Strategy: Backend as source of truth, frontend caches

---

## Future Consolidation Plan

### **Option: Move Everything to GCP**

**Timeline:** Q1 2025 evaluation

**Pros:**
- Single platform simplifies management
- Unified billing and monitoring
- Better integration between services
- Easier to implement service mesh

**Cons:**
- Lose Cloudflare Edge performance benefits
- Higher costs for static assets
- More complex CDN setup needed

**Decision Point:** After 3 months of dual-platform operation
- Evaluate costs
- Measure performance differences
- Assess operational complexity

---

## Current Deployment Status

### **netmesh-production**
- ✅ Configured for Cloudflare Pages
- ✅ wrangler.toml exists
- ✅ Worker bindings configured (D1, R2)
- 🔄 Ready for deployment

### **EventRelay Frontend**
- ✅ Build pipeline works (Vite)
- 🔄 Needs Cloudflare Pages configuration
- 🔄 Migration from current hosting (if any)

### **EventRelay Backend**
- ✅ Dockerfile.production exists
- ✅ cloudbuild.yaml configured
- ✅ Health checks implemented
- 🔄 Ready for GCP Cloud Run deployment

---

## Deployment Commands

### **Frontend (Cloudflare)**

```bash
# netmesh-production
cd projects/netmesh-production
npm run build
wrangler pages deploy

# EventRelay frontend
cd projects/EventRelay/frontend
npm run build
wrangler pages deploy dist
```

### **Backend (GCP)**

```bash
# EventRelay backend
cd projects/EventRelay
gcloud builds submit --config cloudbuild.yaml

# Or manual deploy
docker build -f Dockerfile.production -t gcr.io/PROJECT_ID/eventrelay:latest .
docker push gcr.io/PROJECT_ID/eventrelay:latest
gcloud run deploy eventrelay --image gcr.io/PROJECT_ID/eventrelay:latest --region us-central1
```

---

## Monitoring Integration

### **Sentry Configuration**

**Frontend (Cloudflare):**
```typescript
// Sentry for Cloudflare Workers
import * as Sentry from "@sentry/cloudflare"

Sentry.init({
  dsn: env.SENTRY_DSN,
  environment: env.ENVIRONMENT,
  tracesSampleRate: 0.1,
})
```

**Backend (GCP):**
```python
# Sentry for Python/FastAPI
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT"),
    traces_sample_rate=0.1,
    integrations=[FastApiIntegration()],
)
```

---

## Next Steps

### **This Week - Day 2**
1. ✅ Document platform strategy (this file)
2. 🔄 Set up Sentry accounts (frontend + backend)
3. 🔄 Configure GCP Cloud Monitoring
4. 🔄 Test deployments to both platforms

### **Week 2**
1. Deploy staging environments (both platforms)
2. Set up monitoring dashboards
3. Configure alerting rules
4. Load testing

### **Month 1**
1. Monitor costs on both platforms
2. Evaluate performance metrics
3. Document operational patterns
4. Decide on consolidation timeline

---

**Created:** December 23, 2024
**Last Updated:** December 23, 2024
**Status:** Active - Dual Platform Strategy
**Review Date:** March 2025
# Sentry Setup Instructions
**Date:** December 23, 2024  
**Status:** Ready for Configuration  

---

## Overview

Sentry is configured for both frontend and backend. You just need to create a Sentry account and add your DSN values.

---

## Step 1: Create Sentry Account

1. **Go to https://sentry.io/signup/**
2. **Sign up** with your organizational email
3. **Choose plan:**
   - Developer (Free): 5,000 errors/month - Good for testing
   - Team ($26/month): 50,000 errors/month - Recommended for production

---

## Step 2: Create Projects

### Create Frontend Project

1. Click **"Create Project"**
2. **Platform:** React
3. **Project name:** `netmesh-frontend`
4. **Copy the DSN** - looks like: `https://abc123@o1234567.ingest.sentry.io/1234567`

### Create Backend Project

1. Click **"Create Project"**
2. **Platform:** Python (FastAPI)
3. **Project name:** `eventrelay-backend`
4. **Copy the DSN**

---

## Step 3: Configure DSN Values

### Frontend (netmesh-production)

Edit `projects/netmesh-production/.env.local`:
```bash
VITE_SENTRY_DSN=https://YOUR_FRONTEND_DSN@sentry.io/PROJECT_ID
VITE_ENVIRONMENT=development
VITE_RELEASE=1.0.0
```

### Backend (EventRelay)

Edit `projects/EventRelay/.env.local`:
```bash
SENTRY_DSN=https://YOUR_BACKEND_DSN@sentry.io/PROJECT_ID
ENVIRONMENT=development
APP_VERSION=1.0.0
```

---

## Step 4: Test Sentry Integration

### Test Frontend

1. **Start dev server:**
```bash
cd projects/netmesh-production
npm run dev
```

2. **Open browser console and trigger test error:**
```javascript
// In browser console
throw new Error("Sentry Frontend Test");
```

3. **Check Sentry dashboard** - error should appear in Issues

### Test Backend

1. **Start backend server:**
```bash
cd projects/EventRelay
source .venv/bin/activate
uvicorn uvai.api.main:app --reload
```

2. **Trigger test error:**
```bash
curl -X POST http://localhost:8000/test-sentry
```

3. **Check Sentry dashboard** - error should appear

---

## Step 5: Configure Source Maps (Frontend)

For production builds with readable stack traces:

1. **Create Sentry Auth Token:**
   - Go to https://sentry.io/settings/account/api/auth-tokens/
   - Create new token with `project:releases` scope
   - Copy the token

2. **Add to environment:**
```bash
# For local builds
export SENTRY_AUTH_TOKEN=your_auth_token_here
export SENTRY_ORG=your-org-slug
export SENTRY_PROJECT=netmesh-frontend

# Build with source maps
cd projects/netmesh-production
npm run build
```

3. **For GitHub Actions (later):**
```yaml
# Add secrets in GitHub repo settings
SENTRY_AUTH_TOKEN: <your_token>
```

---

## Step 6: Verify Configuration

### Frontend Checklist

- [ ] DSN added to `.env.local`
- [ ] Test error appears in Sentry dashboard
- [ ] Stack trace is readable
- [ ] Session replay is working (check Replays tab)

### Backend Checklist

- [ ] DSN added to `.env.local`
- [ ] Test error appears in Sentry dashboard
- [ ] FastAPI integration working (breadcrumbs visible)
- [ ] Performance traces visible (Transactions tab)

---

## Step 7: Configure for Production

### Frontend Production Config

Edit `projects/netmesh-production/.env.production`:
```bash
VITE_SENTRY_DSN=https://YOUR_FRONTEND_DSN@sentry.io/PROJECT_ID
VITE_ENVIRONMENT=production
VITE_RELEASE=${GIT_COMMIT_SHA}
```

### Backend Production Config

Add the Sentry secret/environment mapping to the reviewed protected workflow,
then release the exact tested SHA through
`.github/workflows/deploy-cloud-run.yml`. Do not update the Cloud Run service
directly; a direct revision would bypass database, identity, smoke and rollback
gates.

---

## Additional Configuration

### Set User Context (Frontend)

When user logs in:
```typescript
import { setSentryUser } from '@/utils/sentry';

// On successful login
setSentryUser({
  id: user.id,
  email: user.email,
  username: user.username,
});

// On logout
import { clearSentryUser } from '@/utils/sentry';
clearSentryUser();
```

### Add Breadcrumbs (Frontend)

Track user actions:
```typescript
import { addBreadcrumb } from '@/utils/sentry';

addBreadcrumb(
  'User clicked button',
  'user.action',
  'info',
  { buttonId: 'submit-form' }
);
```

### Capture Custom Events

```typescript
import { captureEvent } from '@/utils/sentry';

captureEvent(
  'Payment processed',
  'info',
  { amount: 100, currency: 'USD' }
);
```

---

## Monitoring & Alerts

### Set Up Alerts

1. Go to **Alerts** in Sentry dashboard
2. Create alert for:
   - New issues
   - Error rate spikes (>5% in 5 minutes)
   - Performance degradation (p95 >2s)

### Configure Integrations

1. **Slack:** Settings → Integrations → Slack
2. **Email:** Settings → Notifications
3. **GitHub:** Link issues to GitHub Issues

---

## Cost Management

### Free Tier Limits

- 5,000 errors/month
- 10,000 transactions/month
- 50 replays/month

### Monitor Usage

- Dashboard → Stats
- Set quota alerts at 80% usage
- Archive old issues to save quota

---

## Troubleshooting

### Errors Not Appearing

1. Check DSN is correct
2. Verify environment is not 'development' (Sentry disabled in dev)
3. Check browser console for Sentry init errors
4. Verify network requests to sentry.io are not blocked

### Source Maps Not Working

1. Verify `SENTRY_AUTH_TOKEN` is set
2. Check build output for "Uploading source maps" message
3. Verify release version matches between app and uploaded maps

### Performance Issues

1. Reduce `tracesSampleRate` to 0.05 (5%) in production
2. Reduce `replaysSessionSampleRate` to 0.01 (1%)
3. Keep `replaysOnErrorSampleRate` at 1.0 (100%)

---

## Next Steps

After Sentry is configured:

1. ✅ Configure GCP Cloud Monitoring (backend metrics)
2. ✅ Set up Cloudflare Analytics (frontend metrics)  
3. ✅ Create unified monitoring dashboard
4. ✅ Configure alerting rules
5. ✅ Deploy to staging and test

---

**Questions?** Check Sentry docs at https://docs.sentry.io/

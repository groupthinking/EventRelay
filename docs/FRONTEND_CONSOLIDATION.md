# Frontend Consolidation Runbook

> Resolves issues #82 and #87 — consolidate 5 deployments into one canonical URL

## Target Architecture

```
uvai.io          → event-relay-web.vercel.app (Next.js frontend)
api.uvai.io      → uvai-backend-688578214833.us-central1.run.app (FastAPI)
*.vercel.app     → 301 redirect to uvai.io
uvai-io.pages.dev → 301 redirect to uvai.io
```

## Step 1: Choose Canonical Frontend

**Recommended: `event-relay-web.vercel.app`** (EventRelay Next.js app)

Rationale:
- Most complete codebase (EventRelay is the evolved version)
- Vercel has native custom domain support
- Already deployed and stable

## Step 2: Wire uvai.io → Vercel

### 2a. Add Custom Domain in Vercel
1. Go to [Vercel Dashboard](https://vercel.com) → EventRelay project → Settings → Domains
2. Add `uvai.io` as a custom domain
3. Vercel will provide DNS records (A record or CNAME)

### 2b. Configure DNS at GoDaddy
1. Go to GoDaddy → DNS Management for `uvai.io`
2. Add the records Vercel provides:
   - **Option A (recommended):** CNAME `@` → `cname.vercel-dns.com`
   - **Option B:** A record → `76.76.21.21` (Vercel's IP)
3. Add CNAME for `www` → `cname.vercel-dns.com`

### 2c. Configure api.uvai.io → Cloud Run
1. In GoDaddy DNS, add CNAME: `api` → `uvai-backend-688578214833.us-central1.run.app`
2. In Google Cloud Console → Cloud Run → uvai-backend → Custom Domains → Map `api.uvai.io`
3. Google will provision an SSL certificate automatically

## Step 3: Set Up Redirects

### 3a. Vercel Redirects (vercel.json)
Add to the EventRelay repo root:

```json
{
  "redirects": [
    {
      "source": "/(.*)",
      "has": [
        { "type": "host", "value": "event-relay-web.vercel.app" }
      ],
      "destination": "https://uvai.io/$1",
      "permanent": true
    },
    {
      "source": "/(.*)",
      "has": [
        { "type": "host", "value": "v0-uvai.vercel.app" }
      ],
      "destination": "https://uvai.io/$1",
      "permanent": true
    }
  ]
}
```

### 3b. Cloudflare Redirect (uvai-io.pages.dev)
1. In Cloudflare Dashboard → Pages → uvai-io → Custom domains
2. Add `uvai.io` OR set up a redirect rule:
   - Rule: `uvai-io.pages.dev/*` → 301 to `https://uvai.io/$1`

### 3c. YOUTUBE-EXTENSION Redirect
1. In Vercel → youtube-extension project → Settings → Domains
2. Either delete the project or add a redirect in its vercel.json

## Step 4: Clean Up Duplicate Deployments

After confirming uvai.io works:
1. **Keep:** `event-relay-web.vercel.app` (canonical, serves uvai.io)
2. **Keep:** `uvai-backend-*.run.app` (API, serves api.uvai.io)
3. **Archive/Delete:** `v0-uvai.vercel.app` (Vercel project)
4. **Archive/Delete:** `uvai-io.pages.dev` (Cloudflare Pages project)
5. **Archive/Delete:** `youtube-extension.vercel.app` (Vercel project)

## Step 5: Update References

Update these files to reference `uvai.io` instead of deployment URLs:
- [ ] EventRelay `README.md`
- [ ] YOUTUBE-EXTENSION `README.md`
- [ ] `SESSION_HANDOFF.md`
- [ ] Any marketing materials or documentation

## Verification Checklist
- [ ] `https://uvai.io` loads correctly with SSL
- [ ] `https://api.uvai.io/docs` loads FastAPI docs
- [ ] `https://event-relay-web.vercel.app` redirects to `https://uvai.io`
- [ ] `https://v0-uvai.vercel.app` redirects to `https://uvai.io`
- [ ] `https://uvai-io.pages.dev` redirects to `https://uvai.io`
- [ ] `https://youtube-extension.vercel.app` redirects to `https://uvai.io`

## Estimated Time
- DNS propagation: 1-24 hours
- Vercel custom domain: ~5 minutes
- Cloud Run domain mapping: ~10 minutes + certificate provisioning
- Total active work: ~30 minutes (then wait for DNS)

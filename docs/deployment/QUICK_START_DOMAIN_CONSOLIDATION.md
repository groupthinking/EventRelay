# 🚀 Quick Start: Domain Consolidation Deployment

## TL;DR

**Goal:** Consolidate all frontends to `uvai.io` with API at `api.uvai.io`

**What Changed:**
- ✅ `vercel.json` - Added redirects for legacy domains
- ✅ `next.config.js` - Added domain redirects and security headers
- ✅ `.env.production` - Updated canonical URLs
- ✅ `public/_redirects` - Cloudflare Pages redirect rules

## 3-Step Deployment

### Step 1: Configure DNS (Domain Registrar)

Add these DNS records for `uvai.io`:

```dns
uvai.io       CNAME  cname.vercel-dns.com
www.uvai.io   CNAME  cname.vercel-dns.com
api.uvai.io   CNAME  ghs.googlehosted.com
```

**Time:** 5 minutes + 24-48 hours for propagation

### Step 2: Configure Vercel Project

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select project: `event-relay-web` (or your main project)
3. Settings → Domains → Add Domain
4. Add: `uvai.io` (mark as primary)
5. Vercel will provide DNS records - add them if not using CNAME above
6. Environment Variables → Add:
   ```
   NEXT_PUBLIC_APP_URL=https://uvai.io
   NEXT_PUBLIC_API_URL=https://api.uvai.io
   ```

**Time:** 10 minutes

### Step 3: Deploy Code Changes

```bash
# From repository root
git pull origin main
npm run build  # Test locally
git push origin main  # Auto-deploys to Vercel
```

**Time:** 5 minutes + build time

## Verification Checklist

```bash
# 1. Check redirects (should return 301)
curl -I https://event-relay-web.vercel.app
curl -I https://v0-uvai.vercel.app
curl -I https://youtube-extension.vercel.app
curl -I https://www.uvai.io

# 2. Check canonical domain (should return 200)
curl -I https://uvai.io

# 3. Check API backend
curl https://uvai-backend-gpwz4wb5na-uc.a.run.app/api/v1/health
curl https://api.uvai.io/api/v1/health  # After DNS propagates
```

## Configure Cloud Run Custom Domain

```bash
# Authenticate
gcloud auth login

# Set project
gcloud config set project uvai-730bb

# Map custom domain to Cloud Run service
gcloud run domain-mappings create \
  --service uvai-backend \
  --domain api.uvai.io \
  --region us-central1

# Get DNS record to add
gcloud run domain-mappings describe \
  --domain api.uvai.io \
  --region us-central1
```

## Post-Deployment Cleanup

### Archive Legacy Vercel Projects (Optional)

1. **v0-uvai** project:
   - Settings → General → Archive Project

2. **youtube-extension** project:
   - Settings → General → Archive Project

3. Keep **event-relay-web** as the main project (rename if desired)

### Archive Cloudflare Pages (Optional)

1. Go to Cloudflare Dashboard → Pages
2. Select `uvai-io` project
3. Settings → Delete project (after verifying redirects work)

## Rollback Plan

If something goes wrong:

```bash
# 1. Revert code changes
git revert HEAD
git push origin main

# 2. Remove custom domain from Vercel
# Vercel Dashboard → Settings → Domains → Remove uvai.io

# 3. Restore DNS to previous configuration
# Update DNS records to point back to event-relay-web.vercel.app
```

## Need Help?

- **Full Documentation:** [DOMAIN_CONSOLIDATION.md](./DOMAIN_CONSOLIDATION.md)
- **DNS Issues:** Wait 24-48 hours for propagation, check with `dig uvai.io`
- **SSL Issues:** Vercel auto-provisions SSL, wait up to 24 hours
- **Build Failures:** Check Vercel deployment logs

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "Domain not found" | DNS not propagated yet, wait 24-48 hours |
| "SSL certificate error" | Wait for auto-provisioning, or verify domain ownership |
| "Redirect loop" | Check next.config.js redirects don't conflict with Vercel |
| "API 404" | Verify Cloud Run service is running and domain mapped |

## Success Criteria

✅ `https://uvai.io` loads the frontend (200 OK)
✅ `https://api.uvai.io/api/v1/health` returns backend health (200 OK)
✅ All legacy domains redirect to `uvai.io` (301 Moved Permanently)
✅ www subdomain redirects to non-www (301 Moved Permanently)
✅ SSL certificates valid on all domains
✅ No mixed content warnings

---

**Estimated Total Time:** 30 minutes active work + 24-48 hours DNS propagation
**Complexity:** Low-Medium
**Risk:** Low (easy rollback, no data changes)

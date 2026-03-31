# Domain Consolidation Guide

## Overview

EventRelay has consolidated all frontend deployments to a single canonical domain: **uvai.io**

## Current Architecture

### Production URLs

| Purpose | URL | Status |
|---------|-----|--------|
| **Canonical Frontend** | `https://uvai.io` | ✅ Primary |
| **API Backend** | `https://api.uvai.io` | ✅ CNAME to Cloud Run |
| **Cloud Run Backend** | `https://uvai-backend-gpwz4wb5na-uc.a.run.app` | ✅ Active |

### Legacy URLs (Redirected)

All legacy URLs now permanently redirect (301) to `https://uvai.io`:

- `event-relay-web.vercel.app` → `https://uvai.io`
- `v0-uvai.vercel.app` → `https://uvai.io`
- `youtube-extension.vercel.app` → `https://uvai.io`
- `uvai-io.pages.dev` → `https://uvai.io`
- `www.uvai.io` → `https://uvai.io`

## DNS Configuration

### Required DNS Records

Configure the following DNS records for `uvai.io` domain:

```dns
# Main frontend (Vercel)
uvai.io         A      76.76.21.21 (Vercel IP)
                AAAA   2606:4700:3037::ac43:bd4e (Vercel IPv6)

# Alternative: Use CNAME for Vercel
uvai.io         CNAME  cname.vercel-dns.com

# API subdomain (Cloud Run)
api.uvai.io     CNAME  ghs.googlehosted.com

# WWW redirect (if using CNAME)
www.uvai.io     CNAME  cname.vercel-dns.com
```

### Vercel DNS Configuration

If managing DNS through Vercel:

1. Go to Vercel Project Settings → Domains
2. Add domain: `uvai.io`
3. Add domain: `api.uvai.io` (if routing through Vercel)
4. Configure CNAME records as provided by Vercel

### Cloudflare DNS Configuration

If using Cloudflare for DNS:

1. Go to Cloudflare Dashboard → DNS
2. Add A/CNAME records for `uvai.io`
3. Add CNAME for `api.uvai.io` → `ghs.googlehosted.com`
4. Enable **Proxied** (orange cloud) for CDN and SSL
5. Configure Page Rules for caching:
   - `uvai.io/*` → Cache Level: Standard
   - `api.uvai.io/*` → Cache Level: Bypass

## Vercel Configuration

### Project Settings

1. **Domain Configuration**
   - Primary domain: `uvai.io`
   - Redirect domains:
     - `event-relay-web.vercel.app`
     - `v0-uvai.vercel.app`
     - `youtube-extension.vercel.app`
     - `www.uvai.io`

2. **Environment Variables**
   ```bash
   NEXT_PUBLIC_APP_URL=https://uvai.io
   NEXT_PUBLIC_API_URL=https://api.uvai.io
   BACKEND_URL=https://uvai-backend-gpwz4wb5na-uc.a.run.app
   NEXT_PUBLIC_BACKEND_URL=https://uvai-backend-gpwz4wb5na-uc.a.run.app
   ```

3. **Build Settings**
   - Framework Preset: Next.js
   - Build Command: `npm run build`
   - Output Directory: `.next`
   - Install Command: `npm install`

### Deployment Workflow

```bash
# Deploy to production (automatically via Git push)
git push origin main

# Manual deployment
npm run build
vercel --prod
```

## Google Cloud Run Configuration

### Custom Domain Setup for API

1. **Navigate to Cloud Run Service**
   ```bash
   gcloud run services list
   ```

2. **Add Custom Domain**
   ```bash
   gcloud run domain-mappings create \
     --service uvai-backend \
     --domain api.uvai.io \
     --region us-central1
   ```

3. **Verify DNS Configuration**
   ```bash
   gcloud run domain-mappings describe \
     --domain api.uvai.io \
     --region us-central1
   ```

4. **Update DNS Records**
   - Add the provided CNAME record to your DNS provider
   - Typical format: `api.uvai.io CNAME ghs.googlehosted.com`

### SSL/TLS Certificate

Cloud Run automatically provisions SSL certificates for custom domains via Google-managed certificates. No additional configuration required.

## Cloudflare Pages Migration

If you have an existing Cloudflare Pages deployment (`uvai-io.pages.dev`):

### Option 1: Archive Cloudflare Pages (Recommended)

1. Keep the Cloudflare Pages project for historical purposes
2. Update to serve a redirect page
3. All traffic will redirect via `_redirects` file

### Option 2: Delete Cloudflare Pages

1. Go to Cloudflare Dashboard → Pages
2. Select project `uvai-io`
3. Settings → Delete project
4. Confirm deletion

### Redirect Configuration

The `_redirects` file in `/apps/web/public/_redirects` handles Cloudflare Pages redirects:

```
https://uvai-io.pages.dev/* https://uvai.io/:splat 301!
```

## Terraform Updates

Update your Terraform configuration to reflect the new domain:

```hcl
# infrastructure/terraform/environments/production/main.tf

module "vercel_frontend" {
  source = "../../modules/vercel"

  project_name = "eventrelay-frontend"
  framework    = "nextjs"

  domains = [
    "uvai.io",
    # No www subdomain - handled by redirects
  ]

  environment_variables = {
    NEXT_PUBLIC_APP_URL     = "https://uvai.io"
    NEXT_PUBLIC_API_URL     = "https://api.uvai.io"
    NEXT_PUBLIC_BACKEND_URL = "https://uvai-backend-gpwz4wb5na-uc.a.run.app"
  }
}

module "cloudflare_dns" {
  source = "../../modules/cloudflare"

  domain = "uvai.io"

  dns_records = [
    {
      name    = "@"
      type    = "CNAME"
      value   = "cname.vercel-dns.com"
      proxied = true
    },
    {
      name    = "api"
      type    = "CNAME"
      value   = "ghs.googlehosted.com"
      proxied = true
    },
    {
      name    = "www"
      type    = "CNAME"
      value   = "cname.vercel-dns.com"
      proxied = true
    }
  ]
}
```

## Testing & Verification

### Test Redirects

```bash
# Test legacy domains redirect to canonical domain
curl -I https://event-relay-web.vercel.app
# Expected: HTTP 301, Location: https://uvai.io

curl -I https://v0-uvai.vercel.app
# Expected: HTTP 301, Location: https://uvai.io

curl -I https://youtube-extension.vercel.app
# Expected: HTTP 301, Location: https://uvai.io

curl -I https://www.uvai.io
# Expected: HTTP 301, Location: https://uvai.io
```

### Test API Backend

```bash
# Test Cloud Run backend directly
curl https://uvai-backend-gpwz4wb5na-uc.a.run.app/api/v1/health

# Test via custom domain (after DNS propagation)
curl https://api.uvai.io/api/v1/health
```

### Test Frontend

```bash
# Test canonical domain
curl -I https://uvai.io
# Expected: HTTP 200

# Test API integration
curl https://uvai.io/api/health
```

### DNS Propagation Check

```bash
# Check DNS resolution
dig uvai.io +short
dig api.uvai.io +short
dig www.uvai.io +short

# Check with different DNS servers
dig @8.8.8.8 uvai.io +short  # Google DNS
dig @1.1.1.1 uvai.io +short  # Cloudflare DNS
```

## Monitoring & Analytics

### Vercel Analytics

Enable Vercel Analytics to track traffic and performance:

1. Go to Vercel Project → Analytics
2. Enable Web Analytics
3. Monitor:
   - Traffic sources
   - Page views
   - Redirect performance
   - Geographic distribution

### Google Analytics

Update Google Analytics to track the new canonical domain:

```javascript
// Update gtag.js configuration
gtag('config', 'GA_MEASUREMENT_ID', {
  'cookie_domain': 'uvai.io',
  'cookie_flags': 'SameSite=None;Secure'
});
```

### Cloud Monitoring

Monitor API backend health:

```bash
# View Cloud Run metrics
gcloud monitoring dashboards list

# View service logs
gcloud run services logs tail uvai-backend \
  --region us-central1 \
  --limit 100
```

## SEO Considerations

### Update Sitemap

Update `sitemap.xml` to reflect canonical domain:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://uvai.io/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <!-- Additional pages -->
</urlset>
```

### Update robots.txt

```txt
User-agent: *
Allow: /

Sitemap: https://uvai.io/sitemap.xml
```

### Canonical Tags

Ensure all pages include canonical meta tags:

```html
<link rel="canonical" href="https://uvai.io/current-page" />
```

### Update Search Console

1. Add `uvai.io` to Google Search Console
2. Submit new sitemap
3. Request re-indexing for important pages
4. Monitor redirect coverage

## Rollback Plan

If issues arise, you can rollback by:

1. **Revert DNS Changes**
   - Point `uvai.io` back to previous target
   - Restore legacy domain configurations

2. **Revert Vercel Configuration**
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

3. **Restore Environment Variables**
   - Revert to previous environment variable values
   - Re-deploy to apply changes

## Cleanup Checklist

After successful migration:

- [ ] Verify all redirects working (301 status)
- [ ] DNS propagated globally (24-48 hours)
- [ ] SSL certificates active on all domains
- [ ] API backend accessible via `api.uvai.io`
- [ ] Analytics tracking canonical domain
- [ ] Search Console updated with new domain
- [ ] Sitemap submitted to search engines
- [ ] Internal links updated to canonical domain
- [ ] Legacy Vercel projects archived or deleted
- [ ] Cloudflare Pages project archived or deleted
- [ ] Documentation updated across all repos
- [ ] Team notified of new canonical domain

## Support & Troubleshooting

### Common Issues

**Issue: DNS not resolving**
- Wait 24-48 hours for DNS propagation
- Clear local DNS cache: `sudo dscacheutil -flushcache` (macOS)
- Test with different DNS servers

**Issue: SSL certificate errors**
- Verify domain ownership in Vercel/Cloud Run
- Wait for certificate provisioning (up to 24 hours)
- Check DNS records are correctly configured

**Issue: Redirects not working**
- Verify `vercel.json` and `next.config.js` are deployed
- Clear browser cache and test in incognito mode
- Check Vercel deployment logs

**Issue: API backend unreachable**
- Verify Cloud Run service is running
- Check DNS mapping for `api.uvai.io`
- Verify Cloud Run allows unauthenticated access

## Related Documentation

- [PRODUCTION_ARCHITECTURE.md](./PRODUCTION_ARCHITECTURE.md)
- [Vercel Domains Documentation](https://vercel.com/docs/concepts/projects/domains)
- [Cloud Run Custom Domains](https://cloud.google.com/run/docs/mapping-custom-domains)
- [Cloudflare Pages Redirects](https://developers.cloudflare.com/pages/configuration/redirects/)

---

**Last Updated:** 2026-03-20
**Status:** ✅ Ready for Production
**Owner:** EventRelay Team

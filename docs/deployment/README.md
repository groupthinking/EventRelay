# Deployment Documentation

This directory contains comprehensive guides for deploying and managing EventRelay infrastructure.

## Quick Navigation

### 🚀 Getting Started
- **[QUICK_START_DOMAIN_CONSOLIDATION.md](./QUICK_START_DOMAIN_CONSOLIDATION.md)** - 3-step guide to deploy with consolidated domains
  - Configure DNS (5 minutes)
  - Setup Vercel (10 minutes)
  - Deploy code (5 minutes)
  - Total time: 20 minutes + DNS propagation

### 📚 Complete Guides
- **[DOMAIN_CONSOLIDATION.md](./DOMAIN_CONSOLIDATION.md)** - Full domain consolidation documentation
  - DNS configuration for uvai.io
  - Vercel project setup
  - Cloud Run custom domain mapping
  - Redirect configuration
  - Testing & verification
  - SEO considerations
  - Rollback procedures

- **[PRODUCTION_ARCHITECTURE.md](./PRODUCTION_ARCHITECTURE.md)** - Production deployment architecture
  - Infrastructure requirements
  - Deployment strategies (Blue-Green, Canary, Rolling)
  - Monitoring and alerting
  - CI/CD pipeline configuration
  - Rollback procedures

## Current Production URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | https://uvai.io | Next.js application (Vercel) |
| API Backend | https://api.uvai.io | FastAPI backend (Cloud Run) |
| API Docs | https://api.uvai.io/docs | Interactive Swagger UI |
| Health Check | https://api.uvai.io/api/v1/health | Backend health endpoint |

### Legacy URLs (Redirected)

All these URLs redirect to https://uvai.io:
- `event-relay-web.vercel.app`
- `v0-uvai.vercel.app`
- `youtube-extension.vercel.app`
- `uvai-io.pages.dev`
- `www.uvai.io`

## Infrastructure Components

### Frontend (Vercel)
- **Platform**: Vercel
- **Framework**: Next.js 14
- **Build Command**: `npm run build`
- **Environment Variables**: See [DOMAIN_CONSOLIDATION.md](./DOMAIN_CONSOLIDATION.md#vercel-configuration)

### Backend (Google Cloud Run)
- **Platform**: Google Cloud Run
- **Region**: us-central1
- **Service**: uvai-backend
- **Container Port**: 8080
- **Environment Variables**: Managed via Google Secret Manager

### Database
- **Development**: SQLite (`.runtime/app.db`)
- **Production**: PostgreSQL (configured via Terraform)
- **Migrations**: Alembic

## Deployment Workflows

### Automatic Deployments

```bash
# Frontend - Automatic on push to main
git push origin main
# Vercel automatically deploys and runs build

# Backend - Manual trigger via GitHub Actions
# Go to: Actions → Deploy to Google Cloud Run → Run workflow
```

### Manual Deployments

```bash
# Frontend
cd apps/web
vercel --prod

# Backend
./infrastructure/cloudrun/deploy.sh
```

## Environment Setup

### Required Secrets

**Vercel Environment Variables:**
- `NEXT_PUBLIC_APP_URL`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_BACKEND_URL`
- `BACKEND_URL`
- `GEMINI_API_KEY`
- (See full list in DOMAIN_CONSOLIDATION.md)

**Google Cloud Secrets:**
- `gemini-api-key`
- `openai-api-key`
- `youtube-api-key`
- (Managed via Secret Manager)

## Common Tasks

### Add a Custom Domain
1. Configure DNS records (see [DOMAIN_CONSOLIDATION.md](./DOMAIN_CONSOLIDATION.md#dns-configuration))
2. Add domain in Vercel dashboard
3. Wait for SSL certificate provisioning (up to 24 hours)

### Deploy Backend Update
1. Make code changes
2. Commit and push to GitHub
3. Trigger workflow: `.github/workflows/deploy-cloud-run.yml`
4. Monitor deployment in Cloud Console
5. Verify health check: `curl https://api.uvai.io/api/v1/health`

### Configure Redirects
- **Vercel**: Edit `apps/web/vercel.json` and `apps/web/next.config.js`
- **Cloudflare Pages**: Edit `apps/web/public/_redirects`

### View Logs
```bash
# Vercel logs (frontend)
vercel logs <deployment-url>

# Cloud Run logs (backend)
gcloud run services logs tail uvai-backend --region us-central1

# Real-time logs
gcloud run services logs tail uvai-backend --region us-central1 --follow
```

## Monitoring

### Health Checks
```bash
# Frontend
curl -I https://uvai.io
# Expected: HTTP 200

# Backend
curl https://api.uvai.io/api/v1/health
# Expected: {"status": "healthy", ...}
```

### Performance Monitoring
- **Vercel Analytics**: Project dashboard → Analytics
- **Cloud Run Metrics**: Cloud Console → Cloud Run → uvai-backend → Metrics
- **Application Performance**: `/docs/monitoring/` (if exists)

## Troubleshooting

### DNS Not Resolving
```bash
# Check DNS propagation
dig uvai.io +short
dig api.uvai.io +short

# Test with different DNS servers
dig @8.8.8.8 uvai.io +short  # Google
dig @1.1.1.1 uvai.io +short  # Cloudflare
```

### SSL Certificate Issues
- Verify domain ownership in Vercel/Cloud Run
- Wait up to 24 hours for certificate provisioning
- Check DNS records are correct

### Deployment Failures
- Check GitHub Actions logs
- Review build logs in Vercel dashboard
- Verify environment variables are set
- Check Docker build logs for Cloud Run

### API Connection Issues
- Verify Cloud Run service is running
- Check CORS configuration in backend
- Verify DNS mapping for `api.uvai.io`
- Test backend directly: `https://uvai-backend-gpwz4wb5na-uc.a.run.app`

## Related Documentation

- [../CLAUDE.md](../CLAUDE.md) - Claude Code context and guidelines
- [../ONBOARDING.md](../ONBOARDING.md) - Developer onboarding guide
- [../../infrastructure/](../../infrastructure/) - Infrastructure as Code (Terraform, K8s)
- [../../.github/workflows/](../../.github/workflows/) - CI/CD workflows

## Support

For questions or issues:
1. Check [DOMAIN_CONSOLIDATION.md](./DOMAIN_CONSOLIDATION.md#support--troubleshooting)
2. Review [Common Troubleshooting](#troubleshooting) above
3. Check application logs (Vercel, Cloud Run)
4. Review GitHub Actions workflow runs

---

**Last Updated**: 2026-03-20
**Maintainer**: EventRelay Team

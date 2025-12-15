# Cloud Run Deployment - Quick Reference

## 🚀 One-Line Deploy

```bash
gcloud run deploy eventrelay-api --source . --region us-central1
```

## 📋 Essential Commands

### Deploy with Script
```bash
# Basic deployment
./scripts/deploy-cloud-run.sh production --project my-project

# With secrets setup
./scripts/deploy-cloud-run.sh production --project my-project --setup-secrets

# Dry run
./scripts/deploy-cloud-run.sh production --project my-project --dry-run
```

### Deploy with gcloud
```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Deploy
gcloud run deploy eventrelay-api \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2
```

### Using Cloud Build
```bash
gcloud builds submit --config cloudbuild.yaml
```

## 🔑 Setup Secrets

```bash
# Create secret
echo -n "your-api-key" | gcloud secrets create gemini-api-key --data-file=-

# Grant access
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 🔍 Monitor & Debug

```bash
# View logs
gcloud run services logs tail eventrelay-api --region us-central1

# Get service URL
gcloud run services describe eventrelay-api \
  --region us-central1 \
  --format="value(status.url)"

# Test health
curl $(gcloud run services describe eventrelay-api --region us-central1 --format="value(status.url)")/api/v1/health
```

## ⚙️ Common Configurations

### Development
```bash
--memory 1Gi --cpu 1 --min-instances 0 --max-instances 5
```

### Production (Recommended)
```bash
--memory 2Gi --cpu 2 --min-instances 1 --max-instances 10
```

### High Load
```bash
--memory 4Gi --cpu 4 --min-instances 2 --max-instances 20 --no-cpu-throttling
```

## 📖 Full Documentation

See [CLOUD_RUN_DEPLOYMENT.md](./CLOUD_RUN_DEPLOYMENT.md) for complete guide including:
- Environment variables
- Database setup
- Security configuration
- Monitoring
- Troubleshooting
- Cost optimization

## 🔗 Useful Links

- [Cloud Run Console](https://console.cloud.google.com/run)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Console](https://console.cloud.google.com/security/secret-manager)
- [Artifact Registry Console](https://console.cloud.google.com/artifacts)

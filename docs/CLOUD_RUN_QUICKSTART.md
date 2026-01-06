# Cloud Run Quickstart

Get EventRelay running on Cloud Run in 5 minutes.

## Prerequisites

- Google Cloud SDK installed
- GCP project with billing enabled

## Steps

1. **Authenticate**

   ```bash
   gcloud auth login
   gcloud config set project uvai-730bb
   ```

2. **Enable APIs**

   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com
   ```

3. **Deploy**

   ```bash
   gcloud run deploy uvai-api \
     --source . \
     --region us-central1 \
     --allow-unauthenticated
   ```

4. **Set Secrets**

   ```bash
   gcloud run services update uvai-api \
     --set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest
   ```

5. **Verify**
   ```bash
   curl $(gcloud run services describe uvai-api --format='value(status.url)')/health
   ```

## Next Steps

- See [CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md) for full documentation
- Configure custom domains
- Set up monitoring

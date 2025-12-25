#!/bin/bash
# Script to deploy the UVAI Worker Service

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-uvai-730bb}
REGION=${GOOGLE_CLOUD_REGION:-us-central1}
IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/uvai-api:latest"
SERVICE_NAME="uvai-worker"
SUBSCRIPTION_ID="uvai-backend-worker"
SERVICE_ACCOUNT="uvai-app-sa@$PROJECT_ID.iam.gserviceaccount.com"
CLOUDSQL_INSTANCE="cloudhub-470100:us-central1:eventrelay-db"

echo "Deploying $SERVICE_NAME to $PROJECT_ID in $REGION..."

gcloud run deploy "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --image="$IMAGE" \
    --command="youtube-worker" \
    --service-account="$SERVICE_ACCOUNT" \
    --concurrency=80 \
    --timeout=300 \
    --cpu=2 \
    --memory=2Gi \
    --add-cloudsql-instances="$CLOUDSQL_INSTANCE" \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,PUBSUB_SUBSCRIPTION_ID=$SUBSCRIPTION_ID" \
    --set-env-vars="ENVIRONMENT=production,DEBUG=false,ASYNC_PROCESSING=true,LOG_LEVEL=INFO,LOG_FORMAT=json" \
    --set-env-vars="THENILE_DB_HOST=/cloudsql/$CLOUDSQL_INSTANCE" \
    --set-env-vars="THENILE_DB_USERNAME=uvai,THENILE_DB_NAME=uvai_production,GCS_BUCKET=uvai-videos-prod" \
    --set-env-vars="VIDEO_PROCESSOR_TYPE=enhanced" \
    --set-secrets="THENILE_DB_PASSWORD=DB_PASSWORD:latest" \
    --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest" \
    --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest" \
    --set-secrets="YOUTUBE_API_KEY=YOUTUBE_API_KEY:latest" \
    --set-secrets="JWT_SECRET_KEY=JWT_SECRET_KEY:latest" \
    --no-allow-unauthenticated

echo "Deployment complete for $SERVICE_NAME"

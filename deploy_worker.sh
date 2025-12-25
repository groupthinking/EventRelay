#!/bin/bash
# Script to deploy the UVAI Worker Service

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-uvai-730bb}
REGION=${GOOGLE_CLOUD_REGION:-us-central1}
IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/eventrelay-repo/eventrelay-backend:latest"
SERVICE_NAME="uvai-worker"
SUBSCRIPTION_ID="uvai-backend-worker"
SERVICE_ACCOUNT="uvai-app-sa@$PROJECT_ID.iam.gserviceaccount.com"

echo "Deploying $SERVICE_NAME to $PROJECT_ID in $REGION..."

gcloud run deploy "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --image="$IMAGE" \
    --command="youtube-worker" \
    --service-account="$SERVICE_ACCOUNT" \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,PUBSUB_SUBSCRIPTION_ID=$SUBSCRIPTION_ID" \
    --no-allow-unauthenticated

echo "Deployment complete for $SERVICE_NAME"

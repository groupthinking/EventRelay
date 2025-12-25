#!/bin/bash
# Setup script for Phase 2: Event-Driven Architecture
# Creates Pub/Sub topics, subscriptions, and Eventarc triggers.

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-uvai-730bb}
REGION=${GOOGLE_CLOUD_REGION:-us-central1}
SERVICE_ACCOUNT="688578214833-compute@developer.gserviceaccount.com" # Default Compute Service Account
BUCKET_NAME="uvai-videos-prod"

echo "Using Project: $PROJECT_ID"
echo "Using Region: $REGION"

echo "Using Bucket: $BUCKET_NAME"

# 1. Enable required services
echo "Enabling required services..."
gcloud services enable \
    pubsub.googleapis.com \
    eventarc.googleapis.com \
    run.googleapis.com \
    aiplatform.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    --project="$PROJECT_ID"

# 1a. Create Storage Bucket
echo "Creating Storage Bucket: $BUCKET_NAME"
if ! gsutil ls -p "$PROJECT_ID" "gs://$BUCKET_NAME" > /dev/null 2>&1; then
    gcloud storage buckets create "gs://$BUCKET_NAME" --project="$PROJECT_ID" --location="$REGION"
else
    echo "Bucket $BUCKET_NAME already exists."
fi

# 2. Create Pub/Sub Topic
TOPIC_NAME="uvai-processing-events"
echo "Creating Pub/Sub topic: $TOPIC_NAME"
if ! gcloud pubsub topics describe "$TOPIC_NAME" --project="$PROJECT_ID" > /dev/null 2>&1; then
    gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT_ID"
else
    echo "Topic $TOPIC_NAME already exists."
fi

# 3. Create Pub/Sub Subscription for the Worker
# We use a pull subscription for the worker service
SUBSCRIPTION_NAME="uvai-backend-worker"
echo "Creating Pub/Sub subscription: $SUBSCRIPTION_NAME"
if ! gcloud pubsub subscriptions describe "$SUBSCRIPTION_NAME" --project="$PROJECT_ID" > /dev/null 2>&1; then
    gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
        --topic="$TOPIC_NAME" \
        --project="$PROJECT_ID" \
        --ack-deadline=600 \
        --message-retention-duration=7d
else
    echo "Subscription $SUBSCRIPTION_NAME already exists."
fi

# 4. Grant Pub/Sub Publisher role to the Service Account
echo "Granting Pub/Sub Publisher role to Service Account..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/pubsub.publisher" \
    --condition=None

# 5. Grant Pub/Sub Subscriber role to the Service Account (for the worker)
echo "Granting Pub/Sub Subscriber role to Service Account..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/pubsub.subscriber" \
    --condition=None

echo "Infrastructure setup complete!"
echo "Next steps: Deploy the updated application code."

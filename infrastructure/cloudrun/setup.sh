#!/bin/bash
# Setup Google Cloud infrastructure for cloud-native deployment

set -e

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE_ACCOUNT="uvai-backend-sa"
QUEUE_NAME="video-processing-queue"

echo "🏗️  Setting up cloud infrastructure"
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"

# Enable required APIs
echo "📡 Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  cloudtasks.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project ${PROJECT_ID}

# Create service account if it doesn't exist
echo "👤 Creating service account..."
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com --project ${PROJECT_ID} >/dev/null 2>&1; then
  gcloud iam service-accounts create ${SERVICE_ACCOUNT} \
    --display-name "UVAI Backend Service Account" \
    --project ${PROJECT_ID}
  echo "   ✅ Service account created"
else
  echo "   ℹ️  Service account already exists"
fi

# Grant required IAM roles
echo "🔐 Granting IAM roles..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member "serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role "roles/datastore.user"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member "serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role "roles/cloudtasks.enqueuer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member "serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role "roles/aiplatform.user"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member "serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role "roles/secretmanager.secretAccessor"

echo "   ✅ IAM roles granted"

# Initialize Firestore (if not already initialized)
echo "🗄️  Initializing Firestore..."
if ! gcloud firestore databases describe --project ${PROJECT_ID} >/dev/null 2>&1; then
  gcloud firestore databases create \
    --location=${REGION} \
    --type=firestore-native \
    --project ${PROJECT_ID}
  echo "   ✅ Firestore initialized"
else
  echo "   ℹ️  Firestore already initialized"
fi

# Create Cloud Tasks queue
echo "📋 Creating Cloud Tasks queue..."
if ! gcloud tasks queues describe ${QUEUE_NAME} --location=${REGION} --project ${PROJECT_ID} >/dev/null 2>&1; then
  gcloud tasks queues create ${QUEUE_NAME} \
    --location=${REGION} \
    --project ${PROJECT_ID} \
    --max-dispatches-per-second=100 \
    --max-concurrent-dispatches=50 \
    --max-attempts=3 \
    --min-backoff=10s \
    --max-backoff=300s \
    --max-retry-duration=1h
  echo "   ✅ Cloud Tasks queue created"
else
  echo "   ℹ️  Cloud Tasks queue already exists"
fi

# Create secrets (if they don't exist)
echo "🔑 Creating secrets in Secret Manager..."

# YouTube API Key
if ! gcloud secrets describe youtube-api-key --project ${PROJECT_ID} >/dev/null 2>&1; then
  echo -n "Enter YouTube API Key: "
  read -s YOUTUBE_KEY
  echo
  echo -n "${YOUTUBE_KEY}" | gcloud secrets create youtube-api-key \
    --data-file=- \
    --replication-policy="automatic" \
    --project ${PROJECT_ID}
  echo "   ✅ YouTube API key secret created"
else
  echo "   ℹ️  YouTube API key secret already exists"
fi

# Gemini API Key
if ! gcloud secrets describe gemini-api-key --project ${PROJECT_ID} >/dev/null 2>&1; then
  echo -n "Enter Gemini API Key: "
  read -s GEMINI_KEY
  echo
  echo -n "${GEMINI_KEY}" | gcloud secrets create gemini-api-key \
    --data-file=- \
    --replication-policy="automatic" \
    --project ${PROJECT_ID}
  echo "   ✅ Gemini API key secret created"
else
  echo "   ℹ️  Gemini API key secret already exists"
fi

# Grant service account access to secrets
echo "🔓 Granting secret access..."
gcloud secrets add-iam-policy-binding youtube-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project ${PROJECT_ID}

gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project ${PROJECT_ID}

echo "   ✅ Secret access granted"

# Create Firestore indexes (optional but recommended)
echo "📇 Creating Firestore indexes..."
cat > /tmp/firestore-indexes.yaml << EOF
indexes:
  - collectionGroup: video_processing_state
    queryScope: COLLECTION
    fields:
      - fieldPath: status
        order: ASCENDING
      - fieldPath: created_at
        order: DESCENDING

  - collectionGroup: video_processing_state
    queryScope: COLLECTION
    fields:
      - fieldPath: current_stage
        order: ASCENDING
      - fieldPath: updated_at
        order: DESCENDING
EOF

gcloud firestore indexes composite create \
  --field-config=field-path=status,order=ascending \
  --field-config=field-path=created_at,order=descending \
  --collection-group=video_processing_state \
  --project ${PROJECT_ID} \
  --quiet || echo "   ℹ️  Index creation failed (may already exist)"

echo ""
echo "✅ Cloud infrastructure setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Update Dockerfile with your configuration"
echo "   2. Run: ./infrastructure/cloudrun/deploy.sh"
echo "   3. Test your deployment"
echo ""
echo "🔗 Useful commands:"
echo "   View Cloud Run services: gcloud run services list --project ${PROJECT_ID}"
echo "   View Cloud Tasks queues: gcloud tasks queues list --location ${REGION} --project ${PROJECT_ID}"
echo "   View Firestore data: gcloud firestore export gs://BUCKET_NAME --project ${PROJECT_ID}"
echo ""

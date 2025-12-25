#!/bin/bash
# Setup script for Phase 3: Security
# Creates a dedicated Service Account and grants least-privilege access.

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-uvai-730bb}
SA_NAME="uvai-app-sa"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

echo "Using Project: $PROJECT_ID"
echo "Creating Service Account: $SA_EMAIL"

# 1. Create Service Account
if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" > /dev/null 2>&1; then
    echo "Service Account $SA_EMAIL already exists."
else
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="UVAI Application Service Account" \
        --project="$PROJECT_ID"
    echo "Created Service Account $SA_EMAIL"
fi

# 2. Grant Roles
echo "Granting roles to $SA_EMAIL..."

ROLES=(
    "roles/aiplatform.user"             # Vertex AI
    "roles/pubsub.publisher"            # Publish events
    "roles/pubsub.subscriber"           # Consume events
    "roles/storage.objectUser"          # GCS read/write
    "roles/secretmanager.secretAccessor" # Access secrets
    "roles/logging.logWriter"           # Write logs
    "roles/monitoring.metricWriter"     # Write metrics
    "roles/run.invoker"                 # Invoke other Run services (if needed)
)

for role in "${ROLES[@]}"; do
    echo "Granting $role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$role" \
        --condition=None
done

echo "Security setup complete!"
echo "Next steps: Update service.yaml to use serviceAccountName: $SA_EMAIL"

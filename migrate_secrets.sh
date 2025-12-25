#!/bin/bash
# Script to migrate secrets from cloudhub-470100 to uvai-730bb

SOURCE_PROJECT="cloudhub-470100"
TARGET_PROJECT="uvai-730bb"
SECRETS=("DB_PASSWORD" "GEMINI_API_KEY" "JWT_SECRET_KEY" "OPENAI_API_KEY" "YOUTUBE_API_KEY")

echo "Migrating secrets from $SOURCE_PROJECT to $TARGET_PROJECT..."

for SECRET in "${SECRETS[@]}"; do
    echo "Processing $SECRET..."
    
    # Check if secret exists in target
    if gcloud secrets describe "$SECRET" --project="$TARGET_PROJECT" > /dev/null 2>&1; then
        echo "Secret $SECRET already exists in $TARGET_PROJECT. Skipping creation."
    else
        echo "Creating secret $SECRET in $TARGET_PROJECT..."
        gcloud secrets create "$SECRET" --replication-policy="automatic" --project="$TARGET_PROJECT"
    fi

    # Read latest value from source
    echo "Reading value from $SOURCE_PROJECT..."
    VALUE=$(gcloud secrets versions access latest --secret="$SECRET" --project="$SOURCE_PROJECT")

    if [ -z "$VALUE" ]; then
        echo "Error: Could not read value for $SECRET from $SOURCE_PROJECT"
        continue
    fi

    # Add version to target
    echo "Adding version to $TARGET_PROJECT..."
    echo -n "$VALUE" | gcloud secrets versions add "$SECRET" --data-file=- --project="$TARGET_PROJECT"
done

echo "Secret migration complete."

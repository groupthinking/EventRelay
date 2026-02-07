#!/bin/bash
# Setup secrets in Google Secret Manager from local .env file
# Usage: ./setup-secrets.sh [path-to-env-file]

set -e

PROJECT_ID="${GCP_PROJECT_ID:-uvai-730bb}"
ENV_FILE="${1:-.env}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Secret Manager Setup ===${NC}"
echo "Project: ${PROJECT_ID}"
echo "Source: ${ENV_FILE}"
echo ""

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found at ${ENV_FILE}${NC}"
    echo "Please provide the path to your .env file"
    exit 1
fi

# Secrets to sync (add more as needed)
SECRETS=("GEMINI_API_KEY" "YOUTUBE_API_KEY" "OPENAI_API_KEY" "ANTHROPIC_API_KEY")

for secret_name in "${SECRETS[@]}"; do
    # Extract value from .env file
    value=$(grep "^${secret_name}=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'")

    if [ -z "$value" ]; then
        echo -e "${YELLOW}⚠ Skipping ${secret_name} (not found in .env)${NC}"
        continue
    fi

    # Check if secret exists
    if gcloud secrets describe "${secret_name}" --project="${PROJECT_ID}" &>/dev/null; then
        echo -e "${YELLOW}Updating existing secret: ${secret_name}${NC}"

        # Add new version
        echo -n "$value" | gcloud secrets versions add "${secret_name}" \
            --project="${PROJECT_ID}" \
            --data-file=-
    else
        echo -e "${GREEN}Creating new secret: ${secret_name}${NC}"

        echo -n "$value" | gcloud secrets create "${secret_name}" \
            --project="${PROJECT_ID}" \
            --replication-policy="automatic" \
            --data-file=-
    fi

    echo -e "${GREEN}✓ ${secret_name} synced${NC}"
done

echo ""
echo -e "${GREEN}=== Secret Setup Complete ===${NC}"
echo ""
echo "To verify secrets:"
echo "  gcloud secrets list --project=${PROJECT_ID}"
echo ""
echo "To grant Cloud Run access (run once per service account):"
echo "  gcloud secrets add-iam-policy-binding GEMINI_API_KEY \\"
echo "    --project=${PROJECT_ID} \\"
echo "    --member=serviceAccount:uvai-backend@${PROJECT_ID}.iam.gserviceaccount.com \\"
echo "    --role=roles/secretmanager.secretAccessor"

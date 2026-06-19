#!/bin/bash
# Deploy UVAI Backend to Cloud Run
# Usage: ./deploy.sh [--build-only] [--no-push]

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-uvai-730bb}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE_NAME="uvai-backend"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
TAG="${IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== UVAI Backend Cloud Run Deployment ===${NC}"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Image: ${IMAGE_NAME}:${TAG}"
echo ""

# Parse arguments
BUILD_ONLY=false
NO_PUSH=false
for arg in "$@"; do
    case $arg in
        --build-only)
            BUILD_ONLY=true
            ;;
        --no-push)
            NO_PUSH=true
            ;;
    esac
done

# Step 1: Build the Docker image
echo -e "${YELLOW}Step 1: Building Docker image...${NC}"
cd "$(dirname "$0")/../.."  # Navigate to repo root

docker build \
    --platform linux/amd64 \
    -t "${IMAGE_NAME}:${TAG}" \
    -f Dockerfile \
    .

echo -e "${GREEN}✓ Docker image built successfully${NC}"

if [ "$BUILD_ONLY" = true ]; then
    echo -e "${YELLOW}Build-only mode. Exiting.${NC}"
    exit 0
fi

# Step 2: Push to Google Container Registry
if [ "$NO_PUSH" = false ]; then
    echo -e "${YELLOW}Step 2: Pushing image to GCR...${NC}"

    # Configure Docker for GCR authentication
    gcloud auth configure-docker gcr.io --quiet

    docker push "${IMAGE_NAME}:${TAG}"
    echo -e "${GREEN}✓ Image pushed to GCR${NC}"
else
    echo -e "${YELLOW}Skipping push (--no-push flag set)${NC}"
fi

# Step 3: Ensure secrets exist in Secret Manager
echo -e "${YELLOW}Step 3: Checking Secret Manager secrets...${NC}"

check_or_create_secret() {
    local secret_name=$1
    local env_var_name=$2

    if ! gcloud secrets describe "${secret_name}" --project="${PROJECT_ID}" &>/dev/null; then
        echo -e "${YELLOW}Creating secret: ${secret_name}${NC}"

        # Check if we have the value in environment
        if [ -z "${!env_var_name}" ]; then
            echo -e "${RED}Error: ${env_var_name} not set. Please set it or create the secret manually.${NC}"
            return 1
        fi

        echo -n "${!env_var_name}" | gcloud secrets create "${secret_name}" \
            --project="${PROJECT_ID}" \
            --data-file=-
    else
        echo -e "${GREEN}✓ Secret exists: ${secret_name}${NC}"
    fi
}

check_or_create_secret "GEMINI_API_KEY" "GEMINI_API_KEY"
check_or_create_secret "YOUTUBE_API_KEY" "YOUTUBE_API_KEY"

# Step 4: Run database migrations (if DATABASE_URL is configured)
echo -e "${YELLOW}Step 4: Running database migrations...${NC}"

if [ -n "${DATABASE_URL:-}" ]; then
    docker run --rm \
        -e DATABASE_URL="${DATABASE_URL}" \
        "${IMAGE_NAME}:${TAG}" \
        python -m alembic upgrade head && \
        echo -e "${GREEN}✓ Database migrations applied${NC}" || \
        echo -e "${YELLOW}⚠ Migrations skipped (alembic not configured or no pending migrations)${NC}"
else
    echo -e "${YELLOW}⚠ DATABASE_URL not set, skipping migrations${NC}"
fi

# Step 5: Deploy to Cloud Run
echo -e "${YELLOW}Step 5: Deploying to Cloud Run...${NC}"

gcloud run deploy "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --image="${IMAGE_NAME}:${TAG}" \
    --platform=managed \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300s \
    --concurrency=80 \
    --min-instances=0 \
    --max-instances=10 \
    --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest,YOUTUBE_API_KEY=YOUTUBE_API_KEY:latest" \
    --set-env-vars="LOG_LEVEL=INFO,ENHANCED_ANALYSIS_DIR=/app/data/enhanced_analysis" \
    --allow-unauthenticated \
    --cpu-boost \
    --no-cpu-throttling

echo -e "${GREEN}✓ Deployment complete${NC}"

# Step 6: Get the service URL
echo -e "${YELLOW}Step 6: Getting service URL...${NC}"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(status.url)')

echo ""
echo -e "${GREEN}=== Deployment Successful ===${NC}"
echo "Service URL: ${SERVICE_URL}"
echo ""

# Step 7: Map custom domain api.uvai.io (idempotent)
echo -e "${YELLOW}Step 7: Mapping custom domain api.uvai.io...${NC}"

if gcloud run domain-mappings describe \
    --domain=api.uvai.io \
    --region="${REGION}" \
    --project="${PROJECT_ID}" &>/dev/null; then
    echo -e "${GREEN}✓ Domain mapping already exists for api.uvai.io${NC}"
else
    gcloud run domain-mappings create \
        --service="${SERVICE_NAME}" \
        --domain=api.uvai.io \
        --region="${REGION}" \
        --project="${PROJECT_ID}"
    echo -e "${GREEN}✓ Domain mapping created for api.uvai.io${NC}"
    echo ""
    echo "ACTION REQUIRED: Add the following DNS records to GoDaddy for uvai.io:"
    gcloud run domain-mappings describe \
        --domain=api.uvai.io \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --format='value(status.resourceRecords)'
fi

echo ""
echo "Quick verification commands:"
echo "  curl ${SERVICE_URL}/api/v1/health"
echo "  curl https://api.uvai.io/api/v1/health"
echo "  curl -X POST ${SERVICE_URL}/api/v1/chat -H 'Content-Type: application/json' -d '{\"message\": \"Hello\"}'"

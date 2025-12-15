#!/bin/bash
# EventRelay Cloud Run Deployment Script
# 
# This script simplifies the deployment of EventRelay to Google Cloud Run
# with proper configuration and secrets management.
#
# Usage:
#   ./deploy-cloud-run.sh [environment] [options]
#
# Examples:
#   ./deploy-cloud-run.sh production --project my-project --region us-central1
#   ./deploy-cloud-run.sh staging --no-traffic
#   ./deploy-cloud-run.sh production --setup-secrets

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="eventrelay-api"
ARTIFACT_REPO="eventrelay-repo"
MEMORY="2Gi"
CPU="2"
MIN_INSTANCES="0"
MAX_INSTANCES="10"
TIMEOUT="300"
ALLOW_UNAUTHENTICATED="true"
SETUP_SECRETS="false"
NO_TRAFFIC="false"
DRY_RUN="false"

# Check for help flag first
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
  echo "Usage: $0 [environment] [options]"
  echo ""
  echo "Environments: production, staging, development"
  echo ""
  echo "Options:"
  echo "  --project PROJECT_ID        GCP project ID"
  echo "  --region REGION             GCP region (default: us-central1)"
  echo "  --service-name NAME         Cloud Run service name (default: eventrelay-api)"
  echo "  --memory SIZE               Memory allocation (default: 2Gi)"
  echo "  --cpu COUNT                 CPU allocation (default: 2)"
  echo "  --min-instances COUNT       Minimum instances (default: 0)"
  echo "  --max-instances COUNT       Maximum instances (default: 10)"
  echo "  --setup-secrets             Set up Secret Manager secrets"
  echo "  --no-traffic                Deploy without traffic (for testing)"
  echo "  --no-auth                   Require authentication"
  echo "  --dry-run                   Show commands without executing"
  echo "  --help                      Show this help message"
  exit 0
fi

# Get environment from first argument
ENVIRONMENT="${1:-production}"

# Parse command line arguments
shift || true
while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      PROJECT_ID="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --service-name)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --memory)
      MEMORY="$2"
      shift 2
      ;;
    --cpu)
      CPU="$2"
      shift 2
      ;;
    --min-instances)
      MIN_INSTANCES="$2"
      shift 2
      ;;
    --max-instances)
      MAX_INSTANCES="$2"
      shift 2
      ;;
    --setup-secrets)
      SETUP_SECRETS="true"
      shift
      ;;
    --no-traffic)
      NO_TRAFFIC="true"
      shift
      ;;
    --no-auth)
      ALLOW_UNAUTHENTICATED="false"
      shift
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Functions
log_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
  echo -e "${RED}❌ $1${NC}"
}

run_cmd() {
  if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}[DRY RUN]${NC} $*"
  else
    log_info "Running: $*"
    "$@"
  fi
}

# Banner
echo ""
echo "======================================="
echo "   EventRelay Cloud Run Deployment"
echo "======================================="
echo ""

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(production|staging|development)$ ]]; then
  log_error "Invalid environment: $ENVIRONMENT"
  log_error "Valid environments: production, staging, development"
  exit 1
fi

log_info "Environment: $ENVIRONMENT"

# Get or validate project ID
if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
  if [ -z "$PROJECT_ID" ]; then
    log_error "No GCP project configured. Use --project or run 'gcloud config set project PROJECT_ID'"
    exit 1
  fi
fi

log_info "Project ID: $PROJECT_ID"
log_info "Region: $REGION"
log_info "Service Name: $SERVICE_NAME"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
  log_error "gcloud CLI not found. Please install Google Cloud SDK."
  exit 1
fi

# Check authentication
log_info "Checking authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
  log_error "Not authenticated. Run 'gcloud auth login'"
  exit 1
fi
log_success "Authenticated"

# Set project
run_cmd gcloud config set project "$PROJECT_ID"

# Setup secrets if requested
if [ "$SETUP_SECRETS" = "true" ]; then
  log_info "Setting up Secret Manager secrets..."
  
  # Enable Secret Manager API
  run_cmd gcloud services enable secretmanager.googleapis.com
  
  # Create secrets (will prompt for values)
  for secret in gemini-api-key openai-api-key jwt-secret session-secret oauth-secret; do
    if gcloud secrets describe "$secret" &>/dev/null; then
      log_warning "Secret $secret already exists, skipping..."
    else
      log_info "Creating secret: $secret"
      if [ "$DRY_RUN" = "false" ]; then
        read -rsp "Enter value for $secret: " secret_value
        echo ""
        echo -n "$secret_value" | gcloud secrets create "$secret" --data-file=-
        log_success "Created secret: $secret"
      fi
    fi
  done
  
  # Grant access to default compute service account
  log_info "Granting service account access to secrets..."
  PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
  SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
  
  for secret in gemini-api-key openai-api-key jwt-secret session-secret oauth-secret; do
    run_cmd gcloud secrets add-iam-policy-binding "$secret" \
      --member="serviceAccount:${SERVICE_ACCOUNT}" \
      --role="roles/secretmanager.secretAccessor"
  done
  
  log_success "Secrets setup complete"
fi

# Enable required APIs
log_info "Enabling required Google Cloud APIs..."
run_cmd gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

# Check if Artifact Registry repository exists
log_info "Checking Artifact Registry repository..."
if ! gcloud artifacts repositories describe "$ARTIFACT_REPO" --location="$REGION" &>/dev/null; then
  log_warning "Artifact Registry repository not found. Creating..."
  run_cmd gcloud artifacts repositories create "$ARTIFACT_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="EventRelay container images"
  log_success "Created Artifact Registry repository"
else
  log_success "Artifact Registry repository exists"
fi

# Configure Docker authentication
log_info "Configuring Docker authentication..."
run_cmd gcloud auth configure-docker "${REGION}-docker.pkg.dev"

# Build and push image
IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/${SERVICE_NAME}:latest"
log_info "Building container image: $IMAGE_TAG"

run_cmd docker build -f Dockerfile.production -t "$IMAGE_TAG" .

if [ "$DRY_RUN" = "false" ]; then
  log_info "Pushing container image..."
  run_cmd docker push "$IMAGE_TAG"
  log_success "Image pushed successfully"
fi

# Prepare deployment command
DEPLOY_CMD=(
  gcloud run deploy "$SERVICE_NAME"
  --image "$IMAGE_TAG"
  --region "$REGION"
  --platform managed
  --memory "$MEMORY"
  --cpu "$CPU"
  --timeout "$TIMEOUT"
  --concurrency 80
  --min-instances "$MIN_INSTANCES"
  --max-instances "$MAX_INSTANCES"
  --port 8000
  --set-env-vars "ENVIRONMENT=$ENVIRONMENT,DEBUG=false,LOG_LEVEL=INFO,LOG_FORMAT=json"
)

# Add authentication flag
if [ "$ALLOW_UNAUTHENTICATED" = "true" ]; then
  DEPLOY_CMD+=(--allow-unauthenticated)
else
  DEPLOY_CMD+=(--no-allow-unauthenticated)
fi

# Add no-traffic flag if specified
if [ "$NO_TRAFFIC" = "true" ]; then
  DEPLOY_CMD+=(--no-traffic)
  log_warning "Deploying with --no-traffic flag (no traffic will be routed)"
fi

# Add secrets if they exist
SECRETS=()
for secret in gemini-api-key openai-api-key jwt-secret session-secret oauth-secret; do
  if gcloud secrets describe "$secret" &>/dev/null; then
    case $secret in
      gemini-api-key)
        SECRETS+=("GEMINI_API_KEY=$secret:latest")
        ;;
      openai-api-key)
        SECRETS+=("OPENAI_API_KEY=$secret:latest")
        ;;
      jwt-secret)
        SECRETS+=("JWT_SECRET_KEY=$secret:latest")
        ;;
      session-secret)
        SECRETS+=("SESSION_SECRET_KEY=$secret:latest")
        ;;
      oauth-secret)
        SECRETS+=("OAUTH_SECRET_KEY=$secret:latest")
        ;;
    esac
  fi
done

if [ ${#SECRETS[@]} -gt 0 ]; then
  DEPLOY_CMD+=(--set-secrets "$(IFS=,; echo "${SECRETS[*]}")")
  log_info "Attaching ${#SECRETS[@]} secrets to service"
fi

# Deploy to Cloud Run
log_info "Deploying to Cloud Run..."
run_cmd "${DEPLOY_CMD[@]}"

if [ "$DRY_RUN" = "false" ]; then
  log_success "Deployment complete!"
  
  # Get service URL
  SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --format="value(status.url)" 2>/dev/null)
  
  if [ -n "$SERVICE_URL" ]; then
    echo ""
    echo "======================================="
    echo "   Deployment Information"
    echo "======================================="
    echo "Service URL: $SERVICE_URL"
    echo "Environment: $ENVIRONMENT"
    echo "Region: $REGION"
    echo "Memory: $MEMORY"
    echo "CPU: $CPU"
    echo "Min Instances: $MIN_INSTANCES"
    echo "Max Instances: $MAX_INSTANCES"
    echo ""
    echo "Health Check: $SERVICE_URL/api/v1/health"
    echo "API Docs: $SERVICE_URL/docs"
    echo ""
    log_info "Test the deployment:"
    echo "  curl $SERVICE_URL/api/v1/health"
    echo ""
    log_info "View logs:"
    echo "  gcloud run services logs tail $SERVICE_NAME --region $REGION"
    echo ""
  fi
else
  log_info "Dry run complete. No changes were made."
fi

exit 0

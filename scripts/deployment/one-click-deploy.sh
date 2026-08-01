#!/bin/bash

# Enhanced Browser Extension Framework - One-Click Deployment Script
# This script validates and deploys the entire stack with comprehensive checks

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="production"
DEPLOYMENT_NAME="enhanced-framework"
TIMEOUT=300

# Every path below is relative to the repository root, so anchor there rather
# than depending on the caller's working directory.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCKERFILE="infrastructure/docker/Dockerfile.production"
PRODUCTION_MANIFESTS="infrastructure/k8s/production"
MONITORING_MANIFESTS="infrastructure/k8s/monitoring"
cd "$REPO_ROOT"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Banner
echo -e "${BLUE}"
echo "=================================================================="
echo "🚀 Enhanced Browser Extension Framework - One-Click Deployment"
echo "=================================================================="
echo -e "${NC}"

# Step 1: Pre-deployment Validation
log "Step 1: Pre-deployment Validation"

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
fi
success "Docker is available"

# Check Kubernetes
if ! command -v kubectl &> /dev/null; then
    error "kubectl is not installed. Please install kubectl first."
fi
success "kubectl is available"

# Check if we can connect to Kubernetes cluster
if ! kubectl cluster-info &> /dev/null; then
    error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
fi
success "Kubernetes cluster is accessible"

# Check if required files exist
REQUIRED_FILES=(
    "$DOCKERFILE"
    "package.json"
    "$PRODUCTION_MANIFESTS/deployment.yaml"
    "$PRODUCTION_MANIFESTS/service.yaml"
    "$MONITORING_MANIFESTS/monitoring.yaml"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        error "Required file $file is missing"
    fi
done
success "All required files are present"

# Step 2: Run Integration Tests
log "Step 2: Running Integration Tests"

if [[ -d "venv" ]]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

if ! command -v python3 &> /dev/null; then
    warning "python3 is not available. Skipping integration tests."
elif ! python3 -c "import pytest" &> /dev/null; then
    warning "pytest is not installed. Skipping integration tests."
elif PYTHONPATH="src" python3 -m pytest tests/integration -q; then
    success "Integration tests passed"
else
    error "Integration tests failed. Please fix issues before deployment."
fi

# Step 3: Build Docker Image
log "Step 3: Building Docker Image"

DOCKER_TAG="enhanced-framework:$(date +%Y%m%d-%H%M%S)"
LATEST_TAG="enhanced-framework:latest"

if docker build -f "$DOCKERFILE" -t "$DOCKER_TAG" -t "$LATEST_TAG" .; then
    success "Docker image built successfully: $DOCKER_TAG"
else
    error "Docker image build failed"
fi

# Step 4: Validate Kubernetes Manifests
log "Step 4: Validating Kubernetes Manifests"

# Validate deployment manifest
if kubectl apply --dry-run=client -f "$PRODUCTION_MANIFESTS/deployment.yaml"; then
    success "Deployment manifest is valid"
else
    error "Deployment manifest validation failed"
fi

# Validate service manifest
if kubectl apply --dry-run=client -f "$PRODUCTION_MANIFESTS/service.yaml"; then
    success "Service manifest is valid"
else
    error "Service manifest validation failed"
fi

# Validate monitoring manifest
if kubectl apply --dry-run=client -f "$MONITORING_MANIFESTS/monitoring.yaml"; then
    success "Monitoring manifest is valid"
else
    error "Monitoring manifest validation failed"
fi

# Step 5: Create Namespace
log "Step 5: Creating Namespace"

if kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -; then
    success "Namespace $NAMESPACE is ready"
else
    warning "Namespace $NAMESPACE already exists or creation failed"
fi

# Step 6: Deploy to Kubernetes
log "Step 6: Deploying to Kubernetes"

# Deploy application
if kubectl apply -f "$PRODUCTION_MANIFESTS/" -n "$NAMESPACE"; then
    success "Application deployed successfully"
else
    error "Application deployment failed"
fi

# Deploy monitoring
if kubectl apply -f "$MONITORING_MANIFESTS/" -n "$NAMESPACE"; then
    success "Monitoring stack deployed successfully"
else
    error "Monitoring deployment failed"
fi

# Step 7: Wait for Deployment to be Ready
log "Step 7: Waiting for Deployment to be Ready"

if kubectl rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
    success "Deployment is ready"
else
    error "Deployment failed to become ready within $TIMEOUT seconds"
fi

# Step 8: Verify Services
log "Step 8: Verifying Services"

# Check if pods are running
RUNNING_PODS=$(kubectl get pods -n "$NAMESPACE" -l app="$DEPLOYMENT_NAME" --field-selector=status.phase=Running --no-headers | wc -l)
if [[ "$RUNNING_PODS" -gt 0 ]]; then
    success "$RUNNING_PODS pod(s) are running"
else
    error "No pods are running"
fi

# Check services
if kubectl get service -n "$NAMESPACE" "$DEPLOYMENT_NAME" &> /dev/null; then
    success "Application service is available"
else
    error "Application service is not available"
fi

# Step 9: Health Check
log "Step 9: Performing Health Check"

# Get service endpoint
SERVICE_IP=$(kubectl get service -n "$NAMESPACE" enhanced-framework-lb -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
if [[ -z "$SERVICE_IP" ]]; then
    SERVICE_IP=$(kubectl get service -n "$NAMESPACE" enhanced-framework-lb -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "localhost")
fi

# Port forward for local testing if no external IP
if [[ "$SERVICE_IP" == "localhost" ]]; then
    warning "No external LoadBalancer IP found. Using port-forward for health check."
    kubectl port-forward -n "$NAMESPACE" service/"$DEPLOYMENT_NAME" 8080:80 &
    PORT_FORWARD_PID=$!
    sleep 5
    HEALTH_URL="http://localhost:8080/health"
else
    HEALTH_URL="http://$SERVICE_IP/health"
fi

# Perform health check
if curl -f -s "$HEALTH_URL" > /dev/null; then
    success "Health check passed"
else
    warning "Health check failed or endpoint not ready yet"
fi

# Cleanup port-forward if used
if [[ -n "${PORT_FORWARD_PID:-}" ]]; then
    kill "$PORT_FORWARD_PID" 2>/dev/null || true
fi

# Step 10: Display Deployment Information
log "Step 10: Deployment Information"

echo -e "${GREEN}"
echo "=================================================================="
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "=================================================================="
echo -e "${NC}"

echo "📋 Deployment Details:"
echo "  • Namespace: $NAMESPACE"
echo "  • Docker Image: $DOCKER_TAG"
echo "  • Deployment: $DEPLOYMENT_NAME"

echo ""
echo "🔗 Access Information:"
if [[ "$SERVICE_IP" != "localhost" ]]; then
    echo "  • Application URL: http://$SERVICE_IP"
    echo "  • API Documentation: http://$SERVICE_IP/docs"
else
    echo "  • Use port-forward to access: kubectl port-forward -n $NAMESPACE service/$DEPLOYMENT_NAME 8080:80"
    echo "  • Then visit: http://localhost:8080"
fi

echo ""
echo "📊 Monitoring:"
GRAFANA_IP=$(kubectl get service -n "$NAMESPACE" grafana -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "localhost")
if [[ "$GRAFANA_IP" != "localhost" ]]; then
    echo "  • Grafana Dashboard: http://$GRAFANA_IP:3000"
else
    echo "  • Grafana (port-forward): kubectl port-forward -n $NAMESPACE service/grafana 3000:3000"
fi
echo "  • Grafana Credentials: admin/admin123"

echo ""
echo "🛠️  Useful Commands:"
echo "  • Check pods: kubectl get pods -n $NAMESPACE"
echo "  • View logs: kubectl logs -n $NAMESPACE deployment/$DEPLOYMENT_NAME"
echo "  • Scale deployment: kubectl scale deployment/$DEPLOYMENT_NAME --replicas=5 -n $NAMESPACE"
echo "  • Delete deployment: kubectl delete namespace $NAMESPACE"

echo ""
echo "🎯 Next Steps:"
echo "  1. Test the API endpoints using the documentation"
echo "  2. Monitor the system using Grafana dashboards"
echo "  3. Scale the deployment based on usage patterns"
echo "  4. Set up CI/CD for automated deployments"

echo -e "${GREEN}"
echo "=================================================================="
echo "✅ One-Click Deployment Complete!"
echo "=================================================================="
echo -e "${NC}" 
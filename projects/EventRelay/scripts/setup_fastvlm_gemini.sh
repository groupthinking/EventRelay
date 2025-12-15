#!/bin/bash

# FastVLM + Gemini Hybrid System Setup Script

echo "========================================="
echo "FastVLM + Gemini Hybrid System Setup"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Determine working directory (prefer /workspace if present, else script directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -d "/workspace" ]; then
    WORK_DIR="/workspace"
else
    WORK_DIR="${SCRIPT_DIR}"
fi
print_status "Using work directory: ${WORK_DIR}"

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_status "Python $PYTHON_VERSION found"
else
    print_error "Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

# Check if FastVLM repo exists
echo ""
echo "Checking FastVLM repository..."
FASTVLM_DIR="${WORK_DIR}/ml-fastvlm"
if [ -d "${FASTVLM_DIR}" ]; then
    print_status "FastVLM repository found at ${FASTVLM_DIR}"
else
    print_warning "FastVLM repository not found. Cloning to ${FASTVLM_DIR}..."
    mkdir -p "${WORK_DIR}" 2>/dev/null || true
    git clone https://github.com/apple/ml-fastvlm.git "${FASTVLM_DIR}"
    if [ $? -eq 0 ]; then
        print_status "FastVLM repository cloned successfully"
    else
        print_error "Failed to clone FastVLM repository"
        exit 1
    fi
fi

# Install Python dependencies via pyproject extras
echo ""
echo "Installing Python dependencies (editable extras)..."

if [ -f "${WORK_DIR}/pyproject.toml" ]; then
    PROJECT_ROOT="${WORK_DIR}"
elif [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
    PROJECT_ROOT="${SCRIPT_DIR}"
else
    print_error "Unable to locate pyproject.toml; run this script from the repo root."
    exit 1
fi

pip3 install -q -e "${PROJECT_ROOT}[youtube,ml]"
if [ $? -eq 0 ]; then
    print_status "Project dependencies installed"
else
    print_warning "pip install reported issues; review the output above"
fi

# macOS torch fallback if pinned version unavailable
OS_NAME="$(uname -s)"
if [ "${OS_NAME}" = "Darwin" ]; then
    TORCH_VER=$(python3 - <<'PY'
try:
    import torch
    print(getattr(torch, "__version__", ""))
except Exception:
    print("")
PY
)
    case "${TORCH_VER}" in
        2.6.*)
            print_status "Pinned Torch version detected (${TORCH_VER})"
            ;;
        *)
            print_warning "Pinned Torch not available on macOS (found '${TORCH_VER:-none}'). Attempting fallback torch==2.2.2, torchvision==0.17.2"
            pip3 install -q "torch==2.2.2" "torchvision==0.17.2" || print_warning "Torch fallback install encountered issues"
            ;;
    esac
fi

# Download FastVLM models (optional)
echo ""

# Support non-interactive environments (CI) via NON_INTERACTIVE/AUTO_DOWNLOAD_MODELS
if [ -n "$CI" ] || [ "${NON_INTERACTIVE:-}" = "1" ]; then
    REPLY=${AUTO_DOWNLOAD_MODELS:-n}
    echo "Non-interactive mode detected (CI=$CI, NON_INTERACTIVE=${NON_INTERACTIVE:-0}). AUTO_DOWNLOAD_MODELS=${REPLY}"
else
    read -p "Do you want to download FastVLM models? This may take a while (y/n): " -n 1 -r
    echo
fi

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Downloading FastVLM models..."
    cd "${FASTVLM_DIR}"
    bash get_models.sh
    if [ $? -eq 0 ]; then
        print_status "Models downloaded successfully"
    else
        print_warning "Model download may have encountered issues"
    fi
    cd "${WORK_DIR}"
fi

# Check for API keys
echo ""
echo "Checking API configuration..."
if [ -z "$GEMINI_API_KEY" ]; then
    print_warning "GEMINI_API_KEY not set. Gemini features will be disabled."
    echo "To enable Gemini, set: export GEMINI_API_KEY='your-api-key'"
else
    print_status "Gemini API key configured"
fi

if [ -z "$FASTVLM_MODEL_PATH" ]; then
    print_warning "FASTVLM_MODEL_PATH not set. Using default path."
    export FASTVLM_MODEL_PATH="${WORK_DIR}/checkpoints/fastvlm_0.5b_stage3"
else
    print_status "FastVLM model path configured"
fi

# Create example .env file
echo ""
echo "Creating example .env file..."
mkdir -p "${WORK_DIR}" 2>/dev/null || true
cat > "${WORK_DIR}/.env.example" << EOF
# FastVLM Configuration
FASTVLM_MODEL_PATH=${WORK_DIR}/checkpoints/fastvlm_0.5b_stage3
FASTVLM_DEVICE=mps  # Use 'cuda' for NVIDIA GPUs

# Gemini Configuration
GEMINI_API_KEY=your-gemini-api-key
GOOGLE_CLOUD_PROJECT=your-project-id  # Optional for Vertex AI
GEMINI_MODEL=gemini-2.0-flash-exp

# Hybrid Configuration
HYBRID_MODE=auto
ROUTING_THRESHOLD=0.7
CACHE_ENABLED=true
EOF
if [ -f "${WORK_DIR}/.env.example" ]; then
    print_status "Example .env file created at ${WORK_DIR}/.env.example"
else
    print_warning "Failed to create example .env file at ${WORK_DIR}/.env.example"
fi

# Test the installation
echo ""
echo "Testing installation..."
python3 -c "
try:
    import torch
    import importlib
    print('✓ PyTorch installed:', torch.__version__)
except:
    print('✗ PyTorch not installed')

try:
    import cv2
    print('✓ OpenCV installed:', cv2.__version__)
except Exception as e:
    print(f'✗ OpenCV not installed: {e}')

try:
    import google.generativeai
    print('✓ Google Generative AI installed')
except Exception as e:
    print(f'✗ Google Generative AI not installed: {e}')

try:
    from fastvlm_gemini_hybrid import HybridVLMProcessor
    print('✓ Hybrid system modules accessible')
except Exception as e:
    print(f'✗ Hybrid system modules not accessible: {e}')

try:
    import youtube_transcript_api
    print('✓ youtube-transcript-api installed:', youtube_transcript_api.__version__ if hasattr(youtube_transcript_api, '__version__') else 'unknown')
except Exception as e:
    print(f'✗ youtube-transcript-api not installed: {e}')

try:
    import youtubesearchpython
    print('✓ youtube-search-python installed')
except Exception as e:
    print(f'✗ youtube-search-python not installed: {e}')

try:
    import pytube
    print('✓ pytube installed:', getattr(pytube, '__version__', 'unknown'))
except Exception as e:
    print(f'✗ pytube not installed: {e}')

try:
    import numpy as np
    print('✓ NumPy installed:', np.__version__)
except Exception as e:
    print(f'✗ NumPy not installed: {e}')
"

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Set your API keys:"
echo "   export GEMINI_API_KEY='your-api-key'"
echo "   export FASTVLM_MODEL_PATH='/path/to/model'"
echo ""
echo "2. Run examples:"
echo "   python3 ${WORK_DIR}/examples/basic_usage.py"
echo "   python3 ${WORK_DIR}/examples/advanced_integration.py"
echo ""
echo "3. Read documentation:"
echo "   ${WORK_DIR}/FASTVLM_GEMINI_INTEGRATION.md"
echo ""
print_status "Setup completed successfully!"

#!/usr/bin/env bash

set -Eeuo pipefail

# Simple, repeatable setup + run script for the YouTube Extension API
# - Creates a venv
# - Installs dependencies (avoids problematic extras like bitsandbytes on macOS)
# - Installs local FastVLM repo in editable mode without pulling its heavy pinned deps
# - Exports required env vars and starts the API

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
VENV_DIR="${REPO_ROOT}/.venv"

HOST="0.0.0.0"
PORT="8000"
RUN_SERVER=1
VERIFY=0

usage() {
  cat <<USAGE
Usage: $(basename "$0") [options]

Options:
  --host <host>        Server host (default: ${HOST})
  --port <port>        Server port (default: ${PORT})
  --no-run             Do not start the server after setup
  --verify             Start server in background and verify /api/v1/capabilities
  -h, --help           Show this help

Examples:
  bash $0 --port 8010
  bash $0 --no-run
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --no-run) RUN_SERVER=0; shift;;
    --verify) VERIFY=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown option: $1" >&2; usage; exit 1;;
  esac
done

echo "[info] Repo root: ${REPO_ROOT}"
echo "[info] Python venv: ${VENV_DIR}"

step() { echo -e "\n[step] $*"; }
ok() { echo "[ok] $*"; }
warn() { echo "[warn] $*"; }
die() { echo "[error] $*" >&2; exit 1; }

is_macos() { [[ "$(uname -s)" == "Darwin" ]]; }

ensure_python() {
  step "Checking Python (>=3.9)"
  if ! command -v python3 >/dev/null 2>&1; then
    die "python3 not found. Please install Python 3.9+ and rerun."
  fi
  local pyv
  pyv=$(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])')
  local maj=${pyv%%.*}
  local min=${pyv##*.}
  if (( maj < 3 || (maj==3 && min < 9) )); then
    die "Python ${pyv} detected. Require >= 3.9."
  fi
  ok "Python ${pyv} available"
}

create_venv() {
  step "Creating venv if missing"
  if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}" || die "Failed to create venv"
  fi
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  ok "Venv activated: $(python -c 'import sys; print(sys.executable)')"
}

install_base_tools() {
  step "Upgrading pip/setuptools/wheel"
  pip install -U pip setuptools wheel >/dev/null
  ok "Upgraded pip tooling"
}

install_torch_stack() {
  step "Installing PyTorch stack"
  # Plain install allows pip to pick the right wheel for the platform
  pip install "torch" "torchvision" "torchaudio" >/dev/null || die "Failed to install torch stack"
  ok "Installed torch stack"
}

install_project_package() {
  step "Installing project (editable)"
  pip install -e .[youtube] >/dev/null || die "Failed to install project"
  ok "Project installed"
}

install_fastvlm_repo() {
  step "Installing FastVLM (editable, no deps)"
  if [[ ! -d "${REPO_ROOT}/ml-fastvlm" ]]; then
    die "ml-fastvlm directory not found at ${REPO_ROOT}/ml-fastvlm"
  fi
  pip install -e "${REPO_ROOT}/ml-fastvlm" --no-deps >/dev/null || die "Failed to install ml-fastvlm"
  ok "FastVLM installed"
}

install_runtime_libs() {
  step "Installing runtime libraries"
  # Match ml-fastvlm expectations but avoid problematic extras
  pip install \
    "transformers==4.48.3" \
    "tokenizers==0.21.0" \
    "accelerate==1.6.0" \
    "peft>=0.10.0,<0.14.0" \
    "timm==1.0.15" \
    "einops==0.6.1" \
    "einops-exts==0.0.4" \
    "numpy==1.26.4" \
    "pydantic" \
    "Pillow" \
    "shortuuid" \
    "uvicorn" \
    "fastapi" \
    "google-generativeai" >/dev/null || die "Failed to install runtime libs"
  ok "Runtime libraries installed"

}

install_sentencepiece() {
  step "Installing sentencepiece (wheel-only)"
  local versions
  if [[ -n "${SENTENCEPIECE_VERSION:-}" ]]; then
    versions=("${SENTENCEPIECE_VERSION}")
  else
    versions=("0.2.0" "0.1.99")
  fi

  for version in "${versions[@]}"; do
    echo "[info] Attempting sentencepiece==${version}"
    if pip install --only-binary=:all: "sentencepiece==${version}" >/dev/null 2>&1; then
      ok "sentencepiece ${version} installed"
      return
    fi
    warn "No compatible wheel for sentencepiece==${version}; skipping"
  done

  warn "sentencepiece not installed; install manually if required (set SENTENCEPIECE_VERSION to override)."
}

set_env_vars() {
  step "Setting environment variables"
  export FASTVLM_REPO_PATH="${REPO_ROOT}/ml-fastvlm"
  local default_model="${REPO_ROOT}/ml-fastvlm/checkpoints/llava-fastvithd_0.5b_stage3"
  export FASTVLM_MODEL_PATH="${FASTVLM_MODEL_PATH:-$default_model}"
  local runtime_dir="${REPO_ROOT}/.runtime"
  local default_db_path="${runtime_dir}/app.db"

  if [[ -z "${DATABASE_URL:-}" ]]; then
    mkdir -p "${runtime_dir}"
    export DATABASE_URL="sqlite:////${default_db_path#/}"
    ok "DATABASE_URL defaulted to ${DATABASE_URL}"
  else
    local db_url="${DATABASE_URL}"
    if [[ "${db_url}" == sqlite:* ]]; then
      local path_part="${db_url#sqlite://}"
      if [[ "${path_part}" != ':memory:' && "${path_part}" != 'memory:' ]]; then
        local cleaned="/${path_part#//}"
        mkdir -p "$(dirname "${cleaned}")" || warn "Could not create directory for ${DATABASE_URL}"
      fi
    fi
    ok "DATABASE_URL=${DATABASE_URL}"
  fi

  # Avoid libiomp5 duplicate aborts on macOS/Intel by allowing duplicate OpenMP runtimes
  # and limit threads to avoid oversubscription on small CPUs.
  export KMP_DUPLICATE_LIB_OK=${KMP_DUPLICATE_LIB_OK:-TRUE}
  export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
  export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}
  export VECLIB_MAXIMUM_THREADS=${VECLIB_MAXIMUM_THREADS:-1}
  # Prefer safe fallback if a requested accelerator isn't available
  export PYTORCH_ENABLE_MPS_FALLBACK=${PYTORCH_ENABLE_MPS_FALLBACK:-1}

  if [[ ! -d "${FASTVLM_MODEL_PATH}" ]]; then
    warn "FASTVLM_MODEL_PATH does not exist: ${FASTVLM_MODEL_PATH}"
    warn "If needed, download checkpoints via ml-fastvlm/get_models.sh or update FASTVLM_MODEL_PATH."
  fi

  # Load .env from repo root if present for API keys
  if [[ -f "${REPO_ROOT}/.env" ]]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "${REPO_ROOT}/.env" | xargs -I{} echo {}) || true
  fi

  ok "FASTVLM_REPO_PATH=${FASTVLM_REPO_PATH}"
  ok "FASTVLM_MODEL_PATH=${FASTVLM_MODEL_PATH}"
  if [[ -n "${GEMINI_API_KEY:-}" ]]; then ok "GEMINI_API_KEY detected"; else warn "GEMINI_API_KEY not set"; fi
}

sanity_checks() {
  step "Running sanity checks"
  python - <<'PY'
import sys
ok = True
try:
    import llava  # from ml-fastvlm
    print("[ok] Imported llava", getattr(llava, "__version__", "(no __version__)"))
except Exception as e:
    print("[error] Failed to import llava:", e)
    ok = False

try:
    import fastapi, uvicorn
    print("[ok] Imported fastapi", fastapi.__version__)
except Exception as e:
    print("[error] Failed to import fastapi/uvicorn:", e)
    ok = False

sys.exit(0 if ok else 1)
PY
  ok "Sanity imports passed"
}

start_server_fg() {
  step "Starting API (foreground) at ${HOST}:${PORT}"
  exec uvicorn uvai.api.main:app --host "${HOST}" --port "${PORT}" --reload
}

start_server_bg_and_verify() {
  step "Starting API (background) at ${HOST}:${PORT}"
  uvicorn uvai.api.main:app --host "${HOST}" --port "${PORT}" --reload >/tmp/uvai_api.out 2>/tmp/uvai_api.err &
  local pid=$!
  echo "[info] uvicorn PID: ${pid}"

  # Wait for readiness (max ~20s)
  for i in {1..40}; do
    if curl -s "http://${HOST}:${PORT}/api/v1/health" >/dev/null; then
      ok "API is responding"
      break
    fi
    sleep 0.5
  done

  echo "[info] Capabilities:"
  curl -s "http://${HOST}:${PORT}/api/v1/capabilities" || true
  echo
  echo "[info] Tail last 200 lines of logs; use 'tail -f /tmp/uvai_api.out /tmp/uvai_api.err' to follow"
  tail -n 200 /tmp/uvai_api.out /tmp/uvai_api.err || true
}

main() {
  ensure_python
  create_venv
  install_base_tools
  install_torch_stack
  install_project_package
  install_fastvlm_repo
  install_runtime_libs
  install_sentencepiece
  set_env_vars
  sanity_checks

  if (( RUN_SERVER == 1 )); then
    if (( VERIFY == 1 )); then
      start_server_bg_and_verify
    else
      start_server_fg
    fi
  else
    ok "Setup complete. To start the API:"
    echo "  source ${VENV_DIR}/bin/activate"
    echo "  FASTVLM_REPO_PATH='${REPO_ROOT}/ml-fastvlm' FASTVLM_MODEL_PATH='${FASTVLM_MODEL_PATH}' uvicorn uvai.api.main:app --host ${HOST} --port ${PORT} --reload"
  fi
}

main "$@"

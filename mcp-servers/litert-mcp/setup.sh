#!/usr/bin/env bash
# Setup script for LiteRT-LM MCP server
# Downloads the `lit` CLI binary and a small .litertlm model
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
MODEL_DIR="$SCRIPT_DIR/models"

mkdir -p "$BIN_DIR" "$MODEL_DIR"

# --- 1. Download `lit` CLI binary ---
LIT_VERSION="${LIT_VERSION:-v0.8.1}"
ARCH="$(uname -m)"
case "$ARCH" in
  arm64|aarch64) ASSET="lit-macos-arm64" ;;
  x86_64)        ASSET="lit-macos-x86_64" ;;
  *)             echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

LIT_URL="https://github.com/google-ai-edge/LiteRT-LM/releases/download/${LIT_VERSION}/${ASSET}"
LIT_BIN="$BIN_DIR/lit"

if [ ! -x "$LIT_BIN" ]; then
  echo "Downloading lit binary (${LIT_VERSION}, ${ASSET})..."
  curl -fSL "$LIT_URL" -o "$LIT_BIN"
  chmod +x "$LIT_BIN"
  echo "✓ Downloaded to $LIT_BIN"
else
  echo "✓ lit binary already exists at $LIT_BIN"
fi

# --- 2. Download a small .litertlm model (Gemma 3n) ---
MODEL_NAME="${MODEL_NAME:-gemma3n-E2B-it-int4.litertlm}"
MODEL_URL="https://huggingface.co/litert-community/${MODEL_NAME%.litertlm}/resolve/main/${MODEL_NAME}"
MODEL_PATH="$MODEL_DIR/$MODEL_NAME"

if [ ! -f "$MODEL_PATH" ]; then
  echo "Downloading model ${MODEL_NAME} from HuggingFace..."
  echo "(This may take a while depending on model size)"
  curl -fSL "$MODEL_URL" -o "$MODEL_PATH"
  echo "✓ Downloaded to $MODEL_PATH"
else
  echo "✓ Model already exists at $MODEL_PATH"
fi

# --- 3. Write env file ---
ENV_FILE="$SCRIPT_DIR/.env"
cat > "$ENV_FILE" <<EOF
LIT_BINARY_PATH=$LIT_BIN
LIT_MODEL_PATH=$MODEL_PATH
EOF
echo "✓ Wrote $ENV_FILE"

echo ""
echo "Setup complete. Start the MCP server with:"
echo "  cd $SCRIPT_DIR"
echo "  export \$(cat .env | xargs)"
echo "  python3 server.py"

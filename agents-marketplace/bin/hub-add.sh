#!/usr/bin/env bash
# Usage: hub-add.sh <abs-path-to-source> <apps|agents|projects> [name]
set -euo pipefail
SRC="${1:?abs path required}"; CAT="${2:?apps|agents|projects}"; NAME="${3:-$(basename "$SRC")}"
ROOT="$HOME/Dev/OpenAI_Hub"
DEST="$ROOT/$CAT/$NAME"
mkdir -p "$ROOT/$CAT"
ln -snf "$SRC" "$DEST"
# Append to project_roots if missing
CFG="$HOME/.codex/config.toml"
grep -q "$DEST" "$CFG" || \
  awk -v ins="  \"$DEST\"," '
    BEGIN{done=0}
    /project_roots = \[/ {print; print ins; done=1; next}
    {print}
    END{if(!done){print "project_roots = [\n" ins "\n]"}}
  ' "$CFG" > "$CFG.tmp" && mv "$CFG.tmp" "$CFG"
echo "Added: $DEST"

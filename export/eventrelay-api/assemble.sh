#!/usr/bin/env bash
# Assemble a standalone EventRelay API repo from the monorepo's clean spine.
#
#   bash export/eventrelay-api/assemble.sh ../eventrelay-api
#
# Produces a fresh, self-contained tree (git history NOT carried — a clean root
# that escapes the monorepo's credential history). Verify, then `git init`.
set -euo pipefail

TARGET="${1:?usage: assemble.sh <target-dir>}"
BUNDLE="$(cd "$(dirname "$0")" && pwd)"            # export/eventrelay-api
ROOT="$(cd "$BUNDLE/../.." && pwd)"               # monorepo root

if [ -e "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null || true)" ]; then
  echo "error: target '$TARGET' exists and is not empty" >&2
  exit 1
fi
mkdir -p "$TARGET"

# 1. The package, verbatim (all imports are relative or service.app.* — no churn).
cp -R "$ROOT/service" "$TARGET/service"
find "$TARGET/service" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$TARGET/service" -name '*.py[cod]' -delete

# 2. Promote the Dockerfile to the repo root (its build context is already root:
#    `COPY service /srv/service`). Keep exactly one.
mv "$TARGET/service/Dockerfile" "$TARGET/Dockerfile"

# 3. Root scaffolding from this bundle.
for f in pyproject.toml README.md .gitignore .env.example Makefile EXTRACTION.md; do
  cp "$BUNDLE/$f" "$TARGET/$f"
done
mkdir -p "$TARGET/.github/workflows"
cp "$BUNDLE/.github/workflows/"*.yml "$TARGET/.github/workflows/"

# 4. Carry the governing docs so provenance/criteria travel with the code.
mkdir -p "$TARGET/docs"
for d in PORTING_PARAMETERS.md SC7_CUTOVER.md; do
  [ -f "$ROOT/docs/$d" ] && cp "$ROOT/docs/$d" "$TARGET/docs/$d"
done

echo "Assembled standalone repo at: $TARGET"
echo "Next:"
echo "  cd $TARGET && make install-dev && make test"
echo "  git init && git add -A && git commit -m 'chore: extract EventRelay API from monorepo spine'"

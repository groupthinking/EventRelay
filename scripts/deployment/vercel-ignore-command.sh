#!/usr/bin/env bash
set -euo pipefail

# Vercel ignored-build command semantics:
# - exit 0 => skip build
# - exit 1 => continue build
#
# We skip only when the diff is strictly docs/workflow metadata.

head_sha="${VERCEL_GIT_COMMIT_SHA:-}"
base_sha="${VERCEL_GIT_PREVIOUS_SHA:-}"

if [[ -z "${head_sha}" || -z "${base_sha}" ]]; then
  echo "preview-ignore: missing commit context; running build"
  exit 1
fi

if ! git cat-file -e "${head_sha}^{commit}" 2>/dev/null; then
  echo "preview-ignore: head commit not available locally; running build"
  exit 1
fi

if ! git cat-file -e "${base_sha}^{commit}" 2>/dev/null; then
  echo "preview-ignore: base commit not available locally; running build"
  exit 1
fi

mapfile -t changed < <(git diff --name-only "${base_sha}" "${head_sha}")
if [[ ${#changed[@]} -eq 0 ]]; then
  echo "preview-ignore: no changed files detected; running build"
  exit 1
fi

for path in "${changed[@]}"; do
  if [[ "${path}" == docs/* ]]; then
    continue
  fi
  if [[ "${path}" == .github/workflows/* ]]; then
    continue
  fi
  if [[ "${path}" == .github/ISSUE_TEMPLATE/* ]]; then
    continue
  fi
  if [[ "${path}" == .github/pull_request_template.md ]]; then
    continue
  fi
  if [[ "${path}" == *.md ]]; then
    continue
  fi

  echo "preview-ignore: app-impacting change detected (${path}); running build"
  exit 1
done

echo "preview-ignore: docs/workflow-only change; skipping preview build"
exit 0

#!/usr/bin/env bash
# RETIRED: direct deploys bypass migrations, pinned secrets, and rollout checks.
set -euo pipefail

echo "RETIRED: use .github/workflows/deploy-cloud-run.yml from a protected environment." >&2
exit 1

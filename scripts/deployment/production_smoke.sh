#!/usr/bin/env bash
# Production smoke checks — see docs/deployment/VERCEL_PRODUCTION_RUNBOOK.md
set -euo pipefail

BASE_URL="${UVAI_SMOKE_BASE_URL:-https://uvai.io}"
TEST_VIDEO_URL="${TEST_YOUTUBE_URL:-https://www.youtube.com/watch?v=jNQXAC9IVRw}"

echo "== UVAI production smoke: ${BASE_URL} =="

echo "-- Security headers"
curl -sSI "${BASE_URL}/" | grep -Ei 'content-security-policy|permissions-policy|strict-transport-security' || {
  echo "WARN: expected security headers missing"
}

echo "-- Pipeline metadata"
curl -sS "${BASE_URL}/api/pipeline" | head -c 400
echo

echo "-- Pipeline POST (bounded response expected)"
curl -sS -X POST "${BASE_URL}/api/pipeline" \
  -H 'content-type: application/json' \
  --data "{\"url\":\"${TEST_VIDEO_URL}\"}" | head -c 600
echo

echo "-- Realtime SDP validation"
code=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${BASE_URL}/api/realtime/session" \
  -H 'content-type: application/sdp' \
  --data 'not-sdp')
echo "realtime malformed SDP HTTP ${code} (expect 400)"

echo "-- API docs redirect"
curl -sSI "${BASE_URL}/api/docs" | head -5

echo "== Smoke complete =="
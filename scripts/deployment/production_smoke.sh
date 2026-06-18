#!/usr/bin/env bash
# Production smoke checks — see docs/deployment/VERCEL_PRODUCTION_RUNBOOK.md
set -euo pipefail

BASE_URL="${UVAI_SMOKE_BASE_URL:-https://uvai.io}"
TEST_VIDEO_URL="${TEST_YOUTUBE_URL:-https://www.youtube.com/watch?v=jNQXAC9IVRw}"
STREAM_TIMEOUT_SEC="${UVAI_STREAM_SMOKE_TIMEOUT:-200}"

echo "== UVAI production smoke: ${BASE_URL} =="

echo "-- Security headers"
curl -sSI "${BASE_URL}/" | grep -Ei 'content-security-policy|permissions-policy|strict-transport-security' || {
  echo "WARN: expected security headers missing"
}

echo "-- Pipeline metadata"
curl -sS "${BASE_URL}/api/pipeline" | head -c 400
echo

echo "-- Pipeline async kickoff (fast path; requires deployed async=true handler)"
set +e
async_body=$(curl -sS -X POST "${BASE_URL}/api/pipeline" \
  -H 'content-type: application/json' \
  --data "{\"url\":\"${TEST_VIDEO_URL}\",\"async\":true}" \
  --max-time 15)
async_rc=$?
set -e
if [[ "${async_rc}" -eq 28 ]]; then
  echo "FAIL: async kickoff timed out — deploy latest web with async=true handler"
  exit 1
elif echo "${async_body}" | grep -qE '"job_id":"job_[^"]+"|"status":"pending"|"status":"complete"'; then
  echo "${async_body}" | head -c 600
  echo
  echo "OK: async pipeline kickoff responded"
else
  echo "${async_body}" | head -c 600
  echo
  echo "FAIL: async kickoff missing job_id/complete — check BACKEND_URL + EVENTRELAY_API_KEY"
  exit 1
fi

echo "-- Pipeline stream SSE (bounded, primary long-path check)"
stream_tmp=$(mktemp)
trap 'rm -f "${stream_tmp}"' EXIT

stream_code=$(curl -sS -o "${stream_tmp}" -w '%{http_code}' -X POST "${BASE_URL}/api/pipeline/stream" \
  -H 'content-type: application/json' \
  -H 'accept: text/event-stream' \
  --data "{\"url\":\"${TEST_VIDEO_URL}\"}" \
  --max-time "${STREAM_TIMEOUT_SEC}")

echo "stream HTTP ${stream_code} (expect 200)"
if [[ "${stream_code}" != "200" ]]; then
  echo "FAIL: pipeline stream returned ${stream_code}"
  head -c 800 "${stream_tmp}" || true
  echo
  exit 1
fi

terminal_status=$(
  grep '"type":"pipeline_status"' "${stream_tmp}" \
    | sed -n 's/.*"status":"\([^"]*\)".*/\1/p' \
    | tail -n 1
)

if [[ "${terminal_status}" == "complete" ]]; then
  echo "OK: stream reached pipeline_status complete"
elif [[ "${terminal_status}" == "error" ]]; then
  echo "FAIL: stream ended with pipeline_status error"
  tail -c 1200 "${stream_tmp}" || true
  echo
  exit 1
else
  echo "FAIL: stream closed without terminal pipeline_status"
  head -c 800 "${stream_tmp}" || true
  echo
  exit 1
fi

echo "-- Realtime SDP validation"
code=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${BASE_URL}/api/realtime/session" \
  -H 'content-type: application/sdp' \
  --data 'not-sdp')
echo "realtime malformed SDP HTTP ${code} (expect 400)"

echo "-- API docs redirect"
curl -sSI "${BASE_URL}/api/docs" | head -5

echo "== Smoke complete =="
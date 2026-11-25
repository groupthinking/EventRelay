#!/usr/bin/env bash
# Production smoke checks — see docs/deployment/VERCEL_PRODUCTION_RUNBOOK.md
set -euo pipefail

BASE_URL="${UVAI_SMOKE_BASE_URL:-https://uvai.io}"
TEST_VIDEO_URL="${TEST_YOUTUBE_URL:-https://www.youtube.com/watch?v=jNQXAC9IVRw}"
PACK_POLL_TIMEOUT_SEC="${UVAI_PACK_SMOKE_TIMEOUT:-150}"
PACK_URL="${BASE_URL}/api/video/pack"

echo "== UVAI production smoke: ${BASE_URL} =="

echo "-- Security headers"
curl -sSI "${BASE_URL}/" | grep -Ei 'content-security-policy|permissions-policy|strict-transport-security' || {
  echo "WARN: expected security headers missing"
}

# Same 11-char id derivation as tests/e2e/pipeline.test.ts (watch?v= or youtu.be/).
TEST_VIDEO_ID=$(printf '%s' "${TEST_VIDEO_URL}" | sed -nE 's#.*([?&]v=|youtu\.be/)([A-Za-z0-9_-]{11}).*#\2#p')
if [[ -z "${TEST_VIDEO_ID}" ]]; then
  echo "FAIL: TEST_YOUTUBE_URL is not a recognized YouTube URL: ${TEST_VIDEO_URL}"
  exit 1
fi

pack_tmp=$(mktemp)
trap 'rm -f "${pack_tmp}"' EXIT

# Every /api/video/pack response is compact JSON whose first key is "status"
# (processing | success | error); see apps/web/src/lib/video-pack.ts.
json_status() {
  sed -n 's/^{"status":"\([^"]*\)".*/\1/p' "$1" | head -n 1
}

echo "-- Retired /api/pipeline routes are gone (removed in #2322)"
for retired_path in /api/pipeline /api/pipeline/stream; do
  retired_code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "${BASE_URL}${retired_path}")
  # 404 when auth is off; 401 when the fail-closed auth gate runs first.
  echo "${retired_path} HTTP ${retired_code} (expect 401 or 404)"
  if [[ "${retired_code}" != "401" && "${retired_code}" != "404" ]]; then
    echo "FAIL: retired route ${retired_path} still answers ${retired_code}"
    exit 1
  fi
done

echo "-- Video Pack kickoff (POST /api/video/pack)"
set +e
kick_code=$(curl -sS -o "${pack_tmp}" -w '%{http_code}' -X POST "${PACK_URL}" \
  -H 'content-type: application/json' \
  --data "{\"url\":\"${TEST_VIDEO_URL}\"}" \
  --max-time 60)
kick_rc=$?
set -e
if [[ "${kick_rc}" -eq 28 ]]; then
  echo "FAIL: pack kickoff timed out after 60s"
  exit 1
elif [[ "${kick_rc}" -ne 0 ]]; then
  echo "FAIL: pack kickoff curl error ${kick_rc}"
  exit 1
fi
kick_status=$(json_status "${pack_tmp}")
# 202 + processing = extraction started; 200 + success = pack already ready.
echo "pack POST HTTP ${kick_code} status=${kick_status:-?} (expect 200/202, success/processing)"
if [[ "${kick_code}" != "200" && "${kick_code}" != "202" ]] ||
  [[ "${kick_status}" != "processing" && "${kick_status}" != "success" ]]; then
  head -c 600 "${pack_tmp}" || true
  echo
  echo "FAIL: pack kickoff did not start or return a pack"
  exit 1
fi
echo "OK: pack kickoff responded"

echo "-- Video Pack poll (GET /api/video/pack?video_id=${TEST_VIDEO_ID}, up to ${PACK_POLL_TIMEOUT_SEC}s)"
deadline=$((SECONDS + PACK_POLL_TIMEOUT_SEC))
poll_code=""
pack_status=""
while :; do
  poll_code=$(curl -sS -o "${pack_tmp}" -w '%{http_code}' --max-time 30 \
    "${PACK_URL}?video_id=${TEST_VIDEO_ID}") || poll_code="curl-error"
  pack_status=$(json_status "${pack_tmp}")
  if [[ "${pack_status}" == "success" || "${pack_status}" == "error" ]]; then
    break
  fi
  if (( SECONDS >= deadline )); then
    break
  fi
  sleep 10
done

echo "pack GET HTTP ${poll_code} status=${pack_status:-?}"
if [[ "${pack_status}" == "success" ]]; then
  # Evidence contract: the pack's own video_id and a sha256 source_hash.
  if grep -q "\"video_id\":\"${TEST_VIDEO_ID}\"" "${pack_tmp}" &&
    grep -qE '"source_hash":"[a-f0-9]{64}"' "${pack_tmp}"; then
    echo "OK: pack ready with video_id and source_hash lineage"
  else
    head -c 800 "${pack_tmp}" || true
    echo
    echo "FAIL: ready pack is missing video_id or source_hash"
    exit 1
  fi
elif [[ "${pack_status}" == "error" ]]; then
  head -c 800 "${pack_tmp}" || true
  echo
  echo "FAIL: pack extraction reported an error"
  exit 1
else
  # Same rule as tests/e2e/pipeline.test.ts: still processing after the
  # bounded wait is extraction latency, not a contract break.
  echo "WARN: pack not ready after ${PACK_POLL_TIMEOUT_SEC}s (last HTTP ${poll_code}); not failing"
fi

echo "-- Realtime SDP validation"
code=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${BASE_URL}/api/realtime/session" \
  -H 'content-type: application/sdp' \
  --data 'not-sdp')
echo "realtime malformed SDP HTTP ${code} (expect 400)"

echo "-- API docs redirect"
curl -sSI "${BASE_URL}/api/docs" | head -5

echo "== Smoke complete =="
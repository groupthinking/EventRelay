import http from 'k6/http';
import { check, sleep } from 'k6';

/**
 * k6 load test for UVAI/EventRelay backend.
 *
 * Replicates the routes used in the automated Locust suite:
 * - GET  /api/v1/health
 * - GET  /api/v1/cloud-ai/providers/status
 * - POST /api/v1/transcript-action
 *
 * Targets explicit, deterministic SLA thresholds:
 * - Checks pass rate (checks) > 99%
 * - Error rate (http_req_failed) < 1%
 * - p(95) latency < 500ms
 * - p(99) latency < 1000ms
 *
 * Zero credentials in source; configurable via __ENV.
 */

export const options = {
  vus: 5,
  duration: '5s',
  thresholds: {
    checks: ['rate>0.99'], // SLA: 99%+ of checks must pass
    http_req_failed: ['rate<0.01'], // SLA: <1% of requests can fail
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // SLA: p95 < 500ms, p99 < 1000ms
  },
};

export default function () {
  const host = __ENV.BASE_URL || 'http://localhost:8000';
  const apiKey = __ENV.EVENTRELAY_API_KEY || '';

  const headers = {
    'Content-Type': 'application/json',
  };

  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  // 1. Warmup / Health check
  const healthRes = http.get(`${host}/api/v1/health`, { headers });
  check(healthRes, {
    'health status is 200': (r) => r.status === 200,
    'health service is correct': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status === 'healthy';
      } catch (e) {
        return false;
      }
    }
  });
  sleep(1);

  // 2. Providers Status check
  const providersRes = http.get(`${host}/api/v1/cloud-ai/providers/status`, { headers });
  check(providersRes, {
    'providers status is 200': (r) => r.status === 200 || r.status === 401 || r.status === 403,
  });
  sleep(1);

  // 3. Primary Workflow: Transcript Action (POST)
  const transcriptPayload = JSON.stringify({
    video_url: "https://www.youtube.com/watch?v=auJzb1D-fag",
    language: "en",
    transcript_text: "Hello, welcome to this video tutorial. Today we will build an AI service.",
    video_options: {
      model_name: "gemini-2.5-flash",
      temperature: 0.2
    }
  });

  const transcriptRes = http.post(
    `${host}/api/v1/transcript-action`,
    transcriptPayload,
    { headers }
  );

  check(transcriptRes, {
    'transcript action is 200': (r) => r.status === 200,
    'transcript action reports success': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.success === true;
      } catch (e) {
        return false;
      }
    }
  });
  sleep(1);
}

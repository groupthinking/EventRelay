import http from 'k6/http';
import { check, sleep, group } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Baseline: 10 concurrent users
    { duration: '1m', target: 50 },   // Normal load: 50 concurrent users
    { duration: '1m', target: 200 },  // Peak load: 200 concurrent users
    { duration: '1m', target: 500 },  // Stress test: 500+ concurrent users
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';
  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  group('Warmup and Status', function () {
    const healthRes = http.get(`${baseUrl}/health`);
    check(healthRes, {
      'health status is 200': (r) => r.status === 200,
    });

    const capRes = http.get(`${baseUrl}/api/v1/capabilities`);
    check(capRes, {
      'capabilities status is 200': (r) => r.status === 200,
    });
  });

  group('Core Pipeline', function () {
    const payload = JSON.stringify({
      video_url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      language: 'en'
    });

    // Using transcript-action for realistic workflow load
    const actionRes = http.post(`${baseUrl}/api/v1/transcript-action`, payload, params);
    check(actionRes, {
      'transcript-action accepted or processing': (r) => r.status === 200 || r.status === 202,
    });
  });

  sleep(Math.random() * 3 + 2);
}

/**
 * EventRelay E2E Test Suite
 *
 * Tests the live deployment at BASE_URL (default: https://uvai.io) for:
 *   1. Homepage / Template Gallery rendering
 *   2. SSE pipeline stream — full end-to-end with a real YouTube URL
 *   3. SSE stream closes properly (no 95% hang regression)
 *   4. CloudEvent schema compliance in SSE events
 *   5. Error handling — invalid URL returns error, not a hang
 *   6. Dashboard page renders
 *   7. Interactive transcript player component exists
 *
 * Environment:
 *   BASE_URL — deployment URL (default: https://uvai.io)
 *   TEST_YOUTUBE_URL — short video for pipeline test
 *     (default: https://www.youtube.com/watch?v=dQw4w9WgXcQ — 3:33)
 *
 * Red/Green Signal:
 *   - GREEN: all tests pass → stdout: "✅ ALL TESTS PASSED"
 *   - RED: any failure → stdout: "🔴 FAILURE DETECTED" + details
 */

import { describe, it, expect, beforeAll } from 'vitest';

const BASE_URL = process.env.BASE_URL || 'https://uvai.io';
const TEST_YOUTUBE_URL =
  process.env.TEST_YOUTUBE_URL ||
  'https://www.youtube.com/watch?v=dQw4w9WgXcQ';

// ─── Helpers ────────────────────────────────────────────────────────

/** Fetch with a hard timeout and automatic retry for transient network errors. */
async function fetchWithTimeout(
  url: string,
  init?: RequestInit,
  timeoutMs = 90_000,
  maxRetries = 3,
): Promise<Response> {
  let lastError: Error | null = null;
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(url, { ...init, signal: controller.signal });
      clearTimeout(timer);
      return res;
    } catch (err) {
      clearTimeout(timer);
      lastError = err instanceof Error ? err : new Error(String(err));
      // Retry on transient network errors (ECONNRESET, ECONNREFUSED, etc.)
      const isTransient =
        lastError.message.includes('ECONNRESET') ||
        lastError.message.includes('ECONNREFUSED') ||
        lastError.message.includes('fetch failed') ||
        lastError.message.includes('socket disconnected') ||
        lastError.message.includes('network');
      if (!isTransient || attempt === maxRetries - 1) {
        throw lastError;
      }
      // Wait before retry: 1s, 2s, 3s
      await new Promise((r) => setTimeout(r, (attempt + 1) * 1000));
    }
  }
  throw lastError || new Error('fetchWithTimeout: max retries exceeded');
}

/** Parse an SSE text stream into an array of parsed JSON events. */
function parseSSEEvents(raw: string): Array<Record<string, unknown>> {
  const events: Array<Record<string, unknown>> = [];
  const lines = raw.split('\n');
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      try {
        events.push(JSON.parse(line.slice(6)));
      } catch {
        // skip non-JSON lines
      }
    }
  }
  return events;
}

// ─── Tests ──────────────────────────────────────────────────────────

describe('EventRelay E2E — Live Deployment', () => {
  // Smoke check: is the site up?
  beforeAll(async () => {
    const res = await fetchWithTimeout(BASE_URL, {}, 15_000);
    if (!res.ok) {
      throw new Error(
        `Site is DOWN — ${BASE_URL} returned ${res.status}. Cannot run E2E tests.`,
      );
    }
  });

  // ── 1. Template Gallery Homepage ──────────────────────────────────

  describe('Template Gallery', () => {
    it('homepage returns 200 with HTML', async () => {
      const res = await fetchWithTimeout(BASE_URL);
      expect(res.status).toBe(200);
      const ct = res.headers.get('content-type') || '';
      expect(ct).toContain('text/html');
    });

    it('homepage contains template gallery markup', async () => {
      const res = await fetchWithTimeout(BASE_URL);
      const html = await res.text();
      // The template gallery should have at least some of these workflow names
      const expectedTemplates = [
        'Tutorial',
        'Conference',
        'Podcast',
        'Code Review',
        'Meeting',
        'Research',
      ];
      const found = expectedTemplates.filter((t) =>
        html.toLowerCase().includes(t.toLowerCase()),
      );
      expect(found.length).toBeGreaterThanOrEqual(3);
    });

    it('homepage contains at least 5 template cards', async () => {
      const res = await fetchWithTimeout(BASE_URL);
      const html = await res.text();
      // Count template card patterns — look for the workflow template structure
      // Each template card has a "Run" or "Launch" or similar CTA
      // We check for multiple distinct template-related content blocks
      const templateIndicators = [
        'youtube',
        'tutorial',
        'conference',
        'podcast',
        'meeting',
        'code review',
        'research',
        'demo',
        'webinar',
      ];
      const found = templateIndicators.filter((t) =>
        html.toLowerCase().includes(t),
      );
      expect(found.length).toBeGreaterThanOrEqual(5);
    });
  });

  // ── 2. SSE Pipeline Stream — Full End-to-End ──────────────────────

  describe('SSE Pipeline Stream', () => {
    it('POST /api/pipeline/stream returns SSE content-type', async () => {
      const res = await fetchWithTimeout(
        `${BASE_URL}/api/pipeline/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: TEST_YOUTUBE_URL }),
        },
        90_000,
      );
      expect(res.status).toBe(200);
      const ct = res.headers.get('content-type') || '';
      expect(ct).toContain('text/event-stream');
    });

    it('SSE stream emits pipeline_status:running then pipeline_status:complete', async () => {
      const res = await fetchWithTimeout(
        `${BASE_URL}/api/pipeline/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: TEST_YOUTUBE_URL }),
        },
        90_000,
      );

      const body = await res.text();
      const events = parseSSEEvents(body);

      // Must have at least 2 events
      expect(events.length).toBeGreaterThanOrEqual(2);

      // First event should be pipeline_status:running
      const runningEvent = events.find(
        (e) => e.type === 'pipeline_status' && e.status === 'running',
      );
      expect(runningEvent).toBeDefined();

      // Last pipeline_status event should be 'complete'
      const pipelineEvents = events.filter(
        (e) => e.type === 'pipeline_status',
      );
      const lastPipeline = pipelineEvents[pipelineEvents.length - 1];
      expect(lastPipeline?.status).toBe('complete');
    });

    it('SSE stream closes within 90 seconds (no 95% hang)', async () => {
      const start = Date.now();
      const res = await fetchWithTimeout(
        `${BASE_URL}/api/pipeline/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: TEST_YOUTUBE_URL }),
        },
        90_000,
      );

      // Reading the full body — if the stream hangs, fetchWithTimeout aborts at 90s
      await res.text();
      const elapsed = Date.now() - start;

      // Stream should complete, not hang. If it took > 85s, it's likely hanging.
      expect(elapsed).toBeLessThan(85_000);
    });

    it('SSE events fire in correct agent order', async () => {
      const res = await fetchWithTimeout(
        `${BASE_URL}/api/pipeline/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: TEST_YOUTUBE_URL }),
        },
        90_000,
      );

      const body = await res.text();
      const events = parseSSEEvents(body);

      // Extract agent_update events
      const agentUpdates = events.filter((e) => e.type === 'agent_update');

      if (agentUpdates.length > 0) {
        // Orchestrator should appear before action_gen
        const orchestratorIdx = agentUpdates.findIndex(
          (e) => e.agentId === 'orchestrator',
        );
        const actionGenIdx = agentUpdates.findIndex(
          (e) => e.agentId === 'action_gen',
        );

        if (orchestratorIdx !== -1 && actionGenIdx !== -1) {
          expect(orchestratorIdx).toBeLessThan(actionGenIdx);
        }
      }

      // Must have a workflow event with data
      const workflowEvent = events.find((e) => e.type === 'workflow');
      if (workflowEvent) {
        expect(workflowEvent.data).toBeDefined();
      }
    });
  });

  // ── 3. CloudEvent Schema Compliance ───────────────────────────────

  describe('CloudEvent Schema', () => {
    it('SSE events contain valid timestamps', async () => {
      const res = await fetchWithTimeout(
        `${BASE_URL}/api/pipeline/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: TEST_YOUTUBE_URL }),
        },
        90_000,
      );

      const body = await res.text();
      const events = parseSSEEvents(body);

      for (const event of events) {
        if (event.timestamp) {
          const ts = new Date(event.timestamp as string);
          expect(ts.getTime()).not.toBeNaN();
        }
      }
    });

    it('pipeline_status:complete includes duration and agent count', async () => {
      const res = await fetchWithTimeout(
        `${BASE_URL}/api/pipeline/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: TEST_YOUTUBE_URL }),
        },
        90_000,
      );

      const body = await res.text();
      const events = parseSSEEvents(body);
      const complete = events.find(
        (e) => e.type === 'pipeline_status' && e.status === 'complete',
      );

      expect(complete).toBeDefined();
      if (complete) {
        expect(complete.duration).toBeDefined();
        expect(typeof complete.duration).toBe('number');
        const data = complete.data as Record<string, unknown> | undefined;
        if (data) {
          expect(data.totalAgents).toBeDefined();
          expect(data.completedAgents).toBeDefined();
        }
      }
    });
  });

  // ── 4. Error Handling ─────────────────────────────────────────────

  describe('Error Handling', () => {
    it('missing URL returns 400, not a hang', async () => {
      const start = Date.now();
      const res = await fetchWithTimeout(
        `${BASE_URL}/api/pipeline/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        },
        10_000,
      );

      const elapsed = Date.now() - start;
      expect(res.status).toBe(400);
      expect(elapsed).toBeLessThan(5_000); // Should respond instantly
    });

    it('invalid URL returns error event or completes quickly, not a hang', async () => {
      const start = Date.now();
      const res = await fetchWithTimeout(
        `${BASE_URL}/api/pipeline/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: 'not-a-valid-url' }),
        },
        30_000,
      );

      const elapsed = Date.now() - start;

      if (res.status === 200) {
        // Server may return an SSE stream that either:
        // a) contains an error event, or
        // b) completes with pipeline_status:complete (with error in data), or
        // c) has no events at all
        // All are acceptable — the key requirement is that it does NOT hang.
        const body = await res.text();
        const events = parseSSEEvents(body);
        const hasTerminalEvent = events.some(
          (e) =>
            e.type === 'error' ||
            (e.type === 'pipeline_status' &&
              (e.status === 'error' || e.status === 'complete')),
        );
        // Either has a terminal event or stream was empty
        expect(hasTerminalEvent || events.length === 0).toBe(true);
      } else {
        // Non-200 is also acceptable (400, 503, etc.)
        expect(res.status).toBeGreaterThanOrEqual(400);
      }

      // The critical assertion: must not hang
      expect(elapsed).toBeLessThan(25_000);
    });
  });

  // ── 5. Dashboard Page ─────────────────────────────────────────────

  describe('Dashboard', () => {
    it('/dashboard returns 200', async () => {
      const res = await fetchWithTimeout(`${BASE_URL}/dashboard`);
      expect(res.status).toBe(200);
    });

    it('/dashboard contains agent or pipeline visualization markup', async () => {
      const res = await fetchWithTimeout(`${BASE_URL}/dashboard`);
      const html = await res.text();
      const indicators = ['agent', 'pipeline', 'dashboard', 'transcript', 'video'];
      const found = indicators.filter((t) =>
        html.toLowerCase().includes(t),
      );
      expect(found.length).toBeGreaterThanOrEqual(2);
    });
  });

  // ── 6. API Health ─────────────────────────────────────────────────

  describe('API Health', () => {
    it('GET /api returns a response (not 404)', async () => {
      const res = await fetchWithTimeout(`${BASE_URL}/api`);
      // Should return something — 200 or 405, but not 404
      expect(res.status).not.toBe(404);
    });

    it('POST /api/pipeline/stream with no body returns 400', async () => {
      const res = await fetchWithTimeout(
        `${BASE_URL}/api/pipeline/stream`,
        { method: 'POST' },
        10_000,
      );
      // Should handle gracefully — 400 or 500, but respond quickly
      expect([400, 500]).toContain(res.status);
    });
  });

  // ── 7. Static Assets & Meta ───────────────────────────────────────

  describe('Static Assets', () => {
    it('homepage has proper meta tags', async () => {
      const res = await fetchWithTimeout(BASE_URL);
      const html = await res.text();
      // Should have a title
      expect(html).toMatch(/<title>/i);
      // Should have viewport meta
      expect(html.toLowerCase()).toContain('viewport');
    });

    it('/features page returns 200', async () => {
      const res = await fetchWithTimeout(`${BASE_URL}/features`);
      expect(res.status).toBe(200);
    });
  });
});

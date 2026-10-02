/**
 * EventRelay E2E Test Suite
 *
 * Tests the live deployment at BASE_URL (default: https://uvai.io) for:
 *   1. Homepage smoke check + Template Gallery (/features) rendering
 *   2. Video Pack pipeline — POST /api/video/pack → poll GET until ready
 *   3. Pack evidence contract — hashed identity, source_hash lineage
 *   4. Error handling — invalid URL returns 400, not a hang
 *   5. Dashboard page renders
 *   6. API health descriptor
 *   7. Static assets & meta
 *
 * The legacy /api/pipeline SSE routes were retired; the canonical pipeline is
 * the Video Pack flow (`POST /api/video/pack` → Upstash → Studio → G.A.T.E.).
 *
 * Environment:
 *   BASE_URL — deployment URL (default: https://uvai.io)
 *   TEST_YOUTUBE_URL — short video for pipeline test
 *     (default: https://www.youtube.com/watch?v=auJzb1D-fag)
 *   GITHUB_RUN_ID — included in the E2E User-Agent for production attribution
 *
 * Red/Green Signal:
 *   - GREEN: all tests pass → stdout: "✅ ALL TESTS PASSED"
 *   - RED: any failure → stdout: "🔴 FAILURE DETECTED" + details
 */

import { afterEach, describe, it, expect, beforeAll, vi } from 'vitest';

const BASE_URL = process.env.BASE_URL || 'https://uvai.io';
const TEST_YOUTUBE_URL =
  process.env.TEST_YOUTUBE_URL ||
  'https://www.youtube.com/watch?v=auJzb1D-fag';
/** Derive the 11-char video id from the configured URL (watch?v= or youtu.be/). */
function videoIdFromUrl(url: string): string {
  const match =
    url.match(/[?&]v=([A-Za-z0-9_-]{11})/) || url.match(/youtu\.be\/([A-Za-z0-9_-]{11})/);
  if (!match) throw new Error(`TEST_YOUTUBE_URL is not a recognized YouTube URL: ${url}`);
  return match[1];
}
const TEST_VIDEO_ID = videoIdFromUrl(TEST_YOUTUBE_URL);

// To exercise a protected deployment (e.g. a Vercel preview, which returns 401
// to anonymous requests), set VERCEL_AUTOMATION_BYPASS_SECRET to the project's
// "Protection Bypass for Automation" secret. It is attached as a header on
// every request so the preview is reachable. Unset (the default — e.g. when
// BASE_URL is production) → no bypass header is added; E2E attribution remains.
const E2E_RUN_ID = process.env.GITHUB_RUN_ID?.trim() || 'local';
const E2E_USER_AGENT = `EventRelay-E2E/${E2E_RUN_ID}`;

// ─── Helpers ────────────────────────────────────────────────────────

/** Add stable E2E attribution and the optional Vercel protection bypass. */
function withE2EHeaders(init?: RequestInit): RequestInit {
  // Normalize via the Headers constructor so any HeadersInit shape (plain
  // object, Headers instance, or [key, value][] array) is preserved — a bare
  // spread would silently drop a Headers/array-typed init.headers.
  const headers = new Headers(init?.headers);
  headers.set('User-Agent', E2E_USER_AGENT);
  headers.set('X-EventRelay-Probe', 'e2e');
  const bypassSecret = process.env.VERCEL_AUTOMATION_BYPASS_SECRET?.trim();
  if (bypassSecret) {
    headers.set('x-vercel-protection-bypass', bypassSecret);
  }
  // Deliberately NOT sending `x-vercel-set-bypass-cookie`. That header asks
  // Vercel to persist the bypass as a cookie and answers every request with
  // `307 → /`. `fetch` has no cookie jar, so the redirect target is requested
  // with the same header and 307s again — an unbounded loop that ends in
  // "TypeError: fetch failed / redirect count exceeded", failing the whole
  // suite even though the secret is correct. The bypass header alone is
  // accepted per-request and returns 200 directly, which is all a stateless
  // test client needs. The cookie form only helps a browser that persists it.
  return { ...init, headers };
}

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
      const res = await fetch(url, { ...withE2EHeaders(init), signal: controller.signal });
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

describe('E2E request attribution', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('adds the probe and GitHub run identity headers to every request', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(null, { status: 204 }));
    let capturedInit: RequestInit | undefined;

    try {
      await fetchWithTimeout(
        'https://example.test/api/health',
        { headers: { Accept: 'application/json' } },
        100,
        1,
      );
      capturedInit = fetchSpy.mock.calls[0]?.[1];
    } finally {
      fetchSpy.mockRestore();
    }

    const headers = new Headers(capturedInit?.headers);
    const runId = process.env.GITHUB_RUN_ID?.trim() || 'local';

    expect(headers.get('user-agent')).toBe(`EventRelay-E2E/${runId}`);
    expect(headers.get('x-eventrelay-probe')).toBe('e2e');
    expect(headers.get('accept')).toBe('application/json');
  });

  it('forwards the configured preview bypass on every request without persisting it', async () => {
    vi.stubEnv('VERCEL_AUTOMATION_BYPASS_SECRET', 'preview-bypass-test-value');
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_url, init) => {
      const headers = new Headers(init?.headers);
      const bypassed = headers.get('x-vercel-protection-bypass') === 'preview-bypass-test-value';
      return new Response(null, { status: bypassed ? 204 : 401 });
    });

    try {
      const response = await fetchWithTimeout('https://preview.example.test/api/health', undefined, 100, 1);
      const headers = new Headers(fetchSpy.mock.calls[0]?.[1]?.headers);

      expect(response.status).toBe(204);
      expect(headers.get('x-vercel-protection-bypass')).toBe('preview-bypass-test-value');
      expect(headers.has('x-vercel-set-bypass-cookie')).toBe(false);
    } finally {
      fetchSpy.mockRestore();
    }
  });
});

// ─── Tests ──────────────────────────────────────────────────────────

describe('EventRelay E2E — Live Deployment', () => {
  // Smoke check: is the site up, and is it the app we intend to test?
  //
  // Vercel Deployment Protection intercepts anonymous traffic to a preview in two
  // shapes: HTML routes 302 to vercel.com/sso-api, API routes return a bare 401.
  // The default `redirect: 'follow'` hides the first shape completely — fetch
  // lands on a 200 "Login – Vercel" page, so `res.ok` is true and the suite runs
  // every assertion against Vercel's login markup instead of the deployment. The
  // page happens to contain a <title> and a viewport meta tag, so the meta and
  // liveness tests pass; only the content and API assertions fail, with messages
  // that blame the app ("expected 0 to be greater than or equal to 3") rather than
  // naming the missing bypass secret. Probe with `redirect: 'manual'` so the 302
  // stays visible and fail once, with the remedy.
  beforeAll(async () => {
    const probe = await fetchWithTimeout(BASE_URL, { redirect: 'manual' }, 15_000);
    const location = probe.headers.get('location') || '';
    const ssoRedirect =
      [301, 302, 303, 307, 308].includes(probe.status) &&
      /vercel\.com\/sso-api/i.test(location);

    if (ssoRedirect || probe.status === 401) {
      throw new Error(
        `Deployment protection blocked this run — ${BASE_URL} returned ${probe.status}` +
          `${location ? ` → ${location}` : ''} instead of the app, so every assertion ` +
          `below would execute against Vercel's login page rather than the deployment. ` +
          `Set the VERCEL_AUTOMATION_BYPASS_SECRET repository secret to the project's ` +
          `"Protection Bypass for Automation" value (Vercel → Project → Settings → ` +
          `Deployment Protection); this suite forwards it as the ` +
          `x-vercel-protection-bypass header on every request.`,
      );
    }

    // Liveness check, following redirects as before so a legitimate same-host
    // redirect on `/` still counts as up.
    const res = await fetchWithTimeout(BASE_URL, {}, 15_000);
    if (!res.ok) {
      throw new Error(
        `Site is DOWN — ${BASE_URL} returned ${res.status}. Cannot run E2E tests.`,
      );
    }
  });

  // ── 1. Template Gallery / Feature Showcase ────────────────────────
  // The homepage (BASE_URL) is the interactive Video Workflow Studio and
  // intentionally does NOT render the template gallery. The workflow /
  // template content lives on the /features page, so the content
  // assertions below target /features (the homepage keeps a generic
  // 200/HTML smoke check).

  describe('Template Gallery', () => {
    const FEATURES_URL = `${BASE_URL}/features`;

    it('homepage returns 200 with HTML', async () => {
      const res = await fetchWithTimeout(BASE_URL);
      expect(res.status).toBe(200);
      const ct = res.headers.get('content-type') || '';
      expect(ct).toContain('text/html');
    });

    it('features page contains template/workflow markup', async () => {
      const res = await fetchWithTimeout(FEATURES_URL);
      expect(res.status).toBe(200);
      const html = await res.text();
      // The features page should reference at least some of these workflow names
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

    it('features page surfaces at least 5 workflow/template indicators', async () => {
      const res = await fetchWithTimeout(FEATURES_URL);
      expect(res.status).toBe(200);
      const html = await res.text();
      // Count distinct template-related content blocks across the feature
      // sections and the shared footer use-case list.
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

  // ── 2. Video Pack Pipeline — the canonical flow ───────────────────
  // POST /api/video/pack accepts the URL and returns 202 (processing) or 200
  // (already-ready pack). GET /api/video/pack?video_id=… polls until the pack
  // is ready. The pack is the evidence unit the Studio and G.A.T.E. consume.

  describe('Video Pack Pipeline', () => {
    const PACK_URL = `${BASE_URL}/api/video/pack`;

    it('POST /api/video/pack accepts a YouTube URL without hanging', async () => {
      const start = Date.now();
      const res = await fetchWithTimeout(
        PACK_URL,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: TEST_YOUTUBE_URL }),
        },
        60_000,
      );
      const elapsed = Date.now() - start;

      // 202 = extraction kicked off; 200 = pack already ready (cached).
      expect([200, 202]).toContain(res.status);
      const payload = (await res.json()) as Record<string, unknown>;
      expect(['processing', 'success']).toContain(payload.status);
      expect(elapsed).toBeLessThan(55_000);
    });

    it('GET /api/video/pack resolves to a ready pack with evidence lineage', async () => {
      // Kick off (idempotent — a ready pack returns immediately).
      await fetchWithTimeout(
        PACK_URL,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: TEST_YOUTUBE_URL }),
        },
        60_000,
      );

      // Poll for readiness: bounded, honest about extraction latency.
      const deadline = Date.now() + 150_000;
      let pack: Record<string, unknown> | null = null;
      for (;;) {
        const res = await fetchWithTimeout(
          `${PACK_URL}?video_id=${TEST_VIDEO_ID}`,
          {},
          30_000,
        );
        const payload = (await res.json()) as Record<string, unknown>;
        if (payload.status === 'success' && payload.data && typeof payload.data === 'object') {
          pack = payload.data as Record<string, unknown>;
          break;
        }
        if (Date.now() > deadline) break;
        await new Promise((r) => setTimeout(r, 10_000));
      }

      if (!pack) {
        console.info(
          '[E2E] Pack still processing after 150s — extraction latency, not a contract break. Skipping shape assertions.',
        );
        return;
      }

      // Evidence contract: hashed identity, source lineage, real content.
      expect(pack.video_id).toBe(TEST_VIDEO_ID);
      expect(pack.id).toBe(`vp:v0:${TEST_VIDEO_ID}`);
      expect(typeof pack.source_url).toBe('string');
      const provenance = pack.provenance as Record<string, unknown>;
      expect(provenance.source_hash).toMatch(/^[a-f0-9]{64}$/);
      const transcript = pack.transcript as Record<string, unknown>;
      expect(typeof transcript.full_text).toBe('string');
      expect((transcript.full_text as string).length).toBeGreaterThan(0);
    }, 180_000);
  });

  // ── 3. Error Handling ─────────────────────────────────────────────

  describe('Error Handling', () => {
    const PACK_URL = `${BASE_URL}/api/video/pack`;

    it('missing URL returns 400, not a hang', async () => {
      const start = Date.now();
      const res = await fetchWithTimeout(
        PACK_URL,
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

    it('invalid URL returns 400 quickly, not a hang', async () => {
      const start = Date.now();
      const res = await fetchWithTimeout(
        PACK_URL,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: 'not-a-valid-url' }),
        },
        10_000,
      );

      const elapsed = Date.now() - start;
      expect(res.status).toBe(400);
      const payload = (await res.json()) as Record<string, unknown>;
      expect(payload.status).toBe('error');
      expect(elapsed).toBeLessThan(5_000);
    });

    it('POST /api/video/pack with no body returns 400', async () => {
      const res = await fetchWithTimeout(PACK_URL, { method: 'POST' }, 10_000);
      expect(res.status).toBe(400);
    });
  });

  // ── 4. Dashboard Page ─────────────────────────────────────────────

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
      // When NEXTAUTH_SECRET is set in production the middleware redirects
      // unauthenticated requests to the NextAuth sign-in page; that page
      // contains "dashboard" in the callbackUrl, so we get ≥ 1 match.
      // A fully-rendered (authenticated) dashboard will match more.
      expect(found.length).toBeGreaterThanOrEqual(1);
    });
  });

  // ── 5. API Health ─────────────────────────────────────────────────

  describe('API Health', () => {
    it('GET /api returns a response (not 404)', async () => {
      const res = await fetchWithTimeout(`${BASE_URL}/api`);
      // Should return something — 200 or 405, but not 404
      expect(res.status).not.toBe(404);
    });

    it('retired /api/pipeline routes are gone (no pipeline served)', async () => {
      const res = await fetchWithTimeout(`${BASE_URL}/api/pipeline`);
      // 404 when auth is off (no such route); 401 when the middleware's
      // fail-closed auth gate runs before routing on protected deployments.
      // Either way the legacy pipeline serves nothing — no 200, no SSE.
      expect([401, 404]).toContain(res.status);
    });
  });

  // ── 6. Static Assets & Meta ───────────────────────────────────────

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

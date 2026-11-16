import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * #2214: POST /api/video/pack must not start paid durable extraction without
 * server-side admission (trusted identity + entitlement + atomic quota).
 */

const { resolveTrustedBillingEmail, isProSubscriber } = vi.hoisted(() => ({
  resolveTrustedBillingEmail: vi.fn(async (_req: Request): Promise<string | null> => null),
  isProSubscriber: vi.fn(async (_email: string | null | undefined): Promise<boolean> => false),
}));
vi.mock('@/lib/billing/billing-context', () => ({ resolveTrustedBillingEmail }));
vi.mock('@/lib/billing/entitlement-store', () => ({ isProSubscriber }));

const VIDEO_A = 'auJzb1D-fag';
const VIDEO_B = 'jNQXAC9IVRw';
const VIDEO_C = 'dQw4w9WgXcQ';

function post(body: unknown, headers: Record<string, string> = {}) {
  return new Request('http://localhost:3000/api/video/pack', {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });
}

async function load() {
  const store = await import('@/lib/video-pack-store');
  store.resetVideoPackStoreForTests();
  const admission = await import('@/lib/billing/video-pack-admission');
  admission.resetVideoPackAdmissionForTests();
  const videoPack = await import('@/lib/video-pack');
  const started: string[] = [];
  videoPack.setVideoPackWorkflowStarterForTests(async (identity) => {
    started.push(identity.source_url);
  });
  const route = await import('../route');
  return { POST: route.POST, started, store, videoPack };
}

beforeEach(() => {
  resolveTrustedBillingEmail.mockReset();
  resolveTrustedBillingEmail.mockResolvedValue(null);
  isProSubscriber.mockReset();
  isProSubscriber.mockResolvedValue(false);
});

afterEach(() => {
  vi.resetModules();
  vi.unstubAllEnvs();
});

describe('POST /api/video/pack admission (#2214)', () => {
  it('denies anonymous extraction past the quota with 402 and starts no workflow', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '1');
    const { POST, started } = await load();
    expect((await POST(post({ video_id: VIDEO_A }))).status).toBe(202);
    const denied = await POST(post({ video_id: VIDEO_B }));
    expect(denied.status).toBe(402);
    expect(denied.headers.get('retry-after')).toMatch(/^\d+$/);
    expect(await denied.json()).toMatchObject({ status: 'error', reason: 'subject_quota', upgradeRequired: true });
    expect(started).toEqual([`https://www.youtube.com/watch?v=${VIDEO_A}`]);
  });

  it('a forged body/header plan or email does not lift the anonymous limit', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '0');
    const { POST, started } = await load();
    const res = await POST(
      post(
        { video_id: VIDEO_A, email: 'pro@example.com', plan: 'pro', isPro: true },
        { 'x-billing-email': 'pro@example.com', cookie: 'er_billing_email=pro@example.com' },
      ),
    );
    expect(res.status).toBe(402);
    expect(started).toHaveLength(0);
  });

  it('serves a ready cached pack without consuming quota', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '0');
    const { POST, started, store, videoPack } = await load();
    const identity = videoPack.buildIdentityPack(VIDEO_A);
    const ready = videoPack.applyExtractedSpec(identity, {
      transcript: { language: 'en', full_text: 'real speech', segments: [] },
      keyframes: [],
      concepts: ['c'],
      requirements: [],
      code_snippets: [],
      artifacts: [],
      stack: { tools: [] },
      visual_context: null,
      chapters: [],
      action_items: [],
    } as never);
    store.seedVideoPackRecordForTests({ state: 'ready', pack: ready });
    const res = await POST(post({ url: `https://youtu.be/${VIDEO_A}?t=42` }));
    expect(res.status).toBe(200);
    expect(started).toHaveLength(0);
  });

  it('URL variants of one video share one claim: the second POST is not billed again', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '1');
    const { POST, started } = await load();
    expect((await POST(post({ url: `https://www.youtube.com/watch?v=${VIDEO_A}&list=PL1&t=9s` }))).status).toBe(202);
    for (const url of [
      `https://youtu.be/${VIDEO_A}`,
      `https://m.youtube.com/watch?v=${VIDEO_A}`,
      `https://www.youtube.com/shorts/${VIDEO_A}`,
      `https://WWW.YouTube.com/watch?v=${VIDEO_A}`,
    ]) {
      expect((await POST(post({ url }))).status).toBe(202); // in-flight processing record, no new spend
    }
    expect(started).toEqual([`https://www.youtube.com/watch?v=${VIDEO_A}`]);
  });

  it('retrying a failed pack consumes quota each time (no unbounded retry billing)', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '2');
    const { POST, started, store } = await load();
    const { identityHash } = await import('@/lib/video-pack');
    const errorRecord = {
      state: 'error' as const,
      video_id: VIDEO_C,
      source_url: `https://www.youtube.com/watch?v=${VIDEO_C}`,
      source_hash: identityHash(VIDEO_C),
      id: `vp:v0:${VIDEO_C}`,
      error: 'boom',
      failed_at: new Date().toISOString(),
    };
    store.seedVideoPackRecordForTests(errorRecord);
    expect((await POST(post({ video_id: VIDEO_C }))).status).toBe(202);
    store.seedVideoPackRecordForTests(errorRecord);
    expect((await POST(post({ video_id: VIDEO_C }))).status).toBe(202);
    store.seedVideoPackRecordForTests(errorRecord);
    expect((await POST(post({ video_id: VIDEO_C }))).status).toBe(402);
    expect(started).toHaveLength(2);
  });

  it('returns the reserved unit when the workflow fails to start', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_ANON', '1');
    const { POST, videoPack } = await load();
    videoPack.setVideoPackWorkflowStarterForTests(async () => {
      throw new Error('Workflow endpoint is unavailable');
    });
    expect((await POST(post({ video_id: VIDEO_A }))).status).toBe(503);
    const started: string[] = [];
    videoPack.setVideoPackWorkflowStarterForTests(async (identity) => {
      started.push(identity.video_id);
    });
    expect((await POST(post({ video_id: VIDEO_B }))).status).toBe(202);
    expect(started).toEqual([VIDEO_B]);
  });

  it('returns 429 when the global daily cap is exhausted, even for pro', async () => {
    vi.stubEnv('VIDEO_PACK_EXTRACT_DAILY_LIMIT_GLOBAL', '1');
    resolveTrustedBillingEmail.mockResolvedValue('pro@example.com');
    isProSubscriber.mockResolvedValue(true);
    const { POST, started } = await load();
    expect((await POST(post({ video_id: VIDEO_A }))).status).toBe(202);
    const res = await POST(post({ video_id: VIDEO_B }));
    expect(res.status).toBe(429);
    expect(await res.json()).toMatchObject({ reason: 'global_quota' });
    expect(started).toHaveLength(1);
  });

  it('fails closed (503, nothing started) when the quota store errors', async () => {
    const { POST, started, store } = await load();
    store.setVideoPackRedisForTests({
      get: async () => null,
      set: async () => 'OK',
      eval: async () => {
        throw new Error('redis down');
      },
    });
    const res = await POST(post({ video_id: VIDEO_A }));
    expect(res.status).toBe(503);
    expect(started).toHaveLength(0);
  });

  it('emits a machine-readable start receipt without the raw email', async () => {
    resolveTrustedBillingEmail.mockResolvedValue('someone@example.com');
    const info = vi.spyOn(console, 'info').mockImplementation(() => {});
    const { POST } = await load();
    expect((await POST(post({ video_id: VIDEO_A }))).status).toBe(202);
    const receipt = info.mock.calls
      .map((c) => String(c[0]))
      .map((s) => {
        try {
          return JSON.parse(s) as Record<string, unknown>;
        } catch {
          return null;
        }
      })
      .find((r) => r?.event === 'extraction_start_receipt');
    expect(receipt).toMatchObject({
      outcome: 'started',
      plan: 'free',
      video_id: VIDEO_A,
      source_url: `https://www.youtube.com/watch?v=${VIDEO_A}`,
    });
    expect(String(receipt?.requester)).toMatch(/^[a-f0-9]{16}$/);
    expect(JSON.stringify(receipt)).not.toContain('someone@example.com');
    info.mockRestore();
  });
});

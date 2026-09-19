import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  QJ_SOP_STEPS,
  QJ_SOURCE_URL,
  QJ_TRANSCRIPT,
  QJ_VIDEO_ID,
  QJ_VISUAL_EVENTS,
} from '@/lib/__fixtures__/qj-z5ohr7sga-emit';
import {
  XYMC_SOP_STEPS,
  XYMC_TRANSCRIPT,
  XYMC_VIDEO_ID,
  XYMC_VISUAL_EVENTS,
  XYMC_SOURCE_URL,
} from '@/lib/__fixtures__/xymcbrfsj4c-emit';

afterEach(() => {
  vi.resetModules();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

async function loadHostedRoute() {
  const videoPack = await import('@/lib/video-pack');
  const store = await import('@/lib/video-pack-store');
  store.resetVideoPackStoreForTests();
  const route = await import('../route');
  return {
    GET: route.GET,
    seedVideoPackRecordForTests: store.seedVideoPackRecordForTests,
    buildIdentityPack: videoPack.buildIdentityPack,
    applyExtractedSpec: videoPack.applyExtractedSpec,
  };
}

function extractedSpec() {
  return {
    transcript: QJ_TRANSCRIPT,
    keyframes: QJ_VISUAL_EVENTS.map((event) => ({
      t_s: event.timestamp,
      desc: event.content,
    })),
    concepts: ['flat tire replacement'],
    code_snippets: [],
    requirements: QJ_SOP_STEPS.map((step) => ({
      id: step.id,
      title: step.title,
      detail: step.description,
      priority: 'HIGH',
      tags: [],
    })),
    artifacts: [],
    stack: { tools: [] },
    visual_context: {
      visual_elements: QJ_VISUAL_EVENTS.map((event) => ({
        timestamp: event.timestamp,
        element_type: event.element_type ?? 'scene',
        content: event.content,
        confidence: 0.9,
      })),
      summary: 'Roadside tire replacement tools.',
      frame_analysis_count: 4,
    },
  };
}

function xymcExtractedSpec() {
  return {
    transcript: XYMC_TRANSCRIPT,
    keyframes: XYMC_VISUAL_EVENTS.map((event) => ({
      t_s: event.timestamp,
      desc: event.content,
    })),
    concepts: ['boring AI automations'],
    code_snippets: [],
    requirements: XYMC_SOP_STEPS.map((step) => ({
      id: step.id,
      title: step.title,
      detail: step.description,
      priority: 'HIGH',
      tags: [],
    })),
    artifacts: [],
    stack: { tools: [] },
    visual_context: {
      visual_elements: XYMC_VISUAL_EVENTS.map((event) => ({
        timestamp: event.timestamp,
        element_type: event.element_type ?? 'scene',
        content: event.content,
        confidence: 0.9,
      })),
      summary: 'n8n, Make, Retell AI demos.',
      frame_analysis_count: 4,
    },
  };
}

describe('GET /d/[videoId]/[[...asset]]', () => {
  it('serves the hosted compiled app index from a ready pack', async () => {
    const loaded = await loadHostedRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-18T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: loaded.applyExtractedSpec(identity, extractedSpec()),
    });

    const res = await loaded.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID }) },
    );

    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toContain('text/html');
    const body = await res.text();
    expect(body).toContain(`Video Pack ${QJ_VIDEO_ID}`);
    expect(body).toContain(`/d/${QJ_VIDEO_ID}/src/main.ts`);
  });

  it('serves transpiled JavaScript for hosted TypeScript assets', async () => {
    const loaded = await loadHostedRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-18T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: loaded.applyExtractedSpec(identity, extractedSpec()),
    });

    const res = await loaded.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}/src/main.ts`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID, asset: ['src', 'main.ts'] }) },
    );

    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toContain('application/javascript');
    const body = await res.text();
    expect(body).toContain('querySelector');
    expect(body).not.toContain('type ChecklistState');
  });

  it('serves the hosted compiled app index for XYMcBrFSJ4c banked pack', async () => {
    const loaded = await loadHostedRoute();
    const identity = loaded.buildIdentityPack(XYMC_VIDEO_ID, XYMC_SOURCE_URL, '2026-09-18T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: loaded.applyExtractedSpec(identity, xymcExtractedSpec()),
    });

    const res = await loaded.GET(
      new Request(`https://uvai.io/d/${XYMC_VIDEO_ID}`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: XYMC_VIDEO_ID }) },
    );

    expect(res.status).toBe(200);
    const body = await res.text();
    expect(body).toContain('nine boring AI automations');
    expect(body).toContain(`/d/${XYMC_VIDEO_ID}/src/main.ts`);
  });

  it('returns and records hosted health checks at /d/{videoId}/health', async () => {
    const loaded = await loadHostedRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-18T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: loaded.applyExtractedSpec(identity, extractedSpec()),
    });

    const first = await loaded.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}/health`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID, asset: ['health'] }) },
    );
    expect(first.status).toBe(200);

    const second = await loaded.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}/health`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID, asset: ['health'] }) },
    );
    const body = (await second.json()) as {
      videoId: string;
      live_url: string;
      health: { ok: boolean; status: number };
      store: { backend: string; ok: boolean };
      checks_recorded: number;
      factory_deliver: { ready: boolean; reason_code: string };
    };

    expect(second.status).toBe(200);
    expect(body.videoId).toBe(QJ_VIDEO_ID);
    expect(body.live_url).toBe(`/d/${QJ_VIDEO_ID}`);
    expect(body.health.ok).toBe(true);
    expect(body.store).toMatchObject({ backend: 'memory', ok: true });
    expect(body.checks_recorded).toBeGreaterThanOrEqual(2);
    expect(body.factory_deliver).toMatchObject({ ready: true, reason_code: 'FACTORY_DELIVER_READY' });
  });

  it('returns non-503 health for a missing pack with an honest reason_code', async () => {
    const loaded = await loadHostedRoute();
    const res = await loaded.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}/health`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID, asset: ['health'] }) },
    );
    const body = (await res.json()) as {
      health: { ok: boolean; reason_code: string; detail: string };
      store: { backend: string; ok: boolean };
      factory_deliver: { ready: boolean; reason_code: string };
    };
    expect(res.status).toBe(200);
    expect(body.health.ok).toBe(false);
    expect(body.health.reason_code).toBe('HOSTED_PACK_NOT_FOUND');
    expect(body.health.detail).toMatch(/pack not found/i);
    expect(body.store.backend).toBe('memory');
    expect(body.factory_deliver.ready).toBe(false);
    expect(body.factory_deliver.reason_code).toBe('FACTORY_DELIVER_HEALTH_FAILED');
  });

  it('returns HOSTED_PACK_STORE_ERROR when durable store read fails', async () => {
    const store = await import('@/lib/video-pack-store');
    store.resetVideoPackStoreForTests();
    const redis = {
      get: async () => {
        throw new Error('upstash read timeout');
      },
      set: async () => 'OK',
      eval: async () => {
        throw new Error('eval unavailable');
      },
    };
    store.setVideoPackRedisForTests(redis);
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://example.upstash.io');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'test-token');

    const route = await import('../route');
    const res = await route.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}/health`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID, asset: ['health'] }) },
    );
    const body = (await res.json()) as {
      health: { ok: boolean; reason_code: string };
      store: { backend: string; ok: boolean };
    };
    expect(res.status).toBe(200);
    expect(body.health.reason_code).toBe('HOSTED_PACK_STORE_ERROR');
    expect(body.store.backend).toBe('upstash');
    expect(body.store.ok).toBe(false);
  });

  it('returns non-503 health when pack extraction failed (no gateway 503 envelope)', async () => {
    const loaded = await loadHostedRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-18T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'error',
      video_id: identity.video_id,
      source_url: identity.source_url,
      source_hash: identity.provenance.source_hash,
      id: identity.id,
      error: 'Vercel AI Gateway returned empty content',
      failed_at: '2026-09-18T00:00:00.000Z',
    });

    const res = await loaded.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}/health`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID, asset: ['health'] }) },
    );
    const body = (await res.json()) as {
      error?: string;
      health: { ok: boolean; reason_code: string; detail: string };
    };
    expect(res.status).toBe(200);
    expect(body.error).toBeUndefined();
    expect(body.health.ok).toBe(false);
    expect(body.health.reason_code).toBe('HOSTED_PACK_EXTRACT_FAILED');
    expect(body.health.detail).toContain('empty content');
  });

  it('never returns HTTP 503 for /d/{videoId} HTML when extraction failed', async () => {
    const loaded = await loadHostedRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-18T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'error',
      video_id: identity.video_id,
      source_url: identity.source_url,
      source_hash: identity.provenance.source_hash,
      id: identity.id,
      error: 'Vercel AI Gateway returned empty content',
      failed_at: '2026-09-18T00:00:00.000Z',
    });

    const res = await loaded.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID }) },
    );
    const body = await res.text();
    expect(res.status).toBe(200);
    expect(res.status).not.toBe(503);
    expect(res.headers.get('content-type')).toContain('text/html');
    expect(body).toContain('Hosted app unavailable');
    expect(body).toContain('HOSTED_PACK_EXTRACT_FAILED');
    expect(body).not.toMatch(/^\s*\{\s*"error"\s*:\s*"Vercel AI Gateway/);
  });

  it('returns HTTP 200 HTML for live page when pack resolution throws', async () => {
    const store = await import('@/lib/video-pack-store');
    store.resetVideoPackStoreForTests();
    vi.spyOn(store, 'getPackRecordWithMeta').mockRejectedValue(
      new Error('Vercel AI Gateway returned empty content'),
    );
    const route = await import('../route');

    const res = await route.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID }) },
    );
    const body = await res.text();
    expect(res.status).toBe(200);
    expect(res.status).not.toBe(503);
    expect(res.headers.get('content-type')).toContain('text/html');
    expect(body).toContain('HOSTED_PACK_EXTRACT_FAILED');
    expect(body).not.toMatch(/^\s*\{\s*"error"\s*:\s*"Vercel AI Gateway/);
  });

  it('seals live page path via pathname when asset params are absent', async () => {
    const loaded = await loadHostedRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-18T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'error',
      video_id: identity.video_id,
      source_url: identity.source_url,
      source_hash: identity.provenance.source_hash,
      id: identity.id,
      error: 'Vercel AI Gateway returned empty content',
      failed_at: '2026-09-18T00:00:00.000Z',
    });

    const res = await loaded.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}/`, {
        method: 'GET',
        headers: { accept: 'text/html' },
      }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID, asset: undefined }) },
    );
    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toContain('text/html');
  });

  it('returns HTTP 200 health when pack resolution throws (gateway race sealed)', async () => {
    const store = await import('@/lib/video-pack-store');
    store.resetVideoPackStoreForTests();
    vi.spyOn(store, 'getPackRecordWithMeta').mockRejectedValue(
      new Error('Vercel AI Gateway returned empty content'),
    );
    const route = await import('../route');

    const res = await route.GET(
      new Request(`https://uvai.io/d/${QJ_VIDEO_ID}/health`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: QJ_VIDEO_ID, asset: ['health'] }) },
    );
    const body = (await res.json()) as {
      error?: string;
      health: { ok: boolean; reason_code: string };
    };
    expect(res.status).toBe(200);
    expect(body.error).toBeUndefined();
    expect(body.health.ok).toBe(false);
    expect(body.health.reason_code).toBe('HOSTED_PACK_EXTRACT_FAILED');
  });

  it('serves src/pack and src/pack.js from src/pack.ts', async () => {
    const loaded = await loadHostedRoute();
    const identity = loaded.buildIdentityPack(XYMC_VIDEO_ID, XYMC_SOURCE_URL, '2026-09-18T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: loaded.applyExtractedSpec(identity, xymcExtractedSpec()),
    });

    const packRes = await loaded.GET(
      new Request(`https://uvai.io/d/${XYMC_VIDEO_ID}/src/pack`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: XYMC_VIDEO_ID, asset: ['src', 'pack'] }) },
    );
    expect(packRes.status).toBe(200);
    expect(await packRes.text()).toContain(XYMC_VIDEO_ID);

    const jsRes = await loaded.GET(
      new Request(`https://uvai.io/d/${XYMC_VIDEO_ID}/src/pack.js`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: XYMC_VIDEO_ID, asset: ['src', 'pack.js'] }) },
    );
    expect(jsRes.status).toBe(200);
    expect(jsRes.headers.get('content-type')).toContain('application/javascript');

    const tsRes = await loaded.GET(
      new Request(`https://uvai.io/d/${XYMC_VIDEO_ID}/src/pack.ts`, { method: 'GET' }),
      { params: Promise.resolve({ videoId: XYMC_VIDEO_ID, asset: ['src', 'pack.ts'] }) },
    );
    expect(tsRes.status).toBe(200);
    expect(tsRes.headers.get('content-type')).toContain('application/javascript');
  });
});

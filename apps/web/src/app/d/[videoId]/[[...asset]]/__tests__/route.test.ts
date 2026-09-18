import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  QJ_PACK_ID,
  QJ_SOP_STEPS,
  QJ_SOURCE_HASH,
  QJ_SOURCE_URL,
  QJ_TRANSCRIPT,
  QJ_VIDEO_ID,
  QJ_VISUAL_EVENTS,
} from '@/lib/__fixtures__/qj-z5ohr7sga-emit';

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
    requirements: QJ_SOP_STEPS.map((step) => ({
      id: step.id,
      title: step.title,
      detail: step.description,
      priority: 'HIGH',
      tags: [],
    })),
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
      checks_recorded: number;
      factory_deliver: { ready: boolean; reason_code: string };
    };

    expect(second.status).toBe(200);
    expect(body.videoId).toBe(QJ_VIDEO_ID);
    expect(body.live_url).toBe(`/d/${QJ_VIDEO_ID}`);
    expect(body.health.ok).toBe(true);
    expect(body.checks_recorded).toBeGreaterThanOrEqual(2);
    expect(body.factory_deliver).toMatchObject({ ready: true, reason_code: 'FACTORY_DELIVER_READY' });
  });
});

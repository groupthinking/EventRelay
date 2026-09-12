import { afterEach, describe, expect, it, vi } from 'vitest';
import { identityHash } from '@/lib/video-pack';
import {
  QJ_FORBIDDEN_ARCHITECTURE,
  QJ_FORBIDDEN_CODE_SNIPPETS,
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

function getRequest(query: string) {
  return new Request(`http://localhost:3000/api/video/sandbox?${query}`, {
    method: 'GET',
  });
}

function postRequest(body: unknown) {
  return new Request('http://localhost:3000/api/video/sandbox', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

async function loadSandboxRoute() {
  const videoPack = await import('@/lib/video-pack');
  const store = await import('@/lib/video-pack-store');
  store.resetVideoPackStoreForTests();
  const route = await import('../route');
  return {
    GET: route.GET,
    POST: route.POST,
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
    code_snippets: QJ_FORBIDDEN_CODE_SNIPPETS,
    architecture: QJ_FORBIDDEN_ARCHITECTURE,
    artifacts: [
      {
        path_hint: 'tire_procedure.ts',
        purpose: 'Invented type dump',
        interface: 'interface ITireReplacement',
      },
    ],
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

describe('GET /api/video/sandbox', () => {
  it('returns 404 when the pack has not been ingested', async () => {
    const { GET } = await loadSandboxRoute();
    const res = await GET(getRequest(`source_hash=${QJ_SOURCE_HASH}`));
    expect(res.status).toBe(404);
    const body = (await res.json()) as { status?: string; error?: string };
    expect(body.status).toBe('error');
    expect(body.error).toMatch(/not found|pack/i);
  });

  it('returns 202 while the pack is still processing', async () => {
    const loaded = await loadSandboxRoute();
    loaded.seedVideoPackRecordForTests({
      state: 'processing',
      video_id: QJ_VIDEO_ID,
      source_url: QJ_SOURCE_URL,
      source_hash: QJ_SOURCE_HASH,
      id: QJ_PACK_ID,
      started_at: new Date().toISOString(),
    });
    const res = await loaded.GET(getRequest(`source_hash=${QJ_SOURCE_HASH}`));
    expect(res.status).toBe(202);
    const body = (await res.json()) as { status?: string };
    expect(body.status).toBe('processing');
  });

  it('materializes QjZ5ohr7sGA without architecture, code snippets, or a live URL', async () => {
    expect(identityHash(QJ_VIDEO_ID)).toBe(QJ_SOURCE_HASH);
    const loaded = await loadSandboxRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-12T00:00:00.000Z');
    const pack = loaded.applyExtractedSpec(identity, extractedSpec());
    loaded.seedVideoPackRecordForTests({ state: 'ready', pack });

    const res = await loaded.GET(getRequest(`source_hash=${QJ_SOURCE_HASH}`));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      status: string;
      data: {
        contract: string;
        cut: string;
        videoId: string;
        files: Record<string, string>;
        preview: { port: number; start: string; smoke: string };
      };
    };
    expect(body.status).toBe('success');
    expect(body.data.contract).toBe('app-builder-workspace');
    expect(body.data.cut).toBe('ingest→App Builder sandbox emit');
    expect(body.data.videoId).toBe(QJ_VIDEO_ID);
    expect(body.data.preview.port).toBe(8080);
    expect(body.data.preview.start).toBe('npm run dev');
    expect(body.data.preview.smoke).toBe('node scripts/browser-smoke.mjs');
    expect(body.data.files['startup.sh']).toContain('http://127.0.0.1:8080/');
    expect(body.data.files['index.html']).toContain(QJ_VIDEO_ID);
    expect(body.data.files['index.html']).toContain('five flat tires');
    expect(body.data.files['index.html']).toContain('Safety and Vehicle Staging');
    const shipped = JSON.stringify(body.data.files);
    expect(shipped).not.toMatch(/https:\/\/[a-z0-9-]+\.vercel\.app/i);
    expect(shipped).not.toContain('tire_procedure.ts');
    expect(shipped).not.toContain('TireChangeContext');
    expect(shipped).not.toContain('SimpleKnotState');
    expect(shipped).not.toMatch(/dpl_/);
  });
});

describe('POST /api/video/sandbox', () => {
  it('materializes from a stored pack for the paste-URL identity', async () => {
    const loaded = await loadSandboxRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-12T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: loaded.applyExtractedSpec(identity, extractedSpec()),
    });

    const res = await loaded.POST(postRequest({ url: QJ_SOURCE_URL }));
    expect(res.status).toBe(200);
    const body = (await res.json()) as { data: { files: Record<string, string> } };
    expect(body.data.files['scripts/browser-smoke.mjs']).toContain(QJ_VIDEO_ID);
    expect(body.data.files['index.html']).toContain('scissor jack');
  });

  it('does not start a new extract when the pack is missing', async () => {
    const loaded = await loadSandboxRoute();
    const res = await loaded.POST(postRequest({ url: QJ_SOURCE_URL }));
    expect(res.status).toBe(404);
    const body = (await res.json()) as { error?: string };
    expect(body.error).toMatch(/\/api\/video\/pack/i);
  });
});

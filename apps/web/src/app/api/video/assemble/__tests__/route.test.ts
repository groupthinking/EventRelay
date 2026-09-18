import { afterEach, describe, expect, it, vi } from 'vitest';
import { identityHash } from '@/lib/video-pack';
import {
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
  return new Request(`http://localhost:3000/api/video/assemble?${query}`, {
    method: 'GET',
  });
}

function postRequest(body: unknown) {
  return new Request('http://localhost:3000/api/video/assemble', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

async function loadAssembleRoute() {
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
    architecture: {
      summary: 'Procedural pipeline for roadside tire changing and validation.',
      stages: [{ id: 'stage_1', name: 'Vehicle Staging', description: 'Park safely.' }],
      mermaid: null,
    },
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

describe('GET /api/video/assemble', () => {
  it('returns 404 when the pack has not been ingested', async () => {
    const { GET } = await loadAssembleRoute();
    const res = await GET(getRequest(`source_hash=${QJ_SOURCE_HASH}`));
    expect(res.status).toBe(404);
    const body = (await res.json()) as { status?: string; error?: string };
    expect(body.status).toBe('error');
    expect(body.error).toMatch(/not found|pack/i);
  });

  it('returns a planned receipt with untested gates and no invented architecture', async () => {
    expect(identityHash(QJ_VIDEO_ID)).toBe(QJ_SOURCE_HASH);
    const loaded = await loadAssembleRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-12T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: loaded.applyExtractedSpec(identity, extractedSpec()),
    });

    const res = await loaded.GET(getRequest(`source_hash=${QJ_SOURCE_HASH}`));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      status: string;
      data: {
        videoId: string;
        files: Record<string, string>;
        assembly: {
          videoId: string;
          sourceHash: string;
          filesDigest: string;
          identityDigest: string;
          gates: Array<{ name: string; status: string }>;
          unresolved: Array<{ id: string }>;
          claims: { recreates_demonstrated_app: boolean; live_deploy_url: boolean };
        };
      };
    };
    expect(body.status).toBe('success');
    expect(body.data.videoId).toBe(QJ_VIDEO_ID);
    expect(body.data.assembly.videoId).toBe(QJ_VIDEO_ID);
    expect(body.data.assembly.sourceHash).toBe(QJ_SOURCE_HASH);
    expect(body.data.assembly.filesDigest).toMatch(/^[a-f0-9]{64}$/);
    expect(body.data.assembly.identityDigest).toMatch(/^[a-f0-9]{64}$/);
    expect(body.data.assembly.gates.every((gate) => gate.status === 'untested')).toBe(true);
    expect(body.data.assembly.unresolved.some((row) => row.id === 'viewer-not-recreation')).toBe(true);
    expect(body.data.assembly.claims.recreates_demonstrated_app).toBe(false);
    expect(body.data.assembly.claims.live_deploy_url).toBe(false);
    expect(body.data.files['index.html']).toContain('five flat tires');
    expect(JSON.stringify(body.data.files)).not.toContain('tire_procedure.ts');
    expect(JSON.stringify(body.data.files)).not.toContain('TireChangeContext');
  });
});

describe('POST /api/video/assemble', () => {
  it('materializes the planned receipt from a stored pack URL', async () => {
    const loaded = await loadAssembleRoute();
    const identity = loaded.buildIdentityPack(QJ_VIDEO_ID, QJ_SOURCE_URL, '2026-09-12T00:00:00.000Z');
    loaded.seedVideoPackRecordForTests({
      state: 'ready',
      pack: loaded.applyExtractedSpec(identity, extractedSpec()),
    });

    const res = await loaded.POST(postRequest({ url: QJ_SOURCE_URL }));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      data: { packId: string; assembly: { packId: string; gates: Array<{ status: string }> } };
    };
    expect(body.data.packId).toBe(QJ_PACK_ID);
    expect(body.data.assembly.packId).toBe(QJ_PACK_ID);
    expect(body.data.assembly.gates.every((gate) => gate.status === 'untested')).toBe(true);
  });
});

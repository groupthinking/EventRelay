import { afterEach, describe, expect, it, vi } from 'vitest';
import { GOLDEN_IDENTITY_HASHES } from '@/lib/video-pack';
import { emitVideoPack, identityPackJson, verifyIdentityPack } from '@/lib/emit-video-pack';

const CANON = 'jNQXAC9IVRw';
const SOURCE_URL = `https://www.youtube.com/watch?v=${CANON}`;
const HASH = GOLDEN_IDENTITY_HASHES[CANON];

const VALID = {
  status: 'success',
  data: {
    version: 'v0',
    id: `vp:v0:${CANON}`,
    video_id: CANON,
    source_url: SOURCE_URL,
    transcript: { full_text: `cite:youtube:${CANON}`, segments: [] },
    provenance: { source_hash: HASH },
  },
};

describe('verifyIdentityPack (CoS: fail closed)', () => {
  it('accepts a v0 pack with source_url and source_hash', () => {
    const citation = verifyIdentityPack(VALID);
    expect(citation.sourceUrl).toBe(SOURCE_URL);
    expect(citation.sourceHash).toBe(HASH);
    expect(citation.videoId).toBe(CANON);
    expect(citation.pack.source_url).toBe(SOURCE_URL);
    expect(citation.pack.provenance.source_hash).toBe(HASH);
    expect(identityPackJson(citation)).toContain(SOURCE_URL);
    expect(identityPackJson(citation)).toContain(HASH);
  });

  it('passes architecture, artifacts, and stack.tools through a ready pack', () => {
    const citation = verifyIdentityPack({
      status: 'success',
      data: {
        ...VALID.data,
        transcript: {
          language: 'en',
          full_text: 'Cloudflare Workers pay via x402.',
          segments: [],
        },
        architecture: {
          summary: 'decode to rails',
          stages: [{ id: 'decode', name: 'decode', description: 'frames' }],
          mermaid: 'flowchart LR\ndecode-->rails',
        },
        artifacts: [
          {
            path_hint: 'src/mcp_x402_gateway.ts',
            purpose: 'Paid MCP gateway',
            interface: 'createGateway(config: GatewayConfig): Gateway',
          },
        ],
        stack: {
          tools: [
            { name: 'Cloudflare', evidence: 'spoken' },
            { name: 'x402', evidence: 'rail' },
          ],
        },
      },
    });
    expect(citation.pack.stack?.tools.map((tool) => tool.name)).toEqual(['Cloudflare', 'x402']);
    expect(citation.pack.architecture?.stages[0]?.id).toBe('decode');
    expect(citation.pack.artifacts?.[0]?.path_hint).toBe('src/mcp_x402_gateway.ts');
    expect(JSON.stringify(citation.pack)).not.toMatch(/shopify/i);
    expect(citation.sourceHash).toBe(HASH);
  });

  it('fails closed when source_url is missing', () => {
    const { source_url: _omit, ...data } = VALID.data;
    expect(() => verifyIdentityPack({ status: 'success', data })).toThrow(/source_url/i);
  });

  it('fails closed when source_hash is missing', () => {
    expect(() =>
      verifyIdentityPack({
        status: 'success',
        data: { ...VALID.data, provenance: {} },
      }),
    ).toThrow(/source_hash/i);
  });

  it('fails closed on an empty or 401 payload', () => {
    expect(() => verifyIdentityPack({ error: 'Authentication required' })).toThrow(/verif/i);
    expect(() => verifyIdentityPack(null)).toThrow(/verif/i);
  });
});

describe('emitVideoPack', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('returns a cached pack from POST without polling', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => VALID,
    });
    vi.stubGlobal('fetch', fetchMock);
    const citation = await emitVideoPack(SOURCE_URL, { pollIntervalMs: 0 });
    expect(citation.sourceHash).toBe(HASH);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/video/pack');
  });

  it('polls GET after a processing POST and returns the ready pack', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 202,
        json: async () => ({
          status: 'processing',
          data: {
            id: `vp:v0:${CANON}`,
            video_id: CANON,
            source_url: SOURCE_URL,
            provenance: { source_hash: HASH },
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => VALID,
      });
    vi.stubGlobal('fetch', fetchMock);
    const citation = await emitVideoPack(SOURCE_URL, { pollIntervalMs: 0, timeoutMs: 5_000 });
    expect(citation.sourceHash).toBe(HASH);
    expect(citation.videoId).toBe(CANON);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain(`source_hash=${HASH}`);
  });

  it('fails closed when the anonymous GET reports a visible extract error', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 202,
        json: async () => ({
          status: 'processing',
          data: {
            id: `vp:v0:${CANON}`,
            video_id: CANON,
            source_url: SOURCE_URL,
            provenance: { source_hash: HASH },
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({
          status: 'error',
          error:
            'Video pack spec extract requires AI Gateway (AI_GATEWAY_API_KEY or VERCEL_AI_GATEWAY_API_KEY) and model google/gemini-3.8-flash.',
        }),
      });
    vi.stubGlobal('fetch', fetchMock);
    await expect(emitVideoPack(SOURCE_URL, { pollIntervalMs: 0, timeoutMs: 5_000 })).rejects.toThrow(
      /AI Gateway/i,
    );
  });
});

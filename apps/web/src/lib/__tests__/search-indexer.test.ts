import { describe, it, expect, afterEach, vi } from 'vitest';

const upsertMock = vi.fn();

vi.mock('@upstash/search', () => ({
  Search: class {
    index() {
      return { upsert: upsertMock, search: vi.fn() };
    }
  },
}));

import { buildVideoPackDocuments, indexVideoPack } from '@/lib/search-indexer';
import type { VideoPackV0Json } from '@/lib/video-pack';

const ENV_KEYS = ['UPSTASH_SEARCH_REST_URL', 'UPSTASH_SEARCH_REST_TOKEN'] as const;
const ORIGINAL_ENV = Object.fromEntries(ENV_KEYS.map((k) => [k, process.env[k]]));

function pack(overrides: Partial<VideoPackV0Json> = {}): VideoPackV0Json {
  return {
    version: 'v0',
    id: 'vp:v0:auJzb1D-fag',
    video_id: 'auJzb1D-fag',
    source_url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    transcript: {
      language: 'en',
      full_text: 'Welcome to the video. Today we deploy to the cloud.',
      segments: [
        { idx: 0, start_s: 0, end_s: 30, text: 'Welcome to the video.' },
        { idx: 1, start_s: 30, end_s: 60, text: 'Today we deploy to the cloud.' },
      ],
    },
    keyframes: [],
    concepts: ['deployment', 'cloud'],
    requirements: [{ id: 'r1', title: 'Ship the app' }],
    code_snippets: [],
    architecture: null,
    artifacts: [],
    stack: { tools: [] },
    chapters: [],
    action_items: [{ id: 'a1', title: 'Run the deploy', description: 'Deploy it' }],
    visual_context: null,
    metrics: {},
    provenance: {
      created_at: new Date().toISOString(),
      tool_versions: { videopack: 'v0' },
      source_hash: 'a'.repeat(64),
      notes: 'test fixture',
    },
    ...overrides,
  };
}

afterEach(() => {
  for (const key of ENV_KEYS) {
    const original = ORIGINAL_ENV[key];
    if (original === undefined) delete process.env[key];
    else process.env[key] = original;
  }
  upsertMock.mockReset();
});

describe('buildVideoPackDocuments', () => {
  it('emits a summary document plus transcript chunks with pack provenance', () => {
    const docs = buildVideoPackDocuments(pack());
    expect(docs[0].id).toBe('video:auJzb1D-fag');
    expect(docs[0].content.topics).toBe('deployment, cloud');
    expect(docs[0].content.action_items).toBe('Run the deploy');
    expect(docs[0].content.requirements).toBe('Ship the app');
    expect(docs[0].metadata?.type).toBe('video_summary');
    // Evidence lineage: every document traces back to the hashed pack.
    expect(docs[0].metadata?.source_hash).toBe('a'.repeat(64));

    const chunkDocs = docs.slice(1);
    expect(chunkDocs.length).toBeGreaterThan(0);
    expect(chunkDocs[0].id).toBe('video:auJzb1D-fag:t0');
    expect(chunkDocs[0].content.text).toContain('Welcome to the video.');
    expect(chunkDocs[0].metadata?.type).toBe('transcript_chunk');
    expect(chunkDocs[0].metadata?.startSeconds).toBe(0);
    expect(chunkDocs[0].metadata?.source_hash).toBe('a'.repeat(64));
  });

  it('caps transcript documents at 40 chunks', () => {
    const longSegments = Array.from({ length: 60 }, (_, i) => ({
      idx: i,
      start_s: i * 30,
      end_s: (i + 1) * 30,
      text: 'x'.repeat(1600),
    }));
    const docs = buildVideoPackDocuments(
      pack({ transcript: { language: 'en', full_text: '', segments: longSegments } }),
    );
    expect(docs).toHaveLength(41); // 1 summary + 40 capped chunks
  });

  it('skips empty transcript segments', () => {
    const docs = buildVideoPackDocuments(
      pack({
        transcript: {
          language: 'en',
          full_text: '',
          segments: [{ idx: 0, start_s: 0, end_s: 10, text: '   ' }],
        },
      }),
    );
    expect(docs).toHaveLength(1); // summary only
  });
});

describe('indexVideoPack', () => {
  it('returns null and does not upsert when Upstash Search is unconfigured', async () => {
    delete process.env.UPSTASH_SEARCH_REST_URL;
    delete process.env.UPSTASH_SEARCH_REST_TOKEN;
    const result = await indexVideoPack(pack());
    expect(result).toBeNull();
    expect(upsertMock).not.toHaveBeenCalled();
  });

  it('upserts the built documents and returns the count when configured', async () => {
    process.env.UPSTASH_SEARCH_REST_URL = 'https://example-search.upstash.io';
    process.env.UPSTASH_SEARCH_REST_TOKEN = 'test-token';
    const result = await indexVideoPack(pack());
    expect(result).toBeGreaterThanOrEqual(2);
    expect(upsertMock).toHaveBeenCalledTimes(1);
    const docs = upsertMock.mock.calls[0][0];
    expect(docs[0].id).toBe('video:auJzb1D-fag');
    expect(docs[0].metadata?.source_hash).toBe('a'.repeat(64));
  });

  it('returns null instead of throwing when the upsert fails (ancillary contract)', async () => {
    process.env.UPSTASH_SEARCH_REST_URL = 'https://example-search.upstash.io';
    process.env.UPSTASH_SEARCH_REST_TOKEN = 'test-token';
    upsertMock.mockRejectedValueOnce(new Error('index down'));
    const result = await indexVideoPack(pack());
    expect(result).toBeNull();
  });
});

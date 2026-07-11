import { describe, it, expect, afterEach, vi } from 'vitest';

const upsertMock = vi.fn();

vi.mock('@upstash/search', () => ({
  Search: class {
    index() {
      return { upsert: upsertMock, search: vi.fn() };
    }
  },
}));

import {
  buildVideoDocuments,
  extractVideoId,
  indexVideoAnalysis,
} from '@/lib/search-indexer';
import type { VideoAnalysisResult } from '@/lib/gemini-video-analyzer';

const ENV_KEYS = ['UPSTASH_SEARCH_REST_URL', 'UPSTASH_SEARCH_REST_TOKEN'] as const;
const ORIGINAL_ENV = Object.fromEntries(ENV_KEYS.map((k) => [k, process.env[k]]));

function analysis(overrides: Partial<VideoAnalysisResult> = {}): VideoAnalysisResult {
  return {
    title: 'Deploying with E22',
    summary: 'A walkthrough of cloud deployment.',
    transcript: [
      { start: 0, duration: 30, text: 'Welcome to the video.' },
      { start: 30, duration: 30, text: 'Today we deploy to the cloud.' },
    ],
    events: [
      {
        timestamp: 10,
        label: 'Setup CLI',
        description: 'Install the CLI',
        codeMapping: 'npm i -g cli',
        cloudService: 'E22',
      },
    ],
    actions: [],
    topics: ['deployment', 'cloud'],
    architectureCode: '',
    ingestScript: '',
    e22Snippets: [],
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

describe('extractVideoId', () => {
  it('pulls the v= param from a watch URL', () => {
    expect(extractVideoId('https://www.youtube.com/watch?v=abc-123&t=5')).toBe('abc-123');
  });

  it('sanitizes non-watch URLs into a safe id', () => {
    expect(extractVideoId('https://youtu.be/xyz')).toBe('https___youtu_be_xyz');
  });
});

describe('buildVideoDocuments', () => {
  it('emits a summary document plus transcript chunks with string content', () => {
    const docs = buildVideoDocuments('https://www.youtube.com/watch?v=vid1', analysis());
    expect(docs[0].id).toBe('video:vid1');
    expect(docs[0].content.topics).toBe('deployment, cloud');
    expect(docs[0].content.events).toBe('Setup CLI');
    expect(docs[0].metadata?.type).toBe('video_summary');

    const chunkDocs = docs.slice(1);
    expect(chunkDocs.length).toBeGreaterThan(0);
    expect(chunkDocs[0].id).toBe('video:vid1:t0');
    expect(chunkDocs[0].content.text).toContain('Welcome to the video.');
    expect(chunkDocs[0].metadata?.type).toBe('transcript_chunk');
    expect(chunkDocs[0].metadata?.startSeconds).toBe(0);
  });

  it('caps transcript documents at 40 chunks', () => {
    const longTranscript = Array.from({ length: 60 }, (_, i) => ({
      start: i * 30,
      duration: 30,
      text: 'x'.repeat(1600),
    }));
    const docs = buildVideoDocuments(
      'https://www.youtube.com/watch?v=long1',
      analysis({ transcript: longTranscript }),
    );
    expect(docs).toHaveLength(41); // 1 summary + 40 capped chunks
  });

  it('skips empty transcript segments', () => {
    const docs = buildVideoDocuments(
      'https://www.youtube.com/watch?v=vid2',
      analysis({ transcript: [{ start: 0, duration: 10, text: '   ' }] }),
    );
    expect(docs).toHaveLength(1); // summary only
  });
});

describe('indexVideoAnalysis', () => {
  it('returns null and does not upsert when Upstash Search is unconfigured', async () => {
    delete process.env.UPSTASH_SEARCH_REST_URL;
    delete process.env.UPSTASH_SEARCH_REST_TOKEN;
    const result = await indexVideoAnalysis('https://www.youtube.com/watch?v=vid1', analysis());
    expect(result).toBeNull();
    expect(upsertMock).not.toHaveBeenCalled();
  });

  it('upserts the built documents and returns the count when configured', async () => {
    process.env.UPSTASH_SEARCH_REST_URL = 'https://example-search.upstash.io';
    process.env.UPSTASH_SEARCH_REST_TOKEN = 'test-token';
    const result = await indexVideoAnalysis('https://www.youtube.com/watch?v=vid1', analysis());
    expect(result).toBeGreaterThanOrEqual(2);
    expect(upsertMock).toHaveBeenCalledTimes(1);
    const docs = upsertMock.mock.calls[0][0];
    expect(docs[0].id).toBe('video:vid1');
  });
});

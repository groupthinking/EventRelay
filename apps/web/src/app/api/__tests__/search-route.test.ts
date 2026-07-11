import { describe, it, expect, afterEach, vi } from 'vitest';

const searchMock = vi.fn();
const upsertMock = vi.fn();

vi.mock('@upstash/search', () => ({
  Search: class {
    index() {
      return { search: searchMock, upsert: upsertMock };
    }
  },
}));

import { POST, PUT } from '@/app/api/search/route';
import { NextRequest } from 'next/server';

const ENV_KEYS = [
  'UPSTASH_SEARCH_REST_URL',
  'UPSTASH_SEARCH_REST_TOKEN',
  'UPSTASH_SEARCH_INDEX',
  'INTERNAL_REQUEST_TOKEN',
] as const;
const ORIGINAL_ENV = Object.fromEntries(ENV_KEYS.map((k) => [k, process.env[k]]));

function configureSearch() {
  process.env.UPSTASH_SEARCH_REST_URL = 'https://example-search.upstash.io';
  process.env.UPSTASH_SEARCH_REST_TOKEN = 'test-token';
}

function postReq(body: unknown) {
  return new NextRequest('http://localhost/api/search', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function putReq(body: unknown, headers: Record<string, string> = {}) {
  return new NextRequest('http://localhost/api/search', {
    method: 'PUT',
    headers: { 'content-type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });
}

afterEach(() => {
  for (const key of ENV_KEYS) {
    const original = ORIGINAL_ENV[key];
    if (original === undefined) delete process.env[key];
    else process.env[key] = original;
  }
  searchMock.mockReset();
  upsertMock.mockReset();
});

describe('POST /api/search', () => {
  it('returns 503 when Upstash Search env is not configured', async () => {
    delete process.env.UPSTASH_SEARCH_REST_URL;
    delete process.env.UPSTASH_SEARCH_REST_TOKEN;
    const res = await POST(postReq({ query: 'hello' }));
    expect(res.status).toBe(503);
    expect((await res.json()).error).toBe('search_not_configured');
  });

  it('returns 400 on a missing query', async () => {
    configureSearch();
    const res = await POST(postReq({}));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toBe('missing_query');
  });

  it('returns results from the index', async () => {
    configureSearch();
    searchMock.mockResolvedValue([
      { id: 'vid-1', content: { title: 'Hello world' }, score: 0.92 },
    ]);
    const res = await POST(postReq({ query: 'hello world', limit: 3 }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.success).toBe(true);
    expect(body.results).toHaveLength(1);
    expect(searchMock).toHaveBeenCalledWith({ query: 'hello world', limit: 3 });
  });

  it('clamps limit into [1, 25]', async () => {
    configureSearch();
    searchMock.mockResolvedValue([]);
    await POST(postReq({ query: 'x', limit: 999 }));
    expect(searchMock).toHaveBeenCalledWith({ query: 'x', limit: 25 });
  });

  it('surfaces index failures as 502 (no fabricated results)', async () => {
    configureSearch();
    searchMock.mockRejectedValue(new Error('index unavailable'));
    const res = await POST(postReq({ query: 'x' }));
    expect(res.status).toBe(502);
    expect((await res.json()).error).toBe('search_failed');
  });
});

describe('PUT /api/search (internal upsert)', () => {
  const DOC = { id: 'vid-1', content: { title: 'Hello' } };

  it('fails closed with 503 when INTERNAL_REQUEST_TOKEN is unset', async () => {
    configureSearch();
    delete process.env.INTERNAL_REQUEST_TOKEN;
    const res = await PUT(putReq({ documents: [DOC] }));
    expect(res.status).toBe(503);
  });

  it('rejects a wrong internal token with 401', async () => {
    configureSearch();
    process.env.INTERNAL_REQUEST_TOKEN = 'secret';
    const res = await PUT(putReq({ documents: [DOC] }, { 'x-eventrelay-internal': 'wrong' }));
    expect(res.status).toBe(401);
    expect(upsertMock).not.toHaveBeenCalled();
  });

  it('rejects malformed documents with 400', async () => {
    configureSearch();
    process.env.INTERNAL_REQUEST_TOKEN = 'secret';
    const res = await PUT(
      putReq({ documents: [{ id: '', content: {} }] }, { 'x-eventrelay-internal': 'secret' }),
    );
    expect(res.status).toBe(400);
  });

  it('upserts valid documents', async () => {
    configureSearch();
    process.env.INTERNAL_REQUEST_TOKEN = 'secret';
    upsertMock.mockResolvedValue(undefined);
    const res = await PUT(putReq({ documents: [DOC] }, { 'x-eventrelay-internal': 'secret' }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.upserted).toBe(1);
    expect(upsertMock).toHaveBeenCalledWith([DOC]);
  });
});

import { NextRequest, NextResponse } from 'next/server';
import { formatApiError } from '@/lib/error-handling';
import { getSearchIndex, resolveSearchIndexName } from '@/lib/upstash-search';
import type { SearchDocument } from '@/lib/upstash-search';

const MAX_LIMIT = 25;
const DEFAULT_LIMIT = 5;
const MAX_UPSERT_BATCH = 100;

/**
 * POST /api/search — cross-video full-text/semantic search via Upstash Search.
 * Body: { query: string, limit?: number }
 */
export async function POST(req: NextRequest) {
  const index = getSearchIndex();
  if (!index) {
    return NextResponse.json(
      { error: 'search_not_configured', detail: 'UPSTASH_SEARCH_REST_URL / UPSTASH_SEARCH_REST_TOKEN are not set.' },
      { status: 503 },
    );
  }

  let body: { query?: unknown; limit?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'invalid_json' }, { status: 400 });
  }

  const query = typeof body.query === 'string' ? body.query.trim() : '';
  if (!query) {
    return NextResponse.json({ error: 'missing_query' }, { status: 400 });
  }
  const rawLimit = typeof body.limit === 'number' && Number.isFinite(body.limit) ? body.limit : DEFAULT_LIMIT;
  const limit = Math.min(Math.max(Math.trunc(rawLimit), 1), MAX_LIMIT);

  try {
    const results = await index.search({ query, limit });
    return NextResponse.json({
      success: true,
      index: resolveSearchIndexName(),
      query,
      results,
    });
  } catch (error) {
    console.error('Upstash search error:', error);
    return NextResponse.json(
      { error: 'search_failed', detail: formatApiError(error).message },
      { status: 502 },
    );
  }
}

/**
 * PUT /api/search — upsert documents into the search index.
 * Server-to-server only: requires the x-eventrelay-internal header to match
 * INTERNAL_REQUEST_TOKEN (same trust mechanism as the middleware bypass).
 * Body: { documents: Array<{ id: string, content: Record<string,string>, metadata? }> }
 */
export async function PUT(req: NextRequest) {
  const internalToken = process.env.INTERNAL_REQUEST_TOKEN?.trim();
  if (!internalToken) {
    // Fail closed: without a configured token there is no legitimate caller.
    return NextResponse.json({ error: 'ingest_not_configured' }, { status: 503 });
  }
  if (req.headers.get('x-eventrelay-internal') !== internalToken) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const index = getSearchIndex();
  if (!index) {
    return NextResponse.json(
      { error: 'search_not_configured', detail: 'UPSTASH_SEARCH_REST_URL / UPSTASH_SEARCH_REST_TOKEN are not set.' },
      { status: 503 },
    );
  }

  let body: { documents?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'invalid_json' }, { status: 400 });
  }

  const documents = Array.isArray(body.documents) ? (body.documents as SearchDocument[]) : [];
  if (documents.length === 0 || documents.length > MAX_UPSERT_BATCH) {
    return NextResponse.json(
      { error: 'invalid_documents', detail: `Provide 1–${MAX_UPSERT_BATCH} documents.` },
      { status: 400 },
    );
  }
  const malformed = documents.find(
    (d) => !d || typeof d.id !== 'string' || !d.id.trim() || typeof d.content !== 'object' || d.content === null,
  );
  if (malformed !== undefined) {
    return NextResponse.json(
      { error: 'invalid_documents', detail: 'Each document needs a non-empty string id and a content object.' },
      { status: 400 },
    );
  }

  try {
    await index.upsert(documents);
    return NextResponse.json({
      success: true,
      index: resolveSearchIndexName(),
      upserted: documents.length,
    });
  } catch (error) {
    console.error('Upstash upsert error:', error);
    return NextResponse.json(
      { error: 'upsert_failed', detail: formatApiError(error).message },
      { status: 502 },
    );
  }
}

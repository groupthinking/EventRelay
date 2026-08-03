import { NextResponse } from 'next/server';
import { backendHeaders } from '@/lib/pipeline-backend';
import { formatApiError } from '@/lib/error-handling';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : '';

export const runtime = 'nodejs';

/**
 * GET /api/jobs/{jobId}
 *
 * Proxies backend async video job status (see-script-ship / Phase 4 contract).
 */
export async function GET(
  _request: Request,
  context: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await context.params;

  if (!jobId?.trim()) {
    return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
  }

  if (!BACKEND_URL) {
    return NextResponse.json({ error: 'BACKEND_URL is not configured' }, { status: 503 });
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/jobs/${encodeURIComponent(jobId)}`, {
      cache: 'no-store',
      headers: backendHeaders(),
      signal: AbortSignal.timeout(15_000),
    });

    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Job fetch error:', error);
    // SECURITY: Prevent information disclosure by masking the raw error message
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 502 },
    );
  }
}
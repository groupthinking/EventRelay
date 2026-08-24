import { NextResponse } from 'next/server';
import { backendHeaders, resolveBackendCapability } from '@/lib/backend/capability';

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

  // Resolved per-request through the shared resolver so this picks up
  // NEXT_PUBLIC_BACKEND_URL as well as BACKEND_URL (audit finding F1).
  const capability = resolveBackendCapability();
  if (!capability.configured || !capability.url) {
    return NextResponse.json(
      {
        error: 'Backend is not configured. Set BACKEND_URL (or NEXT_PUBLIC_BACKEND_URL).',
        reason: capability.reason,
      },
      { status: 503 },
    );
  }

  try {
    const response = await fetch(`${capability.url}/api/v1/jobs/${encodeURIComponent(jobId)}`, {
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

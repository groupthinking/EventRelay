import { NextResponse } from 'next/server';
import { backendHeaders, resolveBackendCapability } from '@/lib/backend/capability';

/**
 * Dashboard metrics + Looker embed proxy.
 *
 * Previously this module computed a `BACKEND_AVAILABLE` flag at import time and
 * then never read it, so both handlers fetched the `http://localhost:8000`
 * placeholder on every production request. GET swallowed the connection error
 * and reported `status: 'degraded'` — indistinguishable from a real backend
 * outage — while POST returned a generic 500. Resolution now happens
 * per-request through the shared capability resolver, and an unconfigured
 * backend is reported as exactly that.
 */

export async function GET() {
  const capability = resolveBackendCapability();
  if (!capability.configured || !capability.url) {
    return NextResponse.json({
      status: 'unconfigured',
      timestamp: new Date().toISOString(),
      reason: capability.reason,
      metrics: { activeWorkflows: 0, totalProcessed: 0, errorRate: 0 },
    });
  }

  try {
    const response = await fetch(`${capability.url}/api/v1/health`, {
      headers: backendHeaders(),
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      throw new Error(`Backend health check failed: ${response.status}`);
    }

    const healthData = await response.json();

    return NextResponse.json({
      status: 'operational',
      timestamp: new Date().toISOString(),
      metrics: {
        activeWorkflows: healthData.active_connections || 0,
        totalProcessed: healthData.total_requests || 0,
        errorRate: 0,
      },
    });
  } catch (error) {
    console.error('Dashboard stats error:', error);
    // Honest fallback: the backend is configured but not answering right now.
    return NextResponse.json({
      status: 'degraded',
      timestamp: new Date().toISOString(),
      reason: error instanceof Error ? error.message : String(error),
      metrics: { activeWorkflows: 0, totalProcessed: 0, errorRate: 0 },
    });
  }
}

export async function POST(request: Request) {
  const capability = resolveBackendCapability();
  if (!capability.configured || !capability.url) {
    return NextResponse.json(
      {
        error:
          'Reporting backend not configured. Set BACKEND_URL (or NEXT_PUBLIC_BACKEND_URL).',
        reason: capability.reason,
      },
      { status: 503 },
    );
  }

  try {
    const body = await request.json();

    const response = await fetch(`${capability.url}/api/v1/reporting/embed/dashboard`, {
      method: 'POST',
      // Shared builder trims EVENTRELAY_API_KEY; the previous inline header did
      // not, so a Secret Manager newline produced a silent 401.
      headers: backendHeaders(),
      body: JSON.stringify({
        dashboard_id: body.dashboard_id || 'events_overview',
        tenant_id: body.tenant_id || 'tenant_default',
        user_id: body.user_id || 'user_demo',
        user_email: body.user_email || 'demo@example.com',
      }),
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Backend Looker service failed: ${response.status} ${errText}`);
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error('Dashboard embed error:', error);
    return NextResponse.json(
      { error: 'Failed to retrieve dashboard embed URL' },
      { status: 500 },
    );
  }
}

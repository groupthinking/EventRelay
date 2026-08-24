import { NextResponse } from 'next/server';
import { backendHeaders, resolveBackendCapability } from '@/lib/backend/capability';

/**
 * GET /api/agents/status?agentId=...
 *
 * Proxy to FastAPI `GET /api/v1/agents/{agent_id}/status` so the UI can poll a
 * dispatched agent's progress without exposing the backend URL to the browser.
 */
export async function GET(request: Request) {
  const capability = resolveBackendCapability();
  if (!capability.configured || !capability.url) {
    return NextResponse.json(
      { error: 'Agent backend not configured.', reason: capability.reason },
      { status: 503 },
    );
  }
  const base = capability.url;

  const agentId = new URL(request.url).searchParams.get('agentId');
  if (!agentId) {
    return NextResponse.json({ error: 'agentId is required' }, { status: 400 });
  }

  try {
    const res = await fetch(`${base}/api/v1/agents/${encodeURIComponent(agentId)}/status`, {
      headers: backendHeaders(),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) {
      throw new Error(`Backend status failed: ${res.status}`);
    }
    return NextResponse.json(await res.json());
  } catch (error) {
    console.error('Agent status error:', error);
    return NextResponse.json(
      { error: 'Failed to get agent status', details: String(error) },
      { status: 502 },
    );
  }
}

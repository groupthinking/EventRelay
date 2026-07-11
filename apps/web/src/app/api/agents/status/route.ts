import { NextResponse } from 'next/server';
import { backendHeaders } from '@/lib/pipeline-backend';

/** Resolve the FastAPI backend base URL, or null if not configured. */
function backendBaseUrl(): string | null {
  const raw = process.env.BACKEND_URL || '';
  return raw.startsWith('http') ? raw : null;
}

/**
 * GET /api/agents/status?agentId=...
 *
 * Proxy to FastAPI `GET /api/v1/agents/{agent_id}/status` so the UI can poll a
 * dispatched agent's progress without exposing the backend URL to the browser.
 */
export async function GET(request: Request) {
  const base = backendBaseUrl();
  if (!base) {
    return NextResponse.json({ error: 'Agent backend not configured.' }, { status: 503 });
  }

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

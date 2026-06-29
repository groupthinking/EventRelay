import { NextResponse } from 'next/server';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { isProSubscriber } from '@/lib/billing/entitlement-store';
import { kaizenObserve } from '@/lib/billing/kaizen-trace';

/** Resolve the FastAPI backend base URL, or null if not configured. */
function backendBaseUrl(): string | null {
  const raw = process.env.BACKEND_URL || '';
  return raw.startsWith('http') ? raw : null;
}

/**
 * GET /api/agents/dispatch
 *
 * Lightweight availability probe so the UI can decide whether to surface the
 * "dispatch agents" action. The backend agent + MCP orchestration layer only
 * exists when a FastAPI server is reachable (Vercel has none by default).
 */
export async function GET() {
  return NextResponse.json({ available: backendBaseUrl() !== null });
}

/**
 * POST /api/agents/dispatch
 *
 * Proxy to FastAPI `POST /api/v1/agents/dispatch`, which hands the extracted
 * events to the MCP agent orchestrator. Returns 503 honestly when no backend
 * is configured rather than fabricating a result (REAL_MODE_ONLY).
 */
export async function POST(request: Request) {
  const body = await request.json();
  const billingEmail = await resolveTrustedBillingEmail(request);
  const isPro = await isProSubscriber(billingEmail);
  if (!isPro) {
    kaizenObserve('billing', 'dispatch_blocked', 'Agent dispatch requires Pro', {
      decision: `email=${billingEmail ?? 'anonymous'}`,
      fix: 'upgrade_to_pro',
    });
    return NextResponse.json(
      {
        error: 'Agent dispatch is a Pro feature. Upgrade at /pricing.',
        upgradeRequired: true,
        plan: 'free',
      },
      { status: 402 },
    );
  }

  kaizenObserve('billing', 'dispatch_allowed', 'Pro agent dispatch', {
    decision: `email=${billingEmail}`,
  });

  const base = backendBaseUrl();
  if (!base) {
    return NextResponse.json(
      { error: 'Agent backend not configured. Deploy the FastAPI backend and set BACKEND_URL.' },
      { status: 503 },
    );
  }

  try {
    const res = await fetch(`${base}/api/v1/agents/dispatch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: body.job_id,
        events: body.events ?? [],
        transcript: body.transcript,
        agent_types: body.agent_types,
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!res.ok) {
      const detail = await res.text();
      throw new Error(`Backend dispatch failed: ${res.status} ${detail}`);
    }

    return NextResponse.json(await res.json());
  } catch (error) {
    console.error('Agent dispatch error:', error);
    return NextResponse.json(
      { error: 'Failed to dispatch agents', details: String(error) },
      { status: 502 },
    );
  }
}

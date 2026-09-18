import { randomUUID } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';
import { decideOriginGate } from '@/lib/origin-gate-store';
import { assertPublicHttpUrl } from '@/lib/ssrf-guard';
import { StudioError } from '@/lib/studio/errors';
import { readStudioJson, requireStudioMutationOrigin, requireStudioOwner } from '@/lib/studio/security';

export const runtime = 'nodejs';
export const maxDuration = 60;

export async function POST(request: NextRequest): Promise<NextResponse> {
  const headers = { 'Cache-Control': 'no-store' };
  try {
    requireStudioMutationOrigin(request);
    const owner = await requireStudioOwner(request);
    const body = await readStudioJson(request);
    const url = body && typeof body === 'object' && 'url' in body && typeof body.url === 'string' ? body.url.trim() : '';
    if (!url || !/^https?:\/\//i.test(url)) return NextResponse.json({ error: 'url (http/https string) is required' }, { status: 400, headers });
    try {
      await assertPublicHttpUrl(url);
    } catch {
      return NextResponse.json({ error: 'url host is not allowed' }, { status: 400, headers });
    }
    // The legacy video-to-job workflow cannot execute the exact approved artifact.
    // A PASS from the acceptance endpoint must never authorize regenerating different bytes.
    const gate = await decideOriginGate({
      transitionId: `attempt:${randomUUID()}`,
      kind: 'studio.deploy',
      fromState: 'proposed',
      toState: 'live',
    }, owner.subject);
    return NextResponse.json({ ok: false, gate, message: gate.reason }, { status: 409, headers });
  } catch (error) {
    if (error instanceof StudioError) return NextResponse.json({ ok: false, error: error.message, code: error.code }, { status: error.status, headers });
    return NextResponse.json({ ok: false, error: 'G.A.T.E. preflight is unavailable. No deployment was started.' }, { status: 503, headers });
  }
}

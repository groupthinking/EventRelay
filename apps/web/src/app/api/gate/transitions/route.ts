import { NextRequest, NextResponse } from 'next/server';
import { decideOriginGate } from '@/lib/origin-gate-store';
import { StudioError } from '@/lib/studio/errors';
import { readStudioJson, requireStudioMutationOrigin, requireStudioOwner } from '@/lib/studio/security';

export const runtime = 'nodejs';

export async function POST(request: NextRequest): Promise<NextResponse> {
  const headers = { 'Cache-Control': 'no-store' };
  try {
    requireStudioMutationOrigin(request);
    const owner = await requireStudioOwner(request);
    const input = await readStudioJson(request);
    const gate = await decideOriginGate(input, owner.subject);
    return NextResponse.json({ ok: gate.decision === 'PASS', gate }, { status: gate.decision === 'PASS' ? 200 : 409, headers });
  } catch (error) {
    if (error instanceof StudioError) return NextResponse.json({ ok: false, error: error.message, code: error.code }, { status: error.status, headers });
    return NextResponse.json({ ok: false, error: 'G.A.T.E. is unavailable. No transition is permitted.' }, { status: 503, headers });
  }
}

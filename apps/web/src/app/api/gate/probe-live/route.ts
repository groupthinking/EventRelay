import { NextRequest, NextResponse } from 'next/server';
import { probeLiveDeploymentUrl } from '@/lib/live-deployment-probe';
import { evaluateStudioDeployTransition, studioGateReceiptView } from '@/lib/gate-transition';
import { readStudioJson, requireStudioMutationOrigin } from '@/lib/studio/security';

export const runtime = 'nodejs';

type ProbeLiveBody = {
  transitionId?: string;
  liveUrl?: string;
  runId?: string;
  runStatus?: string;
  kind?: string;
};

export async function POST(request: NextRequest): Promise<NextResponse> {
  const headers = { 'Cache-Control': 'no-store' };
  try {
    requireStudioMutationOrigin(request);
    const body = (await readStudioJson(request)) as ProbeLiveBody;
    const liveUrl = body.liveUrl?.trim() ?? '';
    if (!liveUrl) {
      return NextResponse.json(
        { ok: false, error: 'liveUrl is required' },
        { status: 400, headers },
      );
    }
    const probe = await probeLiveDeploymentUrl(liveUrl);
    const transitionId =
      body.transitionId?.trim() ||
      body.runId?.trim() ||
      `probe:${liveUrl.slice(0, 32)}`;
    const gate = evaluateStudioDeployTransition({
      transitionId,
      runId: body.runId,
      liveUrl,
      runStatus: body.runStatus,
      kind: body.kind,
      deploymentHttpProbe: probe,
      authority: { actor: 'signed-in' },
    });
    return NextResponse.json(
      {
        ok: probe.ok,
        probe,
        gate: studioGateReceiptView(gate),
      },
      { status: probe.ok ? 200 : 409, headers },
    );
  } catch {
    return NextResponse.json(
      { ok: false, error: 'Probe unavailable' },
      { status: 503, headers },
    );
  }
}

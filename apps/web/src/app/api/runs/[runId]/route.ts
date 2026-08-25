import { NextResponse } from 'next/server';
import { getRunOwner, latestApproval, latestSpec, loadRun } from '@/lib/db/delivery-repo';
import { resolveRunUserId } from '@/lib/run-identity';

export const runtime = 'nodejs';

/**
 * GET /api/runs/:runId — full run state: phase, every gate with its evidence,
 * the spec version under review, and the recorded approval.
 *
 * The gate list is the product's actual claim, so it is returned in full rather
 * than reduced to a status string. A blocked run reads as blocked, with the
 * gate that stopped it named.
 */
export async function GET(
  request: Request,
  context: { params: Promise<{ runId: string }> },
): Promise<NextResponse> {
  const userId = await resolveRunUserId(request);
  if (!userId) {
    return NextResponse.json({ error: 'Sign in required' }, { status: 401 });
  }

  const { runId } = await context.params;
  const owner = await getRunOwner(runId);
  // 404 rather than 403 for someone else's run: a wrong guess should not
  // confirm that the id exists.
  if (!owner || owner !== userId) {
    return NextResponse.json({ error: 'Run not found' }, { status: 404 });
  }

  const run = await loadRun(runId);
  if (!run) {
    return NextResponse.json({ error: 'Run not found' }, { status: 404 });
  }

  const [spec, approval] = await Promise.all([latestSpec(runId), latestApproval(runId)]);

  return NextResponse.json({
    run,
    spec: spec
      ? {
          id: spec.id,
          version: spec.version,
          requirements: spec.requirements,
          plan: spec.plan,
          createdAt: spec.createdAt.toISOString(),
        }
      : null,
    approval,
    awaitingApproval: run.phase === 'awaiting_approval',
  });
}

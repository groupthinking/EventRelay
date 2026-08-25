import { NextResponse } from 'next/server';
import { resumeHook } from 'workflow/api';
import { getRunOwner, latestSpec, loadRun } from '@/lib/db/delivery-repo';
import { resolveRunUserId } from '@/lib/run-identity';
import { withWorldVercelFetch } from '@/lib/world-vercel-fetch';
import { approvalToken } from '@/workflows/delivery-run';

export const runtime = 'nodejs';

/**
 * POST /api/runs/:runId/approve — the human gate.
 *
 * The workflow is suspended on `approvalHook`; resuming it with the decision is
 * the only way a run leaves `awaiting_approval`. Three things are checked
 * before the hook is touched:
 *
 *   1. the caller owns the run (approval is an authorization decision);
 *   2. the run is actually waiting (no re-approving a finished run);
 *   3. a spec version exists (an approval must reference what was read).
 *
 * The row itself is written inside the workflow's approval step, so the
 * decision and the phase transition succeed or fail together.
 */
export async function POST(
  request: Request,
  context: { params: Promise<{ runId: string }> },
): Promise<NextResponse> {
  const userId = await resolveRunUserId(request);
  if (!userId) {
    return NextResponse.json({ error: 'Sign in required' }, { status: 401 });
  }

  const { runId } = await context.params;
  const owner = await getRunOwner(runId);
  if (!owner || owner !== userId) {
    return NextResponse.json({ error: 'Run not found' }, { status: 404 });
  }

  let body: { approved?: unknown; note?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (typeof body.approved !== 'boolean') {
    return NextResponse.json(
      { error: 'approved (boolean) is required' },
      { status: 400 },
    );
  }
  const note = typeof body.note === 'string' ? body.note.trim().slice(0, 2_000) : undefined;

  const run = await loadRun(runId);
  if (!run) {
    return NextResponse.json({ error: 'Run not found' }, { status: 404 });
  }
  if (run.phase !== 'awaiting_approval') {
    return NextResponse.json(
      { error: `Run is ${run.phase}, not awaiting approval`, phase: run.phase },
      { status: 409 },
    );
  }

  const spec = await latestSpec(runId);
  if (!spec) {
    return NextResponse.json(
      { error: 'No spec version to approve' },
      { status: 409 },
    );
  }

  try {
    await withWorldVercelFetch(() =>
      resumeHook(approvalToken(runId), {
        approved: body.approved as boolean,
        decidedBy: userId,
        note,
      }),
    );
  } catch (error) {
    console.error('[api/runs/approve] resumeHook failed', error);
    return NextResponse.json(
      { error: 'Approval could not be delivered to the run', runId },
      { status: 502 },
    );
  }

  return NextResponse.json({
    ok: true,
    runId,
    specId: spec.id,
    specVersion: spec.version,
    decision: body.approved ? 'approved' : 'rejected',
    decidedBy: userId,
  });
}

import { NextResponse } from 'next/server';
import { getRun } from 'workflow/api';
import type { StudioDeployResult } from '@/workflows/studio-deploy';

export const runtime = 'nodejs';

export async function GET(
  _request: Request,
  context: { params: Promise<{ runId: string }> },
): Promise<NextResponse> {
  const { runId: raw } = await context.params;
  const runId = typeof raw === 'string' ? raw.trim() : '';
  if (!runId || runId.length > 200) {
    return NextResponse.json({ error: 'runId is required' }, { status: 400 });
  }

  try {
    const run = getRun<StudioDeployResult>(runId);
    const exists = await run.exists;
    if (!exists) {
      return NextResponse.json(
        { ok: false, runId, error: 'Workflow run not found' },
        { status: 404 },
      );
    }

    const [runStatus, workflowName, createdAt, startedAt, completedAt] =
      await Promise.all([
        run.status,
        run.workflowName.catch(() => undefined),
        run.createdAt.then((d) => d.toISOString()).catch(() => undefined),
        run.startedAt.then((d) => d?.toISOString()).catch(() => undefined),
        run.completedAt.then((d) => d?.toISOString()).catch(() => undefined),
      ]);

    const payload: Record<string, unknown> = {
      ok: true,
      runId,
      runStatus,
      workflowName,
      createdAt,
      startedAt,
      completedAt,
    };

    if (runStatus === 'completed' || runStatus === 'failed') {
      try {
        payload.result = await run.returnValue;
      } catch {
        payload.error = 'Failed to read workflow return value';
      }
    }

    return NextResponse.json(payload);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (/not found|does not exist/i.test(message)) {
      return NextResponse.json(
        { ok: false, runId, error: 'Workflow run not found' },
        { status: 404 },
      );
    }
    console.error('[api/workflows/studio-deploy/:runId]', err);
    return NextResponse.json(
      { ok: false, runId, error: 'Failed to read workflow run' },
      { status: 500 },
    );
  }
}

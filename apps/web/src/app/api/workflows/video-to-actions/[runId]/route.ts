import { NextResponse } from 'next/server';
import { getRun } from 'workflow/api';
import type { VideoToActionsResult } from '@/workflows/video-to-actions';

export const runtime = 'nodejs';

/**
 * GET /api/workflows/video-to-actions/:runId
 *
 * Poll durable Workflow DevKit run status + result (when completed).
 */
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
    const run = getRun<VideoToActionsResult>(runId);
    const exists = await run.exists;
    if (!exists) {
      return NextResponse.json(
        { ok: false, runId, error: 'Workflow run not found' },
        { status: 404 },
      );
    }

    const runStatus = await run.status;
    const payload: Record<string, unknown> = {
      ok: true,
      runId,
      runStatus,
      workflowName: await run.workflowName.catch(() => undefined),
      createdAt: await run.createdAt.then((d) => d.toISOString()).catch(() => undefined),
      startedAt: await run.startedAt
        .then((d) => d?.toISOString())
        .catch(() => undefined),
      completedAt: await run.completedAt
        .then((d) => d?.toISOString())
        .catch(() => undefined),
    };

    if (runStatus === 'completed') {
      try {
        payload.result = await run.returnValue;
      } catch (err) {
        payload.error =
          err instanceof Error ? err.message : 'Failed to read workflow return value';
      }
    } else if (runStatus === 'failed') {
      // Best-effort: some worlds attach the failure on returnValue rejection.
      try {
        payload.result = await Promise.race([
          run.returnValue,
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('timeout')), 500),
          ),
        ]);
      } catch (err) {
        payload.error =
          err instanceof Error && err.message !== 'timeout'
            ? err.message
            : 'Workflow run failed';
      }
    }

    return NextResponse.json(payload);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    // getRun may throw when the world cannot resolve the id.
    if (/not found|does not exist/i.test(message)) {
      return NextResponse.json(
        { ok: false, runId, error: 'Workflow run not found' },
        { status: 404 },
      );
    }
    console.error('[api/workflows/video-to-actions/:runId]', err);
    return NextResponse.json(
      {
        ok: false,
        runId,
        error: message,
        hint: 'Ensure the workflow package is installed and withWorkflow wraps next.config.',
      },
      { status: 500 },
    );
  }
}

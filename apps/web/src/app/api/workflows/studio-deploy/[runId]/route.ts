import { NextResponse } from 'next/server';
import { getRun } from 'workflow/api';
import {
  isTransientWorkflowRunReadError,
  workflowReturnErrorMessage,
} from '@/lib/studio-workflow';
import { withWorldVercelFetch } from '@/lib/world-vercel-fetch';
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
    const payload = await withWorldVercelFetch(async () => {
      const run = getRun<StudioDeployResult>(runId);
      const exists = await run.exists;
      if (!exists) {
        return {
          status: 404 as const,
          body: { ok: false, runId, error: 'Workflow run not found' },
        };
      }

      const [runStatus, workflowName, createdAt, startedAt, completedAt] =
        await Promise.all([
          run.status,
          run.workflowName.catch(() => undefined),
          run.createdAt.then((d) => d.toISOString()).catch(() => undefined),
          run.startedAt.then((d) => d?.toISOString()).catch(() => undefined),
          run.completedAt.then((d) => d?.toISOString()).catch(() => undefined),
        ]);

      const body: Record<string, unknown> = {
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
          body.result = await run.returnValue;
        } catch (err) {
          body.error = workflowReturnErrorMessage(err);
        }
      }

      return { status: 200 as const, body };
    });

    return NextResponse.json(payload.body, { status: payload.status });
  } catch (err) {
    const message = workflowReturnErrorMessage(err);
    if (/not found|does not exist/i.test(message)) {
      return NextResponse.json(
        { ok: false, runId, error: 'Workflow run not found' },
        { status: 404 },
      );
    }
    console.error('[api/workflows/studio-deploy/:runId]', err);
    if (isTransientWorkflowRunReadError(err)) {
      return NextResponse.json({
        ok: true,
        runId,
        runStatus: 'running',
      });
    }
    return NextResponse.json({ ok: false, runId, error: message }, { status: 500 });
  }
}

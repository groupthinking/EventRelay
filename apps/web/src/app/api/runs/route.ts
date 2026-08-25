import { NextResponse } from 'next/server';
import { start } from 'workflow/api';
import { extractYouTubeId } from '@/lib/timestamp';
import { createRun, blockRun, listRuns } from '@/lib/db/delivery-repo';
import { resolveRunUserId } from '@/lib/run-identity';
import { workflowStartErrorBody } from '@/lib/sentry-server-integrations';
import { withWorldVercelFetch } from '@/lib/world-vercel-fetch';
import { deliveryRunWorkflow } from '@/workflows/delivery-run';

export const runtime = 'nodejs';
/** `start()` returns as soon as the run is enqueued; the work is durable. */
export const maxDuration = 60;

const MAX_IDEA_CHARS = 8_000;

/**
 * POST /api/runs — open a delivery run and start the durable workflow.
 *
 * The row is created *before* the workflow starts so a failed `start()` leaves
 * a visible blocked run instead of nothing at all. Silent loss is the failure
 * mode this whole pipeline exists to eliminate, and it applies to its own
 * dispatch path too.
 */
export async function POST(request: Request): Promise<NextResponse> {
  const userId = await resolveRunUserId(request);
  if (!userId) {
    return NextResponse.json({ error: 'Sign in required' }, { status: 401 });
  }

  let body: { sourceUrl?: unknown; idea?: unknown; title?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const sourceUrl = typeof body.sourceUrl === 'string' ? body.sourceUrl.trim() : '';
  const idea = typeof body.idea === 'string' ? body.idea.trim().slice(0, MAX_IDEA_CHARS) : '';

  if (!sourceUrl && !idea) {
    return NextResponse.json(
      { error: 'Provide either sourceUrl (YouTube) or idea text' },
      { status: 400 },
    );
  }

  // Same restriction as the video workflow: only an extractable YouTube id is
  // accepted, which removes the user-controlled server-fetch target entirely
  // rather than relying on a hostname denylist.
  if (sourceUrl && !extractYouTubeId(sourceUrl)) {
    return NextResponse.json(
      { error: 'sourceUrl must be a valid YouTube watch, share, embed, shorts, or live URL' },
      { status: 400 },
    );
  }

  const title =
    (typeof body.title === 'string' && body.title.trim().slice(0, 200)) ||
    (sourceUrl ? `Delivery from ${sourceUrl}` : idea.slice(0, 80));

  let runId: string;
  try {
    runId = await createRun({
      userId,
      title,
      sourceKind: sourceUrl ? 'video' : 'idea',
      sourceUrl: sourceUrl || undefined,
    });
  } catch (error) {
    console.error('[api/runs] createRun failed', error);
    return NextResponse.json(
      { error: 'Run storage is unavailable — set NEON_DATABASE_URL to start runs' },
      { status: 503 },
    );
  }

  try {
    const run = await withWorldVercelFetch(() =>
      start(deliveryRunWorkflow, [
        { runId, userId, sourceUrl: sourceUrl || undefined, idea: idea || undefined },
      ]),
    );

    return NextResponse.json(
      {
        ok: true,
        runId,
        workflowRunId: run.runId,
        phase: 'sourcing',
        statusUrl: `/api/runs/${runId}`,
        streamUrl: `/api/runs/${runId}/stream`,
        approveUrl: `/api/runs/${runId}/approve`,
      },
      { status: 202 },
    );
  } catch (error) {
    console.error('[api/runs] workflow start failed', error);
    const reason = error instanceof Error ? error.message : String(error);
    // The run exists; make its state honest rather than leaving it stuck in
    // `sourcing` forever with no worker attached.
    await blockRun(runId, 'sourcing', `workflow dispatch failed: ${reason}`).catch(() => {});
    return NextResponse.json(
      { ok: false, runId, ...workflowStartErrorBody(error) },
      { status: 500 },
    );
  }
}

/** GET /api/runs — this user's runs, newest first. */
export async function GET(request: Request): Promise<NextResponse> {
  const userId = await resolveRunUserId(request);
  if (!userId) {
    return NextResponse.json({ error: 'Sign in required' }, { status: 401 });
  }

  const limitParam = Number(new URL(request.url).searchParams.get('limit'));
  const limit = Number.isFinite(limitParam) ? Math.min(Math.max(limitParam, 1), 100) : 50;

  const runs = await listRuns(userId, limit);
  return NextResponse.json({ runs });
}

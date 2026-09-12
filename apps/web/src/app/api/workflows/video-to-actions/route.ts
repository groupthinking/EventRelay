import { NextResponse } from 'next/server';
import { start } from 'workflow/api';
import { workflowStartErrorBody } from '@/lib/sentry-server-integrations';
import { sanitizeActEvents, usableProvidedTranscript } from '@/lib/video-to-actions-input';
import { withWorldVercelFetch } from '@/lib/world-vercel-fetch';
import { videoToActionsWorkflow } from '@/workflows/video-to-actions';
import { extractYouTubeId } from '@/lib/timestamp';

export const runtime = 'nodejs';
/** start() returns quickly; the durable run continues in the workflow world. */
export const maxDuration = 60;

/**
 * POST /api/workflows/video-to-actions
 *
 * Starts a durable Workflow DevKit run for video → actions.
 * Accepts an Analyze transcript/events so Act stays on the same run.
 * Returns immediately with { runId }; poll GET .../:runId or use `npx workflow web`.
 */
export async function POST(request: Request): Promise<NextResponse> {
  let body: {
    url?: unknown;
    videoTitle?: unknown;
    transcript?: unknown;
    events?: unknown;
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const url = typeof body.url === 'string' ? body.url.trim() : '';
  if (!url || !/^https?:\/\//i.test(url)) {
    return NextResponse.json(
      { error: 'url (http/https string) is required' },
      { status: 400 },
    );
  }

  // This workflow only supports YouTube sources. Restricting the route to an
  // extracted 11-character ID removes the user-controlled server-fetch target
  // entirely instead of relying on a hostname/DNS denylist.
  if (!extractYouTubeId(url)) {
    return NextResponse.json(
      { error: 'A valid YouTube watch, share, embed, shorts, or live URL is required.' },
      { status: 400 },
    );
  }

  const videoTitle =
    typeof body.videoTitle === 'string' ? body.videoTitle.slice(0, 200) : undefined;
  const transcript = usableProvidedTranscript(
    typeof body.transcript === 'string' ? body.transcript : undefined,
  );
  const events = sanitizeActEvents(body.events);

  try {
    const run = await withWorldVercelFetch(() =>
      start(videoToActionsWorkflow, [{ url, videoTitle, transcript, events }]),
    );
    return NextResponse.json({
      ok: true,
      runId: run.runId,
      generationId: run.runId,
      status: 'queued',
      statusUrl: `/api/workflows/video-to-actions/${encodeURIComponent(run.runId)}`,
      startedAt: new Date().toISOString(),
      message:
        'Durable video-to-actions workflow started. Poll statusUrl or run: npx workflow web',
    });
  } catch (err) {
    console.error('[api/workflows/video-to-actions]', err);
    return NextResponse.json({ ok: false, ...workflowStartErrorBody(err) }, { status: 500 });
  }
}

import { NextResponse } from 'next/server';
import { start } from 'workflow/api';
import { workflowStartErrorBody } from '@/lib/sentry-server-integrations';
import { videoToActionsWorkflow } from '@/workflows/video-to-actions';

export const runtime = 'nodejs';
/** start() returns quickly; the durable run continues in the workflow world. */
export const maxDuration = 60;

/**
 * POST /api/workflows/video-to-actions
 *
 * Starts a durable Workflow DevKit run for video → transcript → actions.
 * Returns immediately with { runId }; poll GET .../:runId or use `npx workflow web`.
 */
export async function POST(request: Request): Promise<NextResponse> {
  let body: { url?: unknown; videoTitle?: unknown };
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

  // Reject obviously private/local targets at the edge (SSRF defense-in-depth;
  // assertPublicHttpUrl still runs inside transcription when audioUrl is used).
  try {
    const host = new URL(url).hostname.toLowerCase();
    if (
      host === 'localhost' ||
      host === '127.0.0.1' ||
      host === '0.0.0.0' ||
      host === '::1' ||
      host.endsWith('.local') ||
      host.endsWith('.internal')
    ) {
      return NextResponse.json(
        { error: 'url host is not allowed' },
        { status: 400 },
      );
    }
  } catch {
    return NextResponse.json({ error: 'url is not a valid URL' }, { status: 400 });
  }

  const videoTitle =
    typeof body.videoTitle === 'string' ? body.videoTitle.slice(0, 200) : undefined;

  try {
    const run = await start(videoToActionsWorkflow, [{ url, videoTitle }]);
    return NextResponse.json({
      ok: true,
      runId: run.runId,
      statusUrl: `/api/workflows/video-to-actions/${encodeURIComponent(run.runId)}`,
      message:
        'Durable video-to-actions workflow started. Poll statusUrl or run: npx workflow web',
    });
  } catch (err) {
    console.error('[api/workflows/video-to-actions]', err);
    return NextResponse.json({ ok: false, ...workflowStartErrorBody(err) }, { status: 500 });
  }
}

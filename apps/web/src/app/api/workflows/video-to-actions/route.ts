import { NextResponse } from 'next/server';
import { start } from 'workflow/api';
import { videoToActionsWorkflow } from '@/workflows/video-to-actions';

/**
 * POST /api/workflows/video-to-actions
 *
 * Starts a durable Workflow DevKit run for video → transcript → actions.
 * Returns immediately with { runId }; inspect via `npx workflow web`.
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

  const videoTitle =
    typeof body.videoTitle === 'string' ? body.videoTitle : undefined;

  try {
    const run = await start(videoToActionsWorkflow, [{ url, videoTitle }]);
    return NextResponse.json({
      ok: true,
      runId: run.runId,
      message:
        'Durable video-to-actions workflow started. Inspect with: npx workflow web',
    });
  } catch (err) {
    console.error('[api/workflows/video-to-actions]', err);
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        ok: false,
        error: message,
        hint: 'Ensure next.config.js wraps with withWorkflow and `workflow` is installed.',
      },
      { status: 500 },
    );
  }
}

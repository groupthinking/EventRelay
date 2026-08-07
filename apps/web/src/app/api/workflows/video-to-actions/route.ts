import { NextResponse } from 'next/server';
import { start } from 'workflow/api';
import { assertPublicHttpUrl } from '@/lib/ssrf-guard';
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

  // Reject private/local targets at the edge (SSRF defense-in-depth;
  // assertPublicHttpUrl also runs inside transcription when audioUrl is used).
  //
  // Delegated to the shared guard rather than spelled out here. A hand-rolled
  // hostname list covers only the names it enumerates: it misses every RFC1918
  // literal (10/8, 172.16/12, 192.168/16), 169.254/16 — the cloud-metadata
  // address — and CGNAT, and an `=== '::1'` comparison never matches because
  // `URL.hostname` keeps the brackets (`http://[::1]/` yields `[::1]`), which is
  // the bug #1486 fixed in the guard itself. `assertPublicHttpUrl` handles all
  // of those plus the NAT64/6to4/IPv4-translated encodings.
  try {
    await assertPublicHttpUrl(url);
  } catch {
    // Deliberately bare: the guard's message distinguishes "does not resolve"
    // from "resolves to a private address", which is the CWE-209 DNS oracle
    // #1381 closed on /api/transcribe. The guard already logs the real cause.
    return NextResponse.json(
      { error: 'url host is not allowed' },
      { status: 400 },
    );
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

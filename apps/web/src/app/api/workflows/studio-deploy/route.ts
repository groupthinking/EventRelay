import { NextResponse } from 'next/server';
import { start } from 'workflow/api';
import { workflowStartErrorBody } from '@/lib/sentry-server-integrations';
import { withWorldVercelFetch } from '@/lib/world-vercel-fetch';
import { studioDeployWorkflow } from '@/workflows/studio-deploy';

export const runtime = 'nodejs';
export const maxDuration = 60;

/**
 * POST /api/workflows/studio-deploy
 *
 * Durable Studio deploy (WDK C): kickoff FastAPI async job + poll.
 * Returns immediately with { runId }.
 */
export async function POST(request: Request): Promise<NextResponse> {
  let body: { url?: unknown; projectType?: unknown; outcome?: unknown };
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
      return NextResponse.json({ error: 'url host is not allowed' }, { status: 400 });
    }
  } catch {
    return NextResponse.json({ error: 'url is not a valid URL' }, { status: 400 });
  }

  const projectType =
    typeof body.projectType === 'string' ? body.projectType.slice(0, 40) : undefined;
  const outcome =
    typeof body.outcome === 'string' ? body.outcome.slice(0, 80) : undefined;

  try {
    const run = await withWorldVercelFetch(() =>
      start(studioDeployWorkflow, [{ url, projectType, outcome }]),
    );
    return NextResponse.json({
      ok: true,
      runId: run.runId,
      statusUrl: `/api/workflows/studio-deploy/${encodeURIComponent(run.runId)}`,
      message: 'Durable Studio deploy started. Poll statusUrl.',
    });
  } catch (err) {
    console.error('[api/workflows/studio-deploy]', err);
    return NextResponse.json({ ok: false, ...workflowStartErrorBody(err) }, { status: 500 });
  }
}

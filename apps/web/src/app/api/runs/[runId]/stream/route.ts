import { getRunOwner, loadRun } from '@/lib/db/delivery-repo';
import { resolveRunUserId } from '@/lib/run-identity';
import { isTerminalPhase } from '@/lib/delivery-lifecycle';

export const runtime = 'nodejs';
/** Long-lived SSE connection; the client reconnects when it ends. */
export const maxDuration = 300;

const POLL_MS = 2_000;
const HEARTBEAT_MS = 15_000;

/**
 * GET /api/runs/:runId/stream — server-sent events for one run.
 *
 * The durable state lives in Postgres, so this streams by polling that state
 * rather than by holding workflow state in memory: a reconnect after a
 * serverless instance dies resumes with the same truth, and nothing is lost
 * because the connection dropped.
 *
 * Only changed snapshots are emitted, so an idle run costs one heartbeat.
 */
export async function GET(
  request: Request,
  context: { params: Promise<{ runId: string }> },
): Promise<Response> {
  const userId = await resolveRunUserId(request);
  if (!userId) {
    return new Response('Sign in required', { status: 401 });
  }

  const { runId } = await context.params;
  const owner = await getRunOwner(runId);
  if (!owner || owner !== userId) {
    return new Response('Run not found', { status: 404 });
  }

  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let closed = false;
      let lastSnapshot = '';
      let lastSendAt = 0;

      const send = (event: string, data: unknown) => {
        if (closed) return;
        controller.enqueue(
          encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`),
        );
        lastSendAt = Date.now();
      };

      const close = () => {
        if (closed) return;
        closed = true;
        clearInterval(timer);
        try {
          controller.close();
        } catch {
          // already closed by the client
        }
      };

      request.signal.addEventListener('abort', close);

      const tick = async () => {
        if (closed) return;
        try {
          const run = await loadRun(runId);
          if (!run) {
            send('error', { message: 'Run disappeared' });
            close();
            return;
          }

          const snapshot = JSON.stringify(run);
          if (snapshot !== lastSnapshot) {
            lastSnapshot = snapshot;
            send('run', run);
          } else if (Date.now() - lastSendAt >= HEARTBEAT_MS) {
            send('ping', { at: new Date().toISOString() });
          }

          // `blocked` ends the stream too: it is resumable, but only by an
          // operator, so there is nothing further to watch until they act.
          if (isTerminalPhase(run.phase) || run.phase === 'blocked') {
            send('done', {
              phase: run.phase,
              reason: run.blockedReason ?? run.error ?? null,
            });
            close();
          }
        } catch (error) {
          console.error('[api/runs/stream]', error);
          send('error', { message: 'Run state is temporarily unreadable' });
        }
      };

      const timer = setInterval(tick, POLL_MS);
      await tick();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}

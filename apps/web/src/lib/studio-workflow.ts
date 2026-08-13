/**
 * Studio helpers for the durable video → transcript → actions workflow (WDK Product v1).
 *
 * Complements `studio-deploy.ts` (FastAPI /api/pipeline job path). This path uses
 * Workflow DevKit: start returns a runId immediately; poll until terminal status.
 */

export interface VideoToActionsStart {
  ok: boolean;
  status: number;
  runId?: string;
  message?: string;
  error?: string;
}

export type WorkflowRunStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | string;

export interface VideoToActionsAction {
  tool: string;
  status: string;
  result?: string;
}

export interface VideoToActionsResult {
  url: string;
  transcriptChars: number;
  actionCount: number;
  provider?: string;
  actions: VideoToActionsAction[];
}

export interface VideoToActionsPoll {
  ok: boolean;
  status: number;
  runId: string;
  runStatus?: WorkflowRunStatus;
  result?: VideoToActionsResult;
  error?: string;
  message?: string;
}

function str(v: unknown): string | undefined {
  return typeof v === 'string' && v.trim() ? v : undefined;
}

/** Start durable video → actions. Returns immediately with runId. */
export async function startVideoToActions(input: {
  url: string;
  videoTitle?: string;
  signal?: AbortSignal;
}): Promise<VideoToActionsStart> {
  const response = await fetch('/api/workflows/video-to-actions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      url: input.url,
      videoTitle: input.videoTitle,
    }),
    signal: input.signal ?? AbortSignal.timeout(30_000),
  });

  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  const runId = str(payload.runId);
  const error = str(payload.error);
  const message = str(payload.message);

  return {
    ok: Boolean(payload.ok) && response.ok && Boolean(runId),
    status: response.status,
    runId,
    message,
    error,
  };
}

/** Single status poll for a workflow run. */
export async function getVideoToActionsStatus(
  runId: string,
  opts?: { signal?: AbortSignal },
): Promise<VideoToActionsPoll> {
  const response = await fetch(
    `/api/workflows/video-to-actions/${encodeURIComponent(runId)}`,
    {
      method: 'GET',
      signal: opts?.signal ?? AbortSignal.timeout(15_000),
    },
  );

  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  const runStatus = str(payload.runStatus) as WorkflowRunStatus | undefined;
  const error = str(payload.error);
  const message = str(payload.message);

  let result: VideoToActionsResult | undefined;
  if (payload.result && typeof payload.result === 'object') {
    const r = payload.result as Record<string, unknown>;
    const actionsRaw = Array.isArray(r.actions) ? r.actions : [];
    result = {
      url: str(r.url) || '',
      transcriptChars: typeof r.transcriptChars === 'number' ? r.transcriptChars : 0,
      actionCount: typeof r.actionCount === 'number' ? r.actionCount : actionsRaw.length,
      provider: str(r.provider),
      actions: actionsRaw
        .filter((a): a is Record<string, unknown> => Boolean(a) && typeof a === 'object')
        .map((a) => ({
          tool: str(a.tool) || 'unknown',
          status: str(a.status) || 'unknown',
          result: str(a.result),
        })),
    };
  }

  return {
    ok: response.ok && !error,
    status: response.status,
    runId: str(payload.runId) || runId,
    runStatus,
    result,
    error,
    message,
  };
}

const TERMINAL = new Set(['completed', 'failed', 'cancelled']);

/**
 * Poll until the run is terminal or attempts are exhausted.
 * Default: 30 attempts × 2s ≈ 60s of wall time (workflow continues server-side).
 *
 * The cadence is chosen against the middleware rate limit, not just for UI
 * responsiveness. Status reads are metered on the general budget
 * (`UVAI_API_RATE_LIMIT_PER_MINUTE`, default 60/min) — see `isAiRoute` in
 * `@/lib/auth-paths`, which exempts GET on `/api/workflows` from the much
 * tighter AI budget. At 2s a run spends 30 req/min, leaving roughly half the
 * general allowance for the rest of the page; the previous 1.5s cadence spent
 * 40/min and left little margin. The wall-clock window doubles to 60s as a
 * side effect, which better fits a transcript fetch plus an agent call.
 */
export async function pollVideoToActions(
  runId: string,
  opts?: { attempts?: number; delayMs?: number; signal?: AbortSignal },
): Promise<VideoToActionsPoll> {
  const attempts = opts?.attempts ?? 30;
  const delayMs = opts?.delayMs ?? 2000;
  let last: VideoToActionsPoll = {
    ok: false,
    status: 0,
    runId,
    message: 'No poll yet',
  };

  for (let i = 0; i < attempts; i++) {
    if (opts?.signal?.aborted) {
      return { ...last, error: last.error || 'aborted', message: 'Polling aborted' };
    }
    last = await getVideoToActionsStatus(runId, { signal: opts?.signal });
    if (last.runStatus && TERMINAL.has(last.runStatus)) {
      return last;
    }
    if (last.status === 404) {
      return last;
    }
    await new Promise((r) => setTimeout(r, delayMs));
  }

  return {
    ...last,
    message:
      last.message ||
      `Still ${last.runStatus || 'running'} after ${attempts} polls — re-check later with runId ${runId}`,
  };
}

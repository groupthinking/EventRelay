/**
 * Studio deploy handoff helpers (F5).
 * Kick off /api/pipeline with deployment_target=vercel and optionally poll job status.
 */

export interface StudioDeployKickoff {
  ok: boolean;
  status: number;
  jobId?: string;
  statusUrl?: string;
  pipeline?: string;
  live_url?: string | null;
  github_repo?: string | null;
  message?: string;
  /** True when backend only returned a configuration handoff (no live deploy). */
  handoff: boolean;
}

export interface StudioJobPoll {
  ok: boolean;
  status: number;
  jobStatus?: string;
  live_url?: string | null;
  github_repo?: string | null;
  message?: string;
  raw?: unknown;
}

function str(v: unknown): string | undefined {
  return typeof v === 'string' && v.trim() ? v : undefined;
}

export async function kickoffStudioDeploy(input: {
  url: string;
  projectType?: string;
  outcome?: string;
  prompt?: string;
  signal?: AbortSignal;
}): Promise<StudioDeployKickoff> {
  const response = await fetch('/api/pipeline', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      url: input.url,
      async: true,
      project_type: input.projectType || 'web',
      deployment_target: 'vercel',
      outcome: input.outcome,
      prompt: input.prompt,
    }),
    signal: input.signal ?? AbortSignal.timeout(30_000),
  });

  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  const nested =
    payload.result && typeof payload.result === 'object'
      ? (payload.result as Record<string, unknown>)
      : {};

  const jobId = str(payload.job_id) || str(nested.job_id);
  const statusUrl = str(payload.status_url) || str(nested.status_url);
  const pipeline = str(payload.pipeline);
  const live_url =
    (str(nested.live_url) as string | undefined) ??
    (str(payload.live_url) as string | undefined) ??
    null;
  const github_repo =
    (str(nested.github_repo) as string | undefined) ??
    (str(payload.github_repo) as string | undefined) ??
    null;
  const message =
    str(payload.error) ||
    str(payload.detail) ||
    str(nested.message) ||
    str(payload.message);

  const handoff =
    !response.ok ||
    pipeline === 'local-fallback' ||
    pipeline === 'transcript-only' ||
    (!jobId && !live_url);

  return {
    ok: response.ok,
    status: response.status,
    jobId,
    statusUrl,
    pipeline,
    live_url,
    github_repo,
    message,
    handoff,
  };
}

/** Poll GET /api/jobs/{jobId} a few times for terminal-ish status. */
export async function pollStudioJob(
  jobId: string,
  opts?: { attempts?: number; delayMs?: number; signal?: AbortSignal },
): Promise<StudioJobPoll> {
  const attempts = opts?.attempts ?? 6;
  const delayMs = opts?.delayMs ?? 1500;
  let last: StudioJobPoll = { ok: false, status: 0, message: 'No poll attempts' };

  for (let i = 0; i < attempts; i++) {
    if (opts?.signal?.aborted) {
      return { ok: false, status: 0, message: 'Polling aborted' };
    }
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, {
        cache: 'no-store',
        signal: opts?.signal ?? AbortSignal.timeout(15_000),
      });
      const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
      const data =
        body.data && typeof body.data === 'object'
          ? (body.data as Record<string, unknown>)
          : body;
      const jobStatus = str(data.status) || str(body.status);
      const live_url = str(data.live_url) ?? str(body.live_url) ?? null;
      const github_repo = str(data.github_repo) ?? str(body.github_repo) ?? null;
      last = {
        ok: res.ok,
        status: res.status,
        jobStatus,
        live_url,
        github_repo,
        message: str(body.error) || str(body.detail) || str(data.message),
        raw: body,
      };

      if (
        live_url ||
        jobStatus === 'completed' ||
        jobStatus === 'failed' ||
        jobStatus === 'error' ||
        jobStatus === 'succeeded'
      ) {
        return last;
      }
    } catch (err) {
      last = {
        ok: false,
        status: 0,
        message: err instanceof Error ? err.message : String(err),
      };
    }
    if (i < attempts - 1) {
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  return last;
}

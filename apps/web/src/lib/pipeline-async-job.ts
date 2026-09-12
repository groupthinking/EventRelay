import 'server-only';

import { backendHeaders } from '@/lib/pipeline-backend';
import { checkBackendHealth, getBackendConfig } from '@/lib/pipeline-backend-health';
import { usableProvidedTranscript } from '@/lib/video-to-actions-input';

export { usableProvidedTranscript as usableKickoffTranscript };

export interface AsyncJobKickoff {
  kind: 'job' | 'handoff' | 'failed' | 'live';
  jobId?: string;
  statusUrl?: string;
  message?: string;
  live_url?: string | null;
  github_repo?: string | null;
  httpStatus?: number;
}

export interface AsyncJobStatus {
  ok: boolean;
  httpStatus?: number;
  jobStatus?: string;
  live_url?: string | null;
  github_repo?: string | null;
  message?: string;
}

function str(v: unknown): string | undefined {
  if (typeof v !== 'string') return undefined;
  const trimmed = v.trim();
  return trimmed ? trimmed : undefined;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/** Pass through a backend-supplied live URL only — never invent one. */
function firstLiveUrl(...values: unknown[]): string | null {
  for (const value of values) {
    const found = str(value);
    if (found) return found;
  }
  return null;
}

const YOUTUBE_REFETCH_RE =
  /sign in to confirm you.?re not a bot|cookies-from-browser|--cookies for the authentication|\[youtube\].*not a bot/i;

export const STUDIO_READY_TRANSCRIPT_HOLD =
  'Ready transcript was not reused. Deploy must not re-fetch YouTube. No verified deploy receipt.';

/** Honest HOLD when a ready transcript exists — never the yt-dlp bot string. */
export function studioDeployYoutubeRefetchHold(message?: string): string {
  if (message && YOUTUBE_REFETCH_RE.test(message)) {
    return STUDIO_READY_TRANSCRIPT_HOLD;
  }
  return message || 'video-to-software returned no verified live URL';
}

/** Cloudflare/origin gateway timeout — kickoff must async-handoff, not HOLD HTTP 524. */
export function isGatewayTimeoutKickoff(status?: number, message?: string): boolean {
  if (status === 524 || status === 504 || status === 408) return true;
  if (!message) return false;
  return /http 524|error code:\s*524|cloudflare|timed out before a verified live url|aborted due to timeout/i.test(
    message,
  );
}

/** Ready-transcript miss: never the bot wall and never HTTP 524. */
export function studioDeployReadyTranscriptHold(message?: string): string {
  if (!message || YOUTUBE_REFETCH_RE.test(message) || isGatewayTimeoutKickoff(undefined, message)) {
    return STUDIO_READY_TRANSCRIPT_HOLD;
  }
  return message;
}

/**
 * Kick off FastAPI async video processing (same contract as POST /api/pipeline async).
 * Used from WDK steps — no self-HTTP to /api/pipeline.
 * When a usable transcript is already ready, do not start URL-only /videos/process
 * (that path re-hits YouTube / yt-dlp).
 */
export async function kickoffAsyncVideoJob(
  url: string,
  opts?: { transcript?: string },
): Promise<AsyncJobKickoff> {
  const health = await checkBackendHealth();
  if (!health.available) {
    return {
      kind: 'handoff',
      message: health.reason || 'BACKEND_URL is not configured or backend is unreachable',
    };
  }

  const transcript = usableProvidedTranscript(opts?.transcript);
  const { url: backendUrl } = getBackendConfig();
  const shipped = await tryVideoToSoftwareDeploy(backendUrl, url, transcript);
  if (shipped.kind === 'live' || shipped.kind === 'job') return shipped;
  if (transcript) {
    return {
      kind: 'failed',
      message: studioDeployReadyTranscriptHold(shipped.message),
    };
  }

  const response = await fetch(`${backendUrl}/api/v1/videos/process`, {
    method: 'POST',
    headers: backendHeaders(),
    body: JSON.stringify({
      video_url: url,
      language: 'en',
      ...(transcript ? { transcript } : {}),
      options: { pipeline: 'video-to-software' },
    }),
    signal: AbortSignal.timeout(15_000),
  });

  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  const data =
    payload.data && typeof payload.data === 'object'
      ? (payload.data as Record<string, unknown>)
      : {};
  const jobId = str(data.job_id) || str(payload.job_id);

  if (response.ok && jobId) {
    return {
      kind: 'job',
      jobId,
      statusUrl: `/api/jobs/${jobId}`,
    };
  }

  return {
    kind: 'failed',
    message:
      str(payload.error) ||
      str(payload.detail) ||
      (response.ok
        ? 'Backend kickoff returned no job id'
        : `Backend kickoff returned HTTP ${response.status}`),
  };
}

/** One status read of a backend async job. WDK poll step retries when still pending. */
export async function fetchAsyncVideoJob(jobId: string): Promise<AsyncJobStatus> {
  const { configured, url: backendUrl } = getBackendConfig();
  if (!configured) {
    return { ok: false, message: 'BACKEND_URL is not configured' };
  }

  const response = await fetch(
    `${backendUrl}/api/v1/jobs/${encodeURIComponent(jobId)}`,
    {
      cache: 'no-store',
      headers: backendHeaders(),
      signal: AbortSignal.timeout(15_000),
    },
  );
  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  const data =
    payload.data && typeof payload.data === 'object'
      ? (payload.data as Record<string, unknown>)
      : payload;

  const metadata = asRecord(data.metadata);
  const outputs = asRecord(metadata?.outputs);
  const nestedMeta = asRecord(metadata?.metadata);
  const deployment =
    asRecord(data.deployment) ||
    asRecord(outputs?.deployment) ||
    asRecord(metadata?.deployment);

  return {
    ok: response.ok,
    httpStatus: response.status,
    jobStatus: str(data.status) || str(payload.status),
    live_url: firstLiveUrl(
      data.live_url,
      payload.live_url,
      metadata?.live_url,
      outputs?.live_url,
      deployment?.live_url,
      deployment?.url,
      nestedMeta?.live_url,
    ),
    github_repo: str(data.github_repo) ?? str(payload.github_repo) ?? null,
    message:
      str(payload.error) ||
      str(payload.detail) ||
      str(data.error) ||
      str(data.message),
  };
}

export function isTerminalJobStatus(status: string | undefined): boolean {
  return (
    status === 'complete' ||
    status === 'completed' ||
    status === 'succeeded' ||
    status === 'failed' ||
    status === 'error' ||
    status === 'cancelled'
  );
}

/**
 * Real deploy attempt (FastAPI video-to-software). Pass through a backend
 * live URL only — never invent one. 401/403 and other non-live outcomes
 * return null so the caller can fall through to the process job.
 */
async function tryVideoToSoftwareDeploy(
  backendUrl: string,
  url: string,
  transcript?: string,
): Promise<AsyncJobKickoff> {
  try {
    const response = await fetch(`${backendUrl}/api/v1/video-to-software`, {
      method: 'POST',
      headers: backendHeaders(),
      body: JSON.stringify({
        video_url: url,
        project_type: 'web',
        deployment_target: 'vercel',
        ...(transcript ? { transcript } : {}),
      }),
      signal: AbortSignal.timeout(20_000),
    });
    const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    const data = asRecord(payload.data) || {};
    const handedOffJobId = str(data.job_id) || str(payload.job_id);
    if (response.status === 202 && handedOffJobId) {
      return {
        kind: 'job',
        jobId: handedOffJobId,
        statusUrl: `/api/jobs/${handedOffJobId}`,
      };
    }
    const miss =
      str(payload.error) ||
      str(payload.detail) ||
      (response.ok
        ? 'video-to-software returned no verified live URL'
        : `Backend kickoff returned HTTP ${response.status}`);
    if (!response.ok) {
      return { kind: 'failed', message: miss, httpStatus: response.status };
    }
    const result = asRecord(payload.result);
    const deployment = asRecord(payload.deployment) || asRecord(result?.deployment);
    const live_url = firstLiveUrl(
      payload.live_url,
      result?.live_url,
      deployment?.live_url,
      deployment?.url,
    );
    if (!live_url) {
      return { kind: 'failed', message: miss };
    }
    return {
      kind: 'live',
      live_url,
      github_repo: str(payload.github_repo) ?? str(result?.github_repo) ?? null,
      message: str(payload.message) || str(result?.message),
    };
  } catch (err) {
    console.error('[pipeline-async-job] video-to-software kickoff failed', err);
    return {
      kind: 'failed',
      message: isAbortTimeout(err)
        ? 'video-to-software timed out before a verified live URL'
        : err instanceof Error
          ? err.message
          : 'video-to-software kickoff failed',
    };
  }
}

function isAbortTimeout(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false;
  const rec = err as { name?: unknown; code?: unknown; message?: unknown };
  if (rec.name === 'TimeoutError') return true;
  if (rec.code === 23 || rec.code === 'TIMEOUT_ERR') return true;
  return typeof rec.message === 'string' && /aborted due to timeout/i.test(rec.message);
}

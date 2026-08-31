import 'server-only';

import { backendHeaders } from '@/lib/pipeline-backend';
import { checkBackendHealth, getBackendConfig } from '@/lib/pipeline-backend-health';

export interface AsyncJobKickoff {
  kind: 'job' | 'handoff' | 'failed';
  jobId?: string;
  statusUrl?: string;
  message?: string;
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

/**
 * Kick off FastAPI async video processing (same contract as POST /api/pipeline async).
 * Used from WDK steps — no self-HTTP to /api/pipeline.
 */
export async function kickoffAsyncVideoJob(url: string): Promise<AsyncJobKickoff> {
  const health = await checkBackendHealth();
  if (!health.available) {
    return {
      kind: 'handoff',
      message: health.reason || 'BACKEND_URL is not configured or backend is unreachable',
    };
  }

  const { url: backendUrl } = getBackendConfig();
  const response = await fetch(`${backendUrl}/api/v1/videos/process`, {
    method: 'POST',
    headers: backendHeaders(),
    body: JSON.stringify({ video_url: url, language: 'en' }),
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

  return {
    ok: response.ok,
    httpStatus: response.status,
    jobStatus: str(data.status) || str(payload.status),
    live_url: str(data.live_url) ?? str(payload.live_url) ?? null,
    github_repo: str(data.github_repo) ?? str(payload.github_repo) ?? null,
    message: str(payload.error) || str(payload.detail) || str(data.message),
  };
}

export function isTerminalJobStatus(status: string | undefined): boolean {
  return (
    status === 'completed' ||
    status === 'succeeded' ||
    status === 'failed' ||
    status === 'error' ||
    status === 'cancelled'
  );
}

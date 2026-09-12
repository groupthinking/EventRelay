import 'server-only';

import { backendHeaders } from '@/lib/pipeline-backend';
import { checkBackendHealth, getBackendConfig } from '@/lib/pipeline-backend-health';

export interface AsyncJobKickoff {
  kind: 'job' | 'handoff' | 'failed' | 'live';
  jobId?: string;
  statusUrl?: string;
  message?: string;
  live_url?: string | null;
  github_repo?: string | null;
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
  const shipped = await tryVideoToSoftwareDeploy(backendUrl, url);
  if (shipped) return shipped;

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
): Promise<AsyncJobKickoff | null> {
  try {
    const response = await fetch(`${backendUrl}/api/v1/video-to-software`, {
      method: 'POST',
      headers: backendHeaders(),
      body: JSON.stringify({
        video_url: url,
        project_type: 'web',
        deployment_target: 'vercel',
      }),
      signal: AbortSignal.timeout(50_000),
    });
    const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (!response.ok) return null;
    const result = asRecord(payload.result);
    const deployment = asRecord(payload.deployment) || asRecord(result?.deployment);
    const live_url = firstLiveUrl(
      payload.live_url,
      result?.live_url,
      deployment?.live_url,
      deployment?.url,
    );
    if (!live_url) return null;
    return {
      kind: 'live',
      live_url,
      github_repo: str(payload.github_repo) ?? str(result?.github_repo) ?? null,
      message: str(payload.message) || str(result?.message),
    };
  } catch (err) {
    console.error('[pipeline-async-job] video-to-software kickoff failed', err);
    return null;
  }
}

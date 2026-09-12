import 'server-only';

import { backendHeaders } from '@/lib/pipeline-backend';
import { checkBackendHealth, getBackendConfig } from '@/lib/pipeline-backend-health';
import { studioVerifiedLiveUrl } from '@/lib/studio-pipeline-status';
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
  /** Timeout / 408 — WDK should retry the step, not FatalError the run. */
  retryable?: boolean;
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

const PREFERRED_LIVE_HOST = /\.(vercel\.app|netlify\.app|fly\.dev)$/i;

function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return '';
  }
}

function collectLiveUrlCandidates(record: Record<string, unknown>): unknown[] {
  const deployment = asRecord(record.deployment);
  const outputs = asRecord(record.outputs);
  const result = asRecord(record.result);
  const metadata = asRecord(record.metadata);
  const data = asRecord(record.data);
  const urls =
    asRecord(deployment?.urls) ||
    asRecord(record.urls) ||
    asRecord(asRecord(outputs?.deployment)?.urls);
  const summary = asRecord(deployment?.summary) || asRecord(record.summary);
  const summaryUrls = asRecord(summary?.deployment_urls);
  const outDep = asRecord(outputs?.deployment);
  return [
    record.live_url,
    data?.live_url,
    result?.live_url,
    metadata?.live_url,
    deployment?.live_url,
    deployment?.url,
    outDep?.live_url,
    outDep?.url,
    urls?.vercel,
    urls?.netlify,
    urls?.fly,
    summary?.primary_url,
    ...(summaryUrls ? Object.values(summaryUrls) : []),
    ...(urls ? Object.values(urls) : []),
    record.url,
    data,
    result,
    metadata,
    deployment,
    outputs,
    outDep,
    urls,
    summary,
  ];
}

/**
 * Pass through a backend-supplied verified https hostname only — never invent one.
 * Prefer explicit live_url / vercel|netlify|fly hosts over a GitHub repo URL.
 */
export function extractBackendLiveUrl(...values: unknown[]): string | null {
  const preferred: string[] = [];
  const other: string[] = [];
  const queue: unknown[] = [...values];
  const seen = new Set<unknown>();
  while (queue.length) {
    const value = queue.shift();
    if (value == null || seen.has(value)) continue;
    if (typeof value === 'object') seen.add(value);
    const verified = studioVerifiedLiveUrl(typeof value === 'string' ? value : null);
    if (verified) {
      const host = hostnameOf(verified);
      if (PREFERRED_LIVE_HOST.test(host) || host.endsWith('.vercel.app')) {
        preferred.push(verified);
      } else if (host !== 'github.com' && host !== 'www.github.com') {
        other.push(verified);
      }
      continue;
    }
    const rec = asRecord(value);
    if (rec) queue.push(...collectLiveUrlCandidates(rec));
  }
  return preferred[0] ?? other[0] ?? null;
}

/** Pass through a backend-supplied live URL only — never invent one. */
function firstLiveUrl(...values: unknown[]): string | null {
  return extractBackendLiveUrl(...values);
}

const YOUTUBE_REFETCH_RE =
  /sign in to confirm you.?re not a bot|cookies-from-browser|--cookies for the authentication|\[youtube\].*not a bot/i;

export const STUDIO_READY_TRANSCRIPT_HOLD =
  'Ready transcript was not reused. Deploy must not re-fetch YouTube. No verified deploy receipt.';

/** Honest HOLD when origin reused the transcript but produced no live URL. */
export const STUDIO_ORIGIN_NO_LIVE_HOLD =
  'Studio transcript was reused. Origin video-to-software returned no verified live URL.';

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

/** Ready-transcript miss: YouTube re-fetch → reuse HOLD; timeout/524 → origin miss. */
export function studioDeployReadyTranscriptHold(message?: string): string {
  if (message && YOUTUBE_REFETCH_RE.test(message)) {
    return STUDIO_READY_TRANSCRIPT_HOLD;
  }
  if (!message || isGatewayTimeoutKickoff(undefined, message)) {
    return STUDIO_ORIGIN_NO_LIVE_HOLD;
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
  if (transcript && isGatewayTimeoutKickoff(shipped.httpStatus, shipped.message)) {
    const retried = await tryVideoToSoftwareDeploy(backendUrl, url, transcript);
    if (retried.kind === 'live' || retried.kind === 'job') return retried;
    return {
      kind: 'failed',
      retryable: true,
      message: studioDeployReadyTranscriptHold(retried.message),
    };
  }
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

  let response: Response;
  try {
    response = await fetch(
      `${backendUrl}/api/v1/jobs/${encodeURIComponent(jobId)}`,
      {
        cache: 'no-store',
        headers: backendHeaders(),
        signal: AbortSignal.timeout(15_000),
      },
    );
  } catch (err) {
    console.error('[pipeline-async-job] job status read failed', err);
    return {
      ok: false,
      httpStatus: isAbortTimeout(err) ? 408 : undefined,
      message: isAbortTimeout(err)
        ? 'Deploy job status read timed out; retrying'
        : err instanceof Error
          ? err.message
          : 'Deploy job status read failed',
    };
  }
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
    live_url: firstLiveUrl(data, payload, metadata, outputs, deployment, nestedMeta),
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

export type StudioDeployPollDecision =
  | {
      action: 'live';
      live_url: string;
      jobStatus?: string;
      github_repo?: string | null;
    }
  | {
      action: 'job';
      jobStatus?: string;
      live_url?: string | null;
      github_repo?: string | null;
      message?: string;
    }
  | { action: 'continue'; message?: string; jobStatus?: string }
  | { action: 'retry'; message: string }
  | { action: 'fail'; message: string };

/**
 * One WDK job-status read → continue, live, terminal job, or honest fail.
 * Timeout / 408 / gateway abort must continue — never a raw abort HOLD.
 */
export function decideStudioDeployPoll(
  status: AsyncJobStatus,
  opts: { jobId: string; transcript?: string },
): StudioDeployPollDecision {
  if (status.live_url) {
    return {
      action: 'live',
      live_url: status.live_url,
      jobStatus: status.jobStatus || 'completed',
      github_repo: status.github_repo,
    };
  }

  const statusTimeout =
    status.httpStatus === 408 ||
    isGatewayTimeoutKickoff(status.httpStatus, status.message);

  if (status.httpStatus === 404) {
    return {
      action: 'continue',
      jobStatus: status.jobStatus,
      message: `Deploy job ${opts.jobId} still pending`,
    };
  }

  if (!status.ok && !statusTimeout) {
    const raw =
      status.message || `Deploy job ${opts.jobId} status HTTP ${status.httpStatus ?? 'error'}`;
    const msg = usableProvidedTranscript(opts.transcript)
      ? studioDeployReadyTranscriptHold(raw)
      : raw;
    if (status.httpStatus && status.httpStatus >= 500) {
      return { action: 'retry', message: msg };
    }
    return { action: 'fail', message: msg };
  }

  if (status.jobStatus === 'failed' || status.jobStatus === 'error') {
    const raw = status.message || `Deploy job ${opts.jobId} ${status.jobStatus}`;
    return {
      action: 'fail',
      message: usableProvidedTranscript(opts.transcript)
        ? studioDeployReadyTranscriptHold(raw)
        : raw,
    };
  }

  if (isTerminalJobStatus(status.jobStatus)) {
    return {
      action: 'job',
      jobStatus: status.jobStatus,
      live_url: status.live_url,
      github_repo: status.github_repo,
      message:
        status.message ||
        (status.live_url ? undefined : 'Backend job finished with no verified live URL'),
    };
  }

  const pending = `Deploy job ${opts.jobId} still ${status.jobStatus || 'pending'}`;
  const raw = status.message;
  const remapped =
    raw && usableProvidedTranscript(opts.transcript)
      ? studioDeployYoutubeRefetchHold(raw)
      : raw;
  return {
    action: 'continue',
    jobStatus: status.jobStatus,
    message:
      !remapped || remapped === STUDIO_READY_TRANSCRIPT_HOLD ? pending : remapped,
  };
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
    const live_url = firstLiveUrl(payload, data, result, deployment);
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
      httpStatus: isAbortTimeout(err) ? 408 : undefined,
      retryable: isAbortTimeout(err) ? true : undefined,
      message: isAbortTimeout(err)
        ? 'video-to-software timed out before a verified live URL'
        : err instanceof Error
          ? err.message
          : 'video-to-software kickoff failed',
    };
  }
}

export function isAbortTimeout(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false;
  const rec = err as { name?: unknown; code?: unknown; message?: unknown };
  if (rec.name === 'TimeoutError') return true;
  if (rec.code === 23 || rec.code === 'TIMEOUT_ERR') return true;
  return typeof rec.message === 'string' && /aborted due to timeout/i.test(rec.message);
}

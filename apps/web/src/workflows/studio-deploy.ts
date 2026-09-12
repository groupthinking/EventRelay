/**
 * Durable Studio deploy (Workflow DevKit) — Product C.
 *
 * Kick off FastAPI async video→software and poll the job until a live URL,
 * terminal failure, or an honest handoff (no backend).
 *
 * Trigger: POST /api/workflows/studio-deploy  { url, projectType?, outcome? }
 * Status:  GET  /api/workflows/studio-deploy/:runId
 */

import { FatalError } from 'workflow';

export interface StudioDeployInput {
  url: string;
  projectType?: string;
  outcome?: string;
  transcript?: string;
}

export interface StudioDeployResult {
  url: string;
  kind: 'live' | 'job' | 'handoff';
  jobId?: string;
  jobStatus?: string;
  live_url?: string | null;
  github_repo?: string | null;
  message?: string;
}

interface StudioDeployKickoff {
  kind: 'job' | 'handoff' | 'failed' | 'live';
  jobId?: string;
  message?: string;
  live_url?: string | null;
  github_repo?: string | null;
  retryable?: boolean;
}

export async function studioDeployWorkflow(
  input: StudioDeployInput,
): Promise<StudioDeployResult> {
  'use workflow';

  const url = (input.url || '').trim();
  if (!url || !/^https?:\/\//i.test(url)) {
    throw new FatalError('url must be an http(s) URL');
  }

  let kicked = await kickoffStep(url, input.transcript);
  if (kicked.kind === 'failed' && kicked.retryable) {
    kicked = await kickoffStep(url, input.transcript);
  }
  if (kicked.kind === 'failed') {
    throw new FatalError(kicked.message || 'Backend refused the deploy kickoff');
  }
  if (kicked.kind === 'live' && kicked.live_url) {
    return {
      url,
      kind: 'live',
      live_url: kicked.live_url,
      github_repo: kicked.github_repo,
      message: kicked.message,
    };
  }
  if (kicked.kind !== 'job' || !kicked.jobId) {
    return {
      url,
      kind: 'handoff',
      message: kicked.message || 'No backend job id — export package for manual Vercel deploy',
    };
  }

  const polled = await pollJobStep(kicked.jobId, input.transcript);
  return { url, ...polled, jobId: kicked.jobId };
}

async function kickoffStep(
  url: string,
  transcript?: string,
): Promise<StudioDeployKickoff> {
  'use step';

  const {
    isAbortTimeout,
    kickoffAsyncVideoJob,
    studioDeployReadyTranscriptHold,
  } = await import('@/lib/pipeline-async-job');
  try {
    return await kickoffAsyncVideoJob(url, { transcript });
  } catch (err) {
    if (isAbortTimeout(err)) {
      return {
        kind: 'failed',
        retryable: true,
        message: studioDeployReadyTranscriptHold(),
      };
    }
    throw err;
  }
}

async function pollJobStep(
  jobId: string,
  transcript?: string,
): Promise<{
  kind: 'live' | 'job';
  jobStatus?: string;
  live_url?: string | null;
  github_repo?: string | null;
  message?: string;
}> {
  'use step';

  const {
    fetchAsyncVideoJob,
    isGatewayTimeoutKickoff,
    isTerminalJobStatus,
    studioDeployReadyTranscriptHold,
    usableKickoffTranscript,
  } = await import('@/lib/pipeline-async-job');

  const reads = 18;
  const gapMs = 10_000;
  let status = await fetchAsyncVideoJob(jobId);
  for (let i = 0; i < reads; i++) {
    if (status.live_url) {
      return {
        kind: 'live',
        jobStatus: status.jobStatus || 'completed',
        live_url: status.live_url,
        github_repo: status.github_repo,
      };
    }

    const statusTimeout =
      status.httpStatus === 408 ||
      isGatewayTimeoutKickoff(status.httpStatus, status.message);

    if (!status.ok && !statusTimeout) {
      const raw = status.message || `Deploy job ${jobId} status HTTP ${status.httpStatus ?? 'error'}`;
      const msg = usableKickoffTranscript(transcript)
        ? studioDeployReadyTranscriptHold(raw)
        : raw;
      if (status.httpStatus && status.httpStatus >= 500) {
        throw new Error(msg);
      }
      throw new FatalError(msg);
    }

    if (status.jobStatus === 'failed' || status.jobStatus === 'error') {
      const raw = status.message || `Deploy job ${jobId} ${status.jobStatus}`;
      throw new FatalError(
        usableKickoffTranscript(transcript)
          ? studioDeployReadyTranscriptHold(raw)
          : raw,
      );
    }

    if (isTerminalJobStatus(status.jobStatus)) {
      return {
        kind: 'job',
        jobStatus: status.jobStatus,
        live_url: status.live_url,
        github_repo: status.github_repo,
        message:
          status.message ||
          (status.live_url ? undefined : 'Backend job finished with no verified live URL'),
      };
    }

    if (i < reads - 1) {
      await new Promise<void>((resolve) => {
        setTimeout(resolve, gapMs);
      });
      status = await fetchAsyncVideoJob(jobId);
    }
  }

  throw new Error(
    usableKickoffTranscript(transcript)
      ? studioDeployReadyTranscriptHold(status.message)
      : status.message || `Deploy job ${jobId} still ${status.jobStatus || 'pending'}`,
  );
}

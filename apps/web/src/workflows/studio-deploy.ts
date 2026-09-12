/**
 * Durable Studio deploy (Workflow DevKit) — Product C.
 *
 * Kick off FastAPI async video→software and poll the job until a live URL,
 * terminal failure, or an honest handoff (no backend).
 *
 * Job waits use workflow `sleep('10s')` between short `'use step'` reads so
 * the poll cannot sit in one step until Vercel/WDK abort-timeout.
 *
 * Trigger: POST /api/workflows/studio-deploy  { url, projectType?, outcome? }
 * Status:  GET  /api/workflows/studio-deploy/:runId
 */

import { FatalError, sleep } from 'workflow';

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

/** Durable 10s gaps × 36 reads = 6 minutes after kickoff — not one 180s step. */
const JOB_POLL_READS = 36;

/** One durable retry after the initial kickoff — not 6 × 45s of silent running. */
const KICKOFF_RETRIES = 1;

export async function studioDeployWorkflow(
  input: StudioDeployInput,
): Promise<StudioDeployResult> {
  'use workflow';

  const url = (input.url || '').trim();
  if (!url || !/^https?:\/\//i.test(url)) {
    throw new FatalError('url must be an http(s) URL');
  }

  let kicked = await kickoffStep(url, input.transcript);
  for (let i = 0; i < KICKOFF_RETRIES && kicked.kind === 'failed' && kicked.retryable; i++) {
    await sleep('10s');
    kicked = await kickoffStep(url, input.transcript);
  }
  if (kicked.kind === 'failed') {
    return {
      url,
      kind: 'handoff',
      message: kicked.message || 'Backend refused the deploy kickoff',
    };
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

  const jobId = kicked.jobId;
  let lastMessage: string | undefined;
  let lastJobStatus: string | undefined;
  for (let i = 0; i < JOB_POLL_READS; i++) {
    const decided = await readJobStep(jobId, input.transcript);
    switch (decided.action) {
      case 'live':
        return {
          url,
          kind: 'live',
          jobId,
          jobStatus: decided.jobStatus,
          live_url: decided.live_url,
          github_repo: decided.github_repo,
        };
      case 'job':
        return {
          url,
          kind: 'job',
          jobId,
          jobStatus: decided.jobStatus,
          live_url: decided.live_url,
          github_repo: decided.github_repo,
          message: decided.message,
        };
      case 'retry':
        throw new Error(decided.message);
      case 'fail':
        throw new FatalError(decided.message);
      case 'continue':
        lastMessage = decided.message;
        lastJobStatus = decided.jobStatus;
        if (i < JOB_POLL_READS - 1) {
          await sleep('10s');
        }
        break;
      default: {
        const unexpected: never = decided;
        throw new FatalError(`Unknown studio.deploy poll decision: ${JSON.stringify(unexpected)}`);
      }
    }
  }

  throw new Error(
    lastMessage || `Deploy job ${jobId} still ${lastJobStatus || 'pending'}`,
  );
}

async function kickoffStep(
  url: string,
  transcript?: string,
): Promise<StudioDeployKickoff> {
  'use step';

  const {
    isAbortTimeout,
    kickoffAsyncVideoJob,
    STUDIO_ORIGIN_KICKOFF_NO_JOB_HOLD,
  } = await import('@/lib/pipeline-async-job');
  try {
    return await kickoffAsyncVideoJob(url, { transcript });
  } catch (err) {
    if (isAbortTimeout(err)) {
      return {
        kind: 'failed',
        retryable: true,
        message: transcript
          ? STUDIO_ORIGIN_KICKOFF_NO_JOB_HOLD
          : 'Deploy kickoff timed out before a verified live URL. Waiting for the origin job — not aborting the attempt.',
      };
    }
    throw err;
  }
}

async function readJobStep(jobId: string, transcript?: string) {
  'use step';

  const { decideStudioDeployPoll, fetchAsyncVideoJob } = await import(
    '@/lib/pipeline-async-job'
  );
  const status = await fetchAsyncVideoJob(jobId);
  return decideStudioDeployPoll(status, { jobId, transcript });
}

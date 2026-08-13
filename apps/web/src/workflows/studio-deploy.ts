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
}

export interface StudioDeployResult {
  url: string;
  kind: 'live' | 'job' | 'handoff' | 'failed';
  jobId?: string;
  jobStatus?: string;
  live_url?: string | null;
  github_repo?: string | null;
  message?: string;
}

export async function studioDeployWorkflow(
  input: StudioDeployInput,
): Promise<StudioDeployResult> {
  'use workflow';

  const url = (input.url || '').trim();
  if (!url || !/^https?:\/\//i.test(url)) {
    throw new FatalError('url must be an http(s) URL');
  }

  const kicked = await kickoffStep(url);
  if (kicked.kind !== 'job' || !kicked.jobId) {
    return {
      url,
      kind: 'handoff',
      message: kicked.message || 'No backend job id — export package for manual Vercel deploy',
    };
  }

  const polled = await pollJobStep(kicked.jobId);
  return { url, ...polled, jobId: kicked.jobId };
}

async function kickoffStep(url: string): Promise<{
  kind: 'job' | 'handoff';
  jobId?: string;
  message?: string;
}> {
  'use step';

  const { kickoffAsyncVideoJob } = await import('@/lib/pipeline-async-job');
  return kickoffAsyncVideoJob(url);
}

async function pollJobStep(jobId: string): Promise<{
  kind: 'live' | 'job' | 'failed';
  jobStatus?: string;
  live_url?: string | null;
  github_repo?: string | null;
  message?: string;
}> {
  'use step';

  const { fetchAsyncVideoJob, isTerminalJobStatus } = await import(
    '@/lib/pipeline-async-job'
  );
  const status = await fetchAsyncVideoJob(jobId);

  if (status.live_url) {
    return {
      kind: 'live',
      jobStatus: status.jobStatus || 'completed',
      live_url: status.live_url,
      github_repo: status.github_repo,
    };
  }

  if (status.jobStatus === 'failed' || status.jobStatus === 'error') {
    throw new FatalError(
      status.message || `Deploy job ${jobId} ${status.jobStatus}`,
    );
  }

  if (!isTerminalJobStatus(status.jobStatus)) {
    // Retryable: WDK re-runs this step until the job finishes or retries exhaust.
    throw new Error(
      status.message || `Deploy job ${jobId} still ${status.jobStatus || 'pending'}`,
    );
  }

  return {
    kind: 'job',
    jobStatus: status.jobStatus,
    live_url: status.live_url,
    github_repo: status.github_repo,
    message: status.message,
  };
}

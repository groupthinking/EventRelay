import 'server-only';

/**
 * Delegation layer between the durable delivery workflow and the FastAPI
 * pipeline that actually builds, publishes, and deploys projects.
 *
 * ## Why this delegates instead of implementing
 *
 * The build/publish/deploy capability already exists and is the production
 * path:
 *
 *   - `ai_code_generator.generate_fullstack_project` (build)
 *   - `deployment_manager.verify_and_fix_project`    (verify + auto-fix)
 *   - `deployment_manager._create_github_repository` (publish)
 *   - `deploy/vercel.VercelAdapter`                  (deploy, polls to READY)
 *
 * all orchestrated by `/api/v1/video-to-software`. Re-implementing any of it in
 * TypeScript would fork the pipeline and guarantee drift. This module is
 * deliberately thin: it resolves the backend through the shared
 * {@link resolveBuildTarget} capability, calls the existing endpoint, and
 * translates the response into the gate outcomes the workflow understands.
 *
 * ## Model fallback lives in one place
 *
 * Requirements and planning are *not* generated here with a second TypeScript
 * model client. They go through the same backend, whose `LLMRouter` already
 * falls back Gemini → Anthropic → OpenAI → Grok → Perplexity. A provider
 * outage degrades in exactly one place, and there is no second set of model
 * IDs and keys to keep in sync.
 *
 * ## Never invent success
 *
 * Every function returns a discriminated `{ ok: true, ... } | { ok: false,
 * reason }`. When the backend is unreachable, returns a non-2xx, or reports a
 * failed stage, these return `ok: false` with the backend's own reason, which
 * moves the run to `blocked`. Nothing here fabricates a URL or a pass.
 */

import {
  backendHeaders,
  parseBackendJson,
  resolveBuildTarget,
} from '@/lib/backend/capability';

/** Generous: a full generate + build + deploy can legitimately take minutes. */
const PIPELINE_TIMEOUT_MS = 15 * 60 * 1000;
const SHORT_TIMEOUT_MS = 2 * 60 * 1000;

export type AgentOutcome<T> = ({ ok: true } & T) | { ok: false; reason: string };

/** Shape returned by `/api/v1/video-to-software` (VideoToSoftwareResponse). */
interface PipelineResponse {
  live_url?: string | null;
  github_repo?: string | null;
  build_status?: string;
  status?: string;
  project_name?: string;
  code_generation?: {
    framework?: string;
    files_created?: string[];
    entry_point?: string;
  };
  deployment?: {
    status?: string;
    errors?: string[];
    urls?: Record<string, string>;
  };
  action_required?: Array<{
    platform?: string;
    action?: string;
    url?: string | null;
    error?: string | null;
  }>;
  video_analysis?: { extracted_info?: Record<string, unknown> };
}

/**
 * POST to the backend, returning a typed outcome rather than throwing.
 *
 * An unreachable or unconfigured backend is a *blocking* condition, not a
 * silent fallback to some weaker local path: a run that cannot reach the
 * builder has not built anything, and must say so.
 */
async function postToBackend<T>(
  path: string,
  body: unknown,
  timeoutMs: number,
): Promise<AgentOutcome<{ data: T }>> {
  const { capability, canDelegate, health } = await resolveBuildTarget();

  if (!canDelegate) {
    return {
      ok: false,
      reason:
        health.reason ||
        capability.reason ||
        'build backend is not configured or not answering',
    };
  }

  try {
    const response = await fetch(`${capability.url}${path}`, {
      method: 'POST',
      headers: backendHeaders(),
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(timeoutMs),
    });

    if (!response.ok) {
      const detail = await response.text().catch(() => '');
      return {
        ok: false,
        reason: `backend ${path} returned ${response.status}${
          detail ? `: ${detail.slice(0, 300)}` : ''
        }`,
      };
    }

    const data = await parseBackendJson<T>(response);
    if (data === null) {
      return { ok: false, reason: `backend ${path} returned a non-JSON body` };
    }
    return { ok: true, data };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    // AbortSignal.timeout surfaces as TimeoutError.
    return {
      ok: false,
      reason: message.includes('timed out') || message.includes('Timeout')
        ? `backend ${path} timed out after ${Math.round(timeoutMs / 1000)}s`
        : `backend ${path} failed: ${message}`,
    };
  }
}

/**
 * Derive requirements from the source material.
 *
 * Uses the backend blueprint endpoint so drafting runs through `LLMRouter`
 * with its provider fallback intact.
 */
export async function generateRequirements(
  content: string,
): Promise<AgentOutcome<{ requirements: string; model: string }>> {
  const result = await postToBackend<{
    requirements?: string;
    blueprint?: string;
    model?: string;
  }>('/api/v1/projects/blueprint', { content, mode: 'requirements' }, SHORT_TIMEOUT_MS);

  if (!result.ok) return result;

  const requirements = (result.data.requirements || result.data.blueprint || '').trim();
  if (requirements.length < 40) {
    return {
      ok: false,
      reason: 'backend returned no usable requirements for this source',
    };
  }
  return { ok: true, requirements, model: result.data.model || 'llm-router' };
}

/** Turn requirements into an executable plan, again via the backend router. */
export async function generatePlan(
  requirements: string,
): Promise<AgentOutcome<{ plan: string; stepCount: number; model: string }>> {
  const result = await postToBackend<{
    plan?: string;
    blueprint?: string;
    steps?: unknown[];
    model?: string;
  }>('/api/v1/projects/blueprint', { content: requirements, mode: 'plan' }, SHORT_TIMEOUT_MS);

  if (!result.ok) return result;

  const plan = (result.data.plan || result.data.blueprint || '').trim();
  if (plan.length < 40) {
    return { ok: false, reason: 'backend returned no usable plan for these requirements' };
  }

  const stepCount = Array.isArray(result.data.steps)
    ? result.data.steps.length
    : plan.split('\n').filter((line) => /^\s*(?:[-*]|\d+\.)\s+/.test(line)).length;

  return { ok: true, plan, stepCount, model: result.data.model || 'llm-router' };
}

/**
 * Run the full backend pipeline: generate the project, verify the build, push
 * to GitHub, and deploy.
 *
 * The backend performs build, publish, and deploy as one orchestrated unit, so
 * this returns everything the workflow's build/verify/deploy gates need. Each
 * gate still evaluates its own evidence from the result — combining the calls
 * does not combine the checks.
 */
export async function runPipeline(
  input: { sourceUrl?: string; plan: string; deploymentTarget?: string },
): Promise<AgentOutcome<{ pipeline: PipelineResponse }>> {
  const result = await postToBackend<PipelineResponse>(
    '/api/v1/video-to-software',
    {
      video_url: input.sourceUrl,
      project_type: 'web',
      deployment_target: input.deploymentTarget || 'vercel',
      features: ['responsive_design', 'modern_ui'],
      plan: input.plan,
    },
    PIPELINE_TIMEOUT_MS,
  );

  if (!result.ok) return result;
  return { ok: true, pipeline: result.data };
}

/**
 * Extract the repository URL, treating absence as failure.
 *
 * The backend now returns `github_repo: null` when the push did not succeed
 * (it previously substituted a placeholder repo that did not exist), so a
 * missing value here is a genuine failure signal rather than a formatting quirk.
 */
export function repoFromPipeline(
  pipeline: PipelineResponse,
): AgentOutcome<{ repoUrl: string; fileCount: number }> {
  const repoUrl = pipeline.github_repo?.trim();
  if (!repoUrl) {
    return {
      ok: false,
      reason:
        firstActionReason(pipeline, 'github') ||
        'backend produced no GitHub repository for this run',
    };
  }
  return {
    ok: true,
    repoUrl,
    fileCount: pipeline.code_generation?.files_created?.length ?? 0,
  };
}

/**
 * Extract the live deployment URL.
 *
 * `live_url` is only populated from a deployment the backend confirmed READY,
 * so an empty value means nothing is live — including the case where a manual
 * Vercel import link is available, which is surfaced as the block reason
 * instead of being mistaken for a deployment.
 */
export function deploymentFromPipeline(
  pipeline: PipelineResponse,
): AgentOutcome<{ deploymentUrl: string }> {
  const liveUrl = pipeline.live_url?.trim();
  if (!liveUrl || pipeline.build_status !== 'completed') {
    const errors = pipeline.deployment?.errors?.filter(Boolean) ?? [];
    return {
      ok: false,
      reason:
        firstActionReason(pipeline, 'vercel') ||
        (errors.length ? errors.join('; ') : 'backend reported no live deployment URL'),
    };
  }
  return { ok: true, deploymentUrl: liveUrl };
}

/** Human-readable reason from the backend's `action_required` entries. */
function firstActionReason(
  pipeline: PipelineResponse,
  platform: string,
): string | null {
  const entry = pipeline.action_required?.find(
    (item) => (item.platform || '').toLowerCase() === platform,
  );
  if (!entry) return null;
  const parts = [entry.error, entry.action && `action required: ${entry.action}`, entry.url]
    .filter(Boolean)
    .join(' — ');
  return parts || null;
}

/**
 * Confirm a deployment answers a live request.
 *
 * The backend already polls Vercel to READY, but READY describes Vercel's view
 * of the build, not whether the URL serves traffic to us. This is an
 * independent check by a different party, so it can catch what the first
 * cannot.
 */
export async function probeDeployment(
  url: string,
): Promise<{ ok: true; status: number } | { ok: false; status?: number; reason: string }> {
  try {
    const response = await fetch(url, {
      method: 'GET',
      redirect: 'follow',
      cache: 'no-store',
      signal: AbortSignal.timeout(30_000),
    });

    // Any non-5xx means something is genuinely serving. 401/403 are valid for
    // a deployment behind auth and must not be misread as a dead site.
    if (response.status >= 500) {
      return {
        ok: false,
        status: response.status,
        reason: `deployment returned ${response.status}`,
      };
    }
    return { ok: true, status: response.status };
  } catch (error) {
    return {
      ok: false,
      reason: error instanceof Error ? error.message : String(error),
    };
  }
}

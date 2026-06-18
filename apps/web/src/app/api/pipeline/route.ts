import { NextResponse } from 'next/server';
import { publishEvent, EventTypes } from '@/lib/cloudevents';
import { analyzeVideoWithGemini } from '@/lib/gemini-video-analyzer';
import { hasGeminiKey } from '@/lib/gemini-client';
import { backendHeaders } from '@/lib/pipeline-backend';
import { resolveVideoUrl } from '@/lib/video-url-request';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

export const runtime = 'nodejs';
/** Sync route — short budget; use /api/pipeline/stream or async=true for long runs. */
export const maxDuration = 60;

export const MAX_DURATION_MS = maxDuration * 1000;

/** Health probe budget for Cloud Run cold start + TLS. */
export const PIPELINE_HEALTH_TIMEOUT_MS = 5_000;
/** Backend video-to-software cap — clamped to remaining request budget. */
export const PIPELINE_BACKEND_TIMEOUT_MS = 50_000;
/** Gemini fallback cap — only runs if backend left enough wall-clock time. */
export const PIPELINE_GEMINI_TIMEOUT_MS = 15_000;

/** Tracks elapsed time so sequential fallback steps stay within maxDuration. */
export class PipelineDeadline {
  constructor(private readonly endsAt: number) {}

  static fromMaxDuration(): PipelineDeadline {
    return new PipelineDeadline(Date.now() + MAX_DURATION_MS);
  }

  remainingMs(): number {
    return Math.max(0, this.endsAt - Date.now());
  }

  budgetMs(requestedMs: number): number {
    return Math.min(requestedMs, this.remainingMs());
  }

  signalFor(requestedMs: number): AbortSignal {
    const ms = this.budgetMs(requestedMs);
    if (ms <= 0) {
      throw new Error('Pipeline deadline exceeded');
    }
    return timeoutSignal(ms);
  }

  async runWithBudget<T>(
    promise: Promise<T>,
    requestedMs: number,
    label: string,
  ): Promise<T> {
    const ms = this.budgetMs(requestedMs);
    if (ms <= 0) {
      throw new Error(`${label}: pipeline deadline exceeded`);
    }
    return withTimeout(promise, ms, label);
  }
}

function backendHost(): string | null {
  if (!BACKEND_AVAILABLE) return null;
  try {
    return new URL(BACKEND_URL).host;
  } catch {
    return null;
  }
}

function timeoutSignal(ms: number): AbortSignal {
  return AbortSignal.timeout(ms);
}

async function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  let timeout: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        timeout = setTimeout(() => reject(new Error(`${label} timed out`)), ms);
      }),
    ]);
  } finally {
    if (timeout) clearTimeout(timeout);
  }
}

async function checkBackendHealth(timeoutMs = PIPELINE_HEALTH_TIMEOUT_MS): Promise<{ configured: boolean; available: boolean; host: string | null; reason?: string }> {
  if (!BACKEND_AVAILABLE) {
    return { configured: false, available: false, host: null, reason: 'BACKEND_URL is not configured' };
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/health`, {
      cache: 'no-store',
      signal: timeoutSignal(timeoutMs),
    });
    return {
      configured: true,
      available: response.ok,
      host: backendHost(),
      reason: response.ok ? undefined : `Backend health returned ${response.status}`,
    };
  } catch (error) {
    return {
      configured: true,
      available: false,
      host: backendHost(),
      reason: error instanceof Error ? error.message : String(error),
    };
  }
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback;
}

function featureList(value: unknown): string[] {
  if (!Array.isArray(value)) return ['source_review', 'workflow_steps', 'vercel_handoff'];
  const features = value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
  return features.length ? features : ['source_review', 'workflow_steps', 'vercel_handoff'];
}

function buildLocalFallbackPipeline({
  url,
  projectType,
  deploymentTarget,
  features,
  backend,
}: {
  url: string;
  projectType: string;
  deploymentTarget: string;
  features: string[];
  backend: Awaited<ReturnType<typeof checkBackendHealth>>;
}) {
  const backendReason = backend.reason || 'Backend pipeline is not available';

  return {
    live_url: null,
    github_repo: null,
    build_status: 'handoff_ready_backend_unavailable',
    video_analysis: {
      title: 'Workflow handoff from video source',
      summary: `UVAI could not run the full backend pipeline for ${url}. A deterministic handoff was created so the user still leaves with review, build, and deploy steps.`,
      events: [
        {
          type: 'source',
          title: 'Video source captured',
          description: url,
          confidence: 0.75,
        },
        {
          type: 'configuration',
          title: 'Automatic pipeline blocked',
          description: backendReason,
          confidence: 1,
        },
      ],
      actions: [
        {
          title: 'Review the source and intended outcome',
          description: 'Confirm the user goal, expected deliverable, and any safety or consent constraints before generating implementation details.',
          category: 'review',
          estimatedMinutes: 5,
        },
        {
          title: 'Create the deployable first draft',
          description: `Prepare the requested ${projectType} package with source notes, acceptance checks, and a Vercel deployment checklist.`,
          category: 'build',
          estimatedMinutes: 20,
        },
        {
          title: 'Reconnect automatic execution',
          description: 'Fix BACKEND_URL and provider billing/quota, then rerun the same source through the full backend pipeline.',
          category: 'configuration',
          estimatedMinutes: 10,
        },
      ],
      topics: ['video workflow', projectType, deploymentTarget, 'fallback handoff'],
      architectureCode: `source -> review -> ${projectType} draft -> ${deploymentTarget} handoff -> verification`,
    },
    code_generation: {
      status: 'handoff_ready',
      project_type: projectType,
      files: [
        'README.md',
        'workflow/spec.md',
        'workflow/acceptance-checks.md',
        'vercel-deploy-checklist.md',
      ],
      features,
    },
    deployment: {
      target: deploymentTarget,
      status: 'blocked_by_configuration',
      blockers: [
        backendReason,
        'Gemini billing or API access must be valid for automatic video analysis.',
        'OpenAI quota must be available for transcript fallback and realtime voice.',
      ],
    },
    features_implemented: features,
    message: 'Created a local fallback handoff. Automatic code generation and deployment require a healthy backend pipeline and valid provider billing.',
  };
}

/**
 * POST /api/pipeline
 *
 * End-to-end pipeline: YouTube URL → Video Analysis → Code Generation → Deployment → Live URL
 *
 * This is the FULL pipeline that the user's notes describe (PK=999, PK=1021):
 *   Ingest → Translate → Transport → Execute
 *
 * Strategies:
 *   1. Backend pipeline (FastAPI /api/v1/video-to-software) — full pipeline with agents
 *   2. Gemini analysis + frontend deployment — when no backend is available
 */
export async function POST(request: Request) {
  let videoUrl: string | undefined;
  try {
    const body = await request.json() as Record<string, unknown>;
    const url = resolveVideoUrl(body);
    const project_type = stringValue(body.project_type, 'web');
    const deployment_target = stringValue(body.deployment_target, 'vercel');
    const features = featureList(body.features);
    videoUrl = url;

    if (!url) {
      return NextResponse.json(
        {
          error: 'Video URL is required',
          accepted_fields: ['url', 'youtubeUrl', 'videoUrl', 'video_url'],
        },
        { status: 400 },
      );
    }

    await publishEvent(EventTypes.VIDEO_RECEIVED, { url, pipeline: 'end-to-end' }, url);

    const deadline = PipelineDeadline.fromMaxDuration();
    const asyncMode = body.async === true || body.async === 'true';

    // ── Strategy 0: Async kickoff (returns job_id immediately) ──
    if (asyncMode && BACKEND_AVAILABLE) {
      try {
        const response = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
          method: 'POST',
          headers: backendHeaders(),
          body: JSON.stringify({
            video_url: url,
            language: stringValue(body.language, 'en'),
          }),
          signal: deadline.signalFor(10_000),
        });

        if (response.ok) {
          const result = await response.json();
          const jobId = typeof result.job_id === 'string' ? result.job_id : undefined;

          return NextResponse.json({
            id: jobId || `pipeline_${Date.now().toString(36)}`,
            status: result.async_processing ? 'pending' : (result.success ? 'complete' : 'failed'),
            pipeline: 'backend-async',
            async_processing: Boolean(result.async_processing),
            job_id: jobId,
            status_url: jobId ? `/api/jobs/${jobId}` : result.status_url,
            result: result.async_processing ? undefined : result,
          });
        }
        console.warn(`Async transcript-action returned ${response.status}, falling back`);
      } catch (e) {
        console.warn('Async pipeline kickoff failed:', e);
      }
    }

    // ── Strategy 1: Full backend pipeline (FastAPI video-to-software) ──
    if (BACKEND_AVAILABLE && deadline.remainingMs() > 1_000) {
      try {
        const response = await fetch(`${BACKEND_URL}/api/v1/video-to-software`, {
          method: 'POST',
          headers: backendHeaders(),
          body: JSON.stringify({
            video_url: url,
            project_type,
            deployment_target,
            features,
          }),
          signal: deadline.signalFor(PIPELINE_BACKEND_TIMEOUT_MS),
        });

        if (response.ok) {
          const result = await response.json();

          await publishEvent(EventTypes.PIPELINE_COMPLETED, {
            strategy: 'backend-pipeline',
            success: result.status === 'success',
            live_url: result.live_url,
            github_repo: result.github_repo,
            build_status: result.build_status,
          }, url);

          return NextResponse.json({
            id: `pipeline_${Date.now().toString(36)}`,
            status: result.status || 'complete',
            pipeline: 'backend',
            processing_time: result.processing_time,
            result: {
              live_url: result.live_url,
              github_repo: result.github_repo,
              build_status: result.build_status,
              video_analysis: result.video_analysis,
              code_generation: result.code_generation,
              deployment: result.deployment,
              features_implemented: result.features_implemented,
            },
          });
        }
        console.warn(`Backend pipeline returned ${response.status}, falling back`);
      } catch (e) {
        console.log('Backend pipeline unavailable:', e);
      }
    }

    // ── Strategy 2: Gemini analysis (video intelligence only, no deployment) ──
    if (hasGeminiKey() && deadline.remainingMs() > 1_000) {
      try {
        const startTime = Date.now();
        const analysis = await deadline.runWithBudget(
          analyzeVideoWithGemini(url),
          PIPELINE_GEMINI_TIMEOUT_MS,
          'Gemini analysis',
        );
        const elapsed = Date.now() - startTime;

        await publishEvent(EventTypes.PIPELINE_COMPLETED, {
          strategy: 'gemini-analysis-only',
          success: true,
          note: 'Backend unavailable — analysis only, no deployment',
        }, url);

        return NextResponse.json({
          id: `pipeline_${Date.now().toString(36)}`,
          status: 'partial',
          pipeline: 'gemini-only',
          processing_time: `${(elapsed / 1000).toFixed(1)}s`,
          result: {
            live_url: null,
            github_repo: null,
            build_status: 'not_attempted',
            video_analysis: {
              title: analysis.title,
              summary: analysis.summary,
              events: analysis.events,
              actions: analysis.actions,
              topics: analysis.topics,
              architectureCode: analysis.architectureCode,
            },
            code_generation: null,
            deployment: null,
            message: 'Backend pipeline unavailable. Video analysis complete but code generation and deployment require the Python backend.',
          },
        });
      } catch (e) {
        console.error('Gemini analysis failed:', e);
      }
    }

    const backend = await checkBackendHealth(deadline.budgetMs(PIPELINE_HEALTH_TIMEOUT_MS) || PIPELINE_HEALTH_TIMEOUT_MS);
    const fallback = buildLocalFallbackPipeline({
      url,
      projectType: project_type,
      deploymentTarget: deployment_target,
      features,
      backend,
    });

    await publishEvent(EventTypes.PIPELINE_COMPLETED, {
      strategy: 'local-fallback',
      success: false,
      backend,
    }, url);

    return NextResponse.json({
      id: `pipeline_${Date.now().toString(36)}`,
      status: 'partial',
      pipeline: 'local-fallback',
      degraded: true,
      backend,
      gemini_configured: hasGeminiKey(),
      warning: 'No automatic pipeline is currently available. Returned a fallback handoff instead of blocking the user.',
      result: fallback,
    });
  } catch (error) {
    console.error('Pipeline error:', error);
    await publishEvent(EventTypes.PIPELINE_FAILED, { error: String(error) }, videoUrl).catch(() => {});
    return NextResponse.json(
      { error: 'Pipeline failed', details: String(error) },
      { status: 500 },
    );
  }
}

export async function GET() {
  const backend = await checkBackendHealth();
  return NextResponse.json({
    name: 'EventRelay End-to-End Pipeline',
    version: '1.0.0',
    description: 'YouTube URL → Video Analysis → Code Generation → Deployment → Live URL',
    pipeline_stages: [
      '1. Ingest: Gemini analyzes video content with Google Search grounding',
      '2. Translate: Structured output → VideoPack artifact',
      '3. Transport: CloudEvents published at each stage',
      '4. Execute: Agents generate code, create repo, deploy to Vercel',
    ],
    backend_configured: backend.configured,
    backend_available: backend.available,
    backend_host: backend.host,
    backend_reason: backend.reason,
    gemini_available: hasGeminiKey(),
    endpoints: {
      pipeline: 'POST /api/pipeline - Full end-to-end pipeline',
      video: 'POST /api/video - Video analysis only',
    },
  });
}

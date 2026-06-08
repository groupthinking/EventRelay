import { NextResponse } from 'next/server';
import { publishEvent, EventTypes } from '@/lib/cloudevents';
import { analyzeVideoWithGemini } from '@/lib/gemini-video-analyzer';
import { hasGeminiKey } from '@/lib/gemini-client';
import { resolveVideoUrl } from '@/lib/video-url-request';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

export const runtime = 'nodejs';
export const maxDuration = 30;

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

async function checkBackendHealth(timeoutMs = 1500): Promise<{ configured: boolean; available: boolean; host: string | null; reason?: string }> {
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
    const { project_type = 'web', deployment_target = 'vercel', features } = body;
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

    // ── Strategy 1: Full backend pipeline (FastAPI video-to-software) ──
    if (BACKEND_AVAILABLE) {
      try {
        const response = await fetch(`${BACKEND_URL}/api/v1/video-to-software`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            video_url: url,
            project_type,
            deployment_target,
            features: features || ['responsive_design', 'modern_ui'],
          }),
          signal: timeoutSignal(8_000),
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
    if (hasGeminiKey()) {
      try {
        const startTime = Date.now();
        const analysis = await withTimeout(
          analyzeVideoWithGemini(url),
          8_000,
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

    return NextResponse.json(
      {
        error: 'No pipeline available. Configure a healthy BACKEND_URL for full pipeline or enable billing for the configured Gemini project.',
        backend: await checkBackendHealth(),
        gemini_configured: hasGeminiKey(),
      },
      { status: 503 },
    );
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

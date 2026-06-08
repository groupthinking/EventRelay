import { NextResponse } from 'next/server';
import { publishEvent, EventTypes } from '@/lib/cloudevents';
import { analyzeVideoWithGemini } from '@/lib/gemini-video-analyzer';
import { hasGeminiKey } from '@/lib/gemini-client';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

export const runtime = 'nodejs';
export const maxDuration = 300;

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
    const body = await request.json();
    const { url, project_type = 'web', deployment_target = 'vercel', features } = body;
    videoUrl = url;

    if (!url) {
      return NextResponse.json({ error: 'Video URL is required' }, { status: 400 });
    }

    await publishEvent(EventTypes.VIDEO_RECEIVED, { url, pipeline: 'end-to-end' }, url);

    // ── Strategy 1: Full backend pipeline (FastAPI video-to-software) ──
    if (BACKEND_AVAILABLE) {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 300_000); // 5 min for full pipeline

        let response: Response;
        try {
          response = await fetch(`${BACKEND_URL}/api/v1/video-to-software`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              video_url: url,
              project_type,
              deployment_target,
              features: features || ['responsive_design', 'modern_ui'],
            }),
            signal: controller.signal,
          });
        } finally {
          clearTimeout(timeout);
        }

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
        const analysis = await analyzeVideoWithGemini(url);
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
      { error: 'No pipeline available. Configure BACKEND_URL for full pipeline or GEMINI_API_KEY for analysis only.' },
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
    backend_available: BACKEND_AVAILABLE,
    gemini_available: hasGeminiKey(),
    endpoints: {
      pipeline: 'POST /api/pipeline - Full end-to-end pipeline',
      video: 'POST /api/video - Video analysis only',
    },
  });
}

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

/**
 * Get the absolute base URL for the current request.
 * Uses the request's origin or falls back to environment variables.
 */
function getBaseUrl(request: Request): string {
  const url = new URL(request.url);
  return `${url.protocol}//${url.host}`;
}

/**
 * POST /api/video
 *
 * Tries the full backend pipeline first (FastAPI transcript-action workflow).
 * If the backend is unreachable — common on Vercel where no Python server
 * runs — falls through to a frontend-only path that chains /api/transcribe
 * and /api/extract-events serverless functions directly.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { url } = body;

    if (!url) {
      return NextResponse.json({ error: 'Video URL is required' }, { status: 400 });
    }

    // ── Strategy 1: Full backend pipeline ──
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15_000);

      const response = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_url: url, language: 'en' }),
        signal: controller.signal,
      }).finally(() => clearTimeout(timeout));

      if (response.ok) {
        const result = await response.json();

        const transcriptAction = result.outputs?.transcript_action?.data || {};
        const personalityAgent = result.outputs?.personality_agent?.data || {};
        const strategyAgent = result.outputs?.strategy_agent?.data || {};

        let summaryText = 'Video analyzed successfully';
        const rawSummary = transcriptAction.summary;
        if (typeof rawSummary === 'string') {
          summaryText = rawSummary;
        } else if (rawSummary && typeof rawSummary === 'object') {
          summaryText =
            rawSummary.content ||
            rawSummary.executive_summary ||
            (typeof rawSummary.raw === 'string'
              ? (() => {
                  try {
                    const parsed = JSON.parse(rawSummary.raw.replace(/```json\n?|```/g, ''));
                    return parsed.executive_summary || parsed.summary || rawSummary.raw.slice(0, 200);
                  } catch {
                    return rawSummary.raw.slice(0, 200);
                  }
                })()
              : JSON.stringify(rawSummary).slice(0, 200));
        }

        const insights = {
          summary: summaryText,
          actions: transcriptAction.task_board?.tasks?.map((t: { title?: string }) => t.title) || [],
          topics: transcriptAction.metadata?.topics || [],
          sentiment: personalityAgent.personality_map?.video_intent?.primary || 'Neutral',
          strategy: strategyAgent.strategic_analysis || null,
          project_scaffold: transcriptAction.project_scaffold || null,
        };

        return NextResponse.json({
          id: `vid_${Date.now().toString(36)}`,
          status: result.success ? 'complete' : 'failed',
          processing_time_ms: Math.round((result.orchestration_meta?.processing_time || 0) * 1000),
          result: {
            success: result.success,
            insights,
            transcript_segments: (Array.isArray(result.transcript) ? result.transcript.length : result.transcript?.segments?.length) || 0,
            agents_used: result.orchestration_meta?.agents_used || [],
            errors: result.errors || [],
            raw_response: result,
          },
        });
      }
      console.warn(`Backend returned ${response.status}, falling back to frontend-only pipeline`);
    } catch {
      console.log('Backend unavailable — using frontend-only pipeline');
    }

    // ── Strategy 2: Frontend-only pipeline ──
    // Works on Vercel without the Python backend by chaining the serverless
    // /api/transcribe and /api/extract-events routes directly.

    let transcript = '';
    let transcriptSource = 'none';
    try {
      const baseUrl = getBaseUrl(request);
      const transcribeRes = await fetch(`${baseUrl}/api/transcribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const transcribeResult = await transcribeRes.json();
      if (transcribeResult.success && transcribeResult.transcript) {
        transcript = transcribeResult.transcript;
        transcriptSource = transcribeResult.source || 'frontend';
      }
    } catch (e) {
      console.error('Transcript extraction failed:', e);
    }

    // Step 2: Extract events + insights from transcript
    let extraction: { events?: Array<{ type: string; title: string; description?: string; timestamp?: string; priority?: string }>; actions?: Array<{ title: string }>; summary?: string; topics?: string[] } = {};
    if (transcript) {
      try {
        const baseUrl = getBaseUrl(request);
        const extractRes = await fetch(`${baseUrl}/api/extract-events`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transcript, videoUrl: url }),
        });
        const extractResult = await extractRes.json();
        if (extractResult.success && extractResult.data) {
          extraction = extractResult.data;
        }
      } catch (e) {
        console.error('Event extraction failed:', e);
      }
    }

    const hasResults = transcript.length > 0;

    return NextResponse.json({
      id: `vid_${Date.now().toString(36)}`,
      status: hasResults ? 'complete' : 'failed',
      processing_time_ms: 0,
      result: {
        success: hasResults,
        insights: {
          summary: extraction.summary || (hasResults ? 'Transcript extracted successfully' : 'Could not extract transcript — configure OPENAI_API_KEY or GEMINI_API_KEY'),
          actions: extraction.actions?.map((a) => a.title) || [],
          topics: extraction.topics || [],
          sentiment: 'Neutral',
        },
        transcript_segments: 0,
        transcript_source: transcriptSource,
        agents_used: ['frontend-pipeline'],
        errors: hasResults ? [] : ['Backend unavailable and transcript extraction failed'],
        raw_response: {
          transcript: { text: transcript },
          extraction,
        },
      },
    });
  } catch (error) {
    console.error('Video analysis error:', error);
    return NextResponse.json(
      { error: 'Failed to analyze video', details: String(error) },
      { status: 500 },
    );
  }
}

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/health`);
    const health = await response.json();

    return NextResponse.json({
      name: 'UVAI Video Analysis API',
      version: '2.0.0',
      backend_status: health.status,
      backend_components: health.components,
      endpoints: {
        analyze: 'POST /api/video - Analyze a video URL',
        health: 'GET /api/video - Check API status',
      },
    });
  } catch {
    return NextResponse.json({
      name: 'UVAI Video Analysis API',
      version: '2.0.0',
      backend_status: 'unavailable',
      frontend_pipeline: 'active',
      endpoints: {
        analyze: 'POST /api/video - Analyze a video URL',
      },
    });
  }
}

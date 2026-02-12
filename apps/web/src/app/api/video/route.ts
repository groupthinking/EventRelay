import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { url, options } = body;

    if (!url) {
      return NextResponse.json({ error: 'Video URL is required' }, { status: 400 });
    }

    // Call the EventRelay backend /api/v1/transcript-action endpoint
    const response = await fetch(`${BACKEND_URL}/api/v1/transcript-action`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        video_url: url,
        language: 'en'
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: `Backend error: ${error}` },
        { status: response.status }
      );
    }

    const result = await response.json();

    // Extract insights from the agent responses
    const transcriptAction = result.outputs?.transcript_action?.data || {};
    const personalityAgent = result.outputs?.personality_agent?.data || {};
    const strategyAgent = result.outputs?.strategy_agent?.data || {};

    // Extract summary string from various possible shapes
    let summaryText = 'Video analyzed successfully';
    const rawSummary = transcriptAction.summary;
    if (typeof rawSummary === 'string') {
      summaryText = rawSummary;
    } else if (rawSummary && typeof rawSummary === 'object') {
      // summary may be { content, raw, executive_summary, ... }
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

    // Build structured response
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
        transcript_segments: result.transcript?.length || 0,
        agents_used: result.orchestration_meta?.agents_used || [],
        errors: result.errors || [],
        raw_response: result
      }
    });
  } catch (error) {
    console.error('Video analysis error:', error);
    return NextResponse.json(
      { error: 'Failed to analyze video', details: String(error) },
      { status: 500 }
    );
  }
}

export async function GET() {
  // Health check - verify backend is available
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
      }
    });
  } catch (error) {
    return NextResponse.json({
      name: 'UVAI Video Analysis API',
      version: '2.0.0',
      backend_status: 'unavailable',
      error: String(error),
      endpoints: {
        analyze: 'POST /api/video - Analyze a video URL',
      }
    });
  }
}

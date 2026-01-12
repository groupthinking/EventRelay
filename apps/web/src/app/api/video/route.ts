import { NextResponse } from 'next/server';

const PRESCIENT_TWIN_URL = process.env.PRESCIENT_TWIN_URL || 'http://localhost:8000';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { url, options } = body;

    if (!url) {
      return NextResponse.json({ error: 'Video URL is required' }, { status: 400 });
    }

    // Call the Prescient Twin /evolve endpoint for video analysis
    const response = await fetch(`${PRESCIENT_TWIN_URL}/evolve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        task: `Analyze this video and extract: summary, key actions, topics, and any code examples: ${url}`,
        context: {
          video_url: url,
          extract_types: options?.extract || ['summary', 'actions', 'code'],
          deploy: options?.deploy || false
        }
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json({ error: `Prescient Twin error: ${error}` }, { status: response.status });
    }

    const result = await response.json();

    // Transform the response to match our API format
    return NextResponse.json({
      id: `vid_${Date.now().toString(36)}`,
      status: 'complete',
      processing_time_ms: result.execution_time_ms || 2300,
      result: {
        summary: result.result || 'Video analyzed successfully',
        brain_used: result.brain_used || 'gemini',
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
  return NextResponse.json({
    name: 'UVAI Video Analysis API',
    version: '1.0.0',
    endpoints: {
      analyze: 'POST /api/video - Analyze a video URL',
    }
  });
}

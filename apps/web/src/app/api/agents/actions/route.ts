import { NextResponse } from 'next/server';
import { runActionAgent } from '@/lib/action-agent';
import { AVAILABLE_TOOL_NAMES } from '@/lib/action-agent';

/**
 * GET /api/agents/actions
 *
 * Advertises the executable tools the action agent can invoke, so the UI can
 * render affordances without hardcoding the list.
 */
export async function GET() {
  const hasKey = !!(process.env.OPENAI_API_KEY || process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY);
  return NextResponse.json({ available: hasKey, tools: AVAILABLE_TOOL_NAMES });
}

/**
 * POST /api/agents/actions
 *
 * Runs the Transcription-Driven Action Agent over a transcript: the LLM decides
 * which tools to call, the tools execute, and the fulfilled actions are
 * returned. Keys stay server-side; no work is fabricated when a key is missing
 * (REAL_MODE_ONLY) — the route returns an honest error instead.
 */
export async function POST(request: Request) {
  try {
    const { transcript, videoTitle, jobId } = await request.json();

    if (!transcript || typeof transcript !== 'string') {
      return NextResponse.json(
        { success: false, error: 'transcript (string) is required', actions: [] },
        { status: 400 },
      );
    }

    const result = await runActionAgent({ transcript, videoTitle, jobId });

    return NextResponse.json({
      success: true,
      provider: result.provider,
      actions: result.actions,
    });
  } catch (error) {
    console.error('Action agent error:', error);
    const message = error instanceof Error ? error.message : String(error);
    const isConfig = message.includes('API key') || message.includes('too short');

    return NextResponse.json(
      { success: false, error: message, actions: [] },
      { status: isConfig ? 400 : 500 },
    );
  }
}

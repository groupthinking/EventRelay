import { NextResponse } from 'next/server';
import { runActionAgent } from '@/lib/action-agent';
import { AVAILABLE_TOOL_NAMES } from '@/lib/action-agent';
import { hasGeminiKey } from '@/lib/gemini-client';

/**
 * GET /api/agents/actions
 *
 * Advertises the executable tools the action agent can invoke, so the UI can
 * render affordances without hardcoding the list.
 */
export async function GET(): Promise<NextResponse> {
  const hasKey = !!(process.env.OPENAI_API_KEY || hasGeminiKey());
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
export async function POST(request: Request): Promise<NextResponse> {
  // Malformed JSON is a client error (400), not a server failure.
  let body: { transcript?: unknown; videoTitle?: unknown; jobId?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { success: false, error: 'Invalid JSON request body', actions: [] },
      { status: 400 },
    );
  }

  const { transcript, videoTitle, jobId } = body;
  if (!transcript || typeof transcript !== 'string') {
    return NextResponse.json(
      { success: false, error: 'transcript (string) is required', actions: [] },
      { status: 400 },
    );
  }

  try {
    const result = await runActionAgent({
      transcript,
      videoTitle: typeof videoTitle === 'string' ? videoTitle : undefined,
      jobId: typeof jobId === 'string' ? jobId : undefined,
    });

    return NextResponse.json({
      success: true,
      provider: result.provider,
      actions: result.actions,
    });
  } catch (error) {
    console.error('Action agent error:', error);
    const message = error instanceof Error ? error.message : String(error);

    // Only the agent's own validation/config guards are client errors (400).
    // Match exact phrases so an upstream provider error that merely mentions
    // "API key" (e.g. OpenAI's 401 "Incorrect API key provided") is correctly
    // surfaced as an upstream failure (502), not mislabeled as a bad request.
    const isClientError =
      message.startsWith('No AI API key configured') ||
      message.includes('transcript is too short');

    return NextResponse.json(
      { success: false, error: message, actions: [] },
      { status: isClientError ? 400 : 502 },
    );
  }
}

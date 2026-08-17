import { NextResponse } from 'next/server';
import { executePreparedActions, runActionAgent } from '@/lib/action-agent';
import { AVAILABLE_TOOL_NAMES } from '@/lib/action-agent';
import { hasGeminiKey } from '@/lib/gemini-client';
import type { AgentAction } from '@/lib/action-lifecycle';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { isProSubscriber } from '@/lib/billing/entitlement-store';

const MAX_CONFIRMED_ACTIONS = 50;
const PRO_ACTION_TOOLS = new Set([
  'dispatch_agent',
  'dispatch_subagents',
  'add_to_knowledge_base',
]);

function isPreparedAction(value: unknown): value is AgentAction {
  if (!value || typeof value !== 'object') return false;
  const action = value as Record<string, unknown>;
  return (
    typeof action.tool === 'string' &&
    !!action.tool &&
    typeof action.input === 'object' &&
    action.input !== null &&
    !Array.isArray(action.input)
  );
}

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
 * The safe default is `mode: "preview"`: the LLM prepares tool calls but no
 * tool runs. `mode: "execute"` requires the exact reviewed action list and is
 * the only path that performs side effects.
 */
export async function POST(request: Request): Promise<NextResponse> {
  // Malformed JSON is a client error (400), not a server failure.
  let body: {
    mode?: unknown;
    transcript?: unknown;
    videoTitle?: unknown;
    jobId?: unknown;
    actions?: unknown;
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { success: false, error: 'Invalid JSON request body', actions: [] },
      { status: 400 },
    );
  }

  const { mode, transcript, videoTitle, jobId, actions } = body;
  if (mode === 'execute') {
    if (
      !Array.isArray(actions) ||
      actions.length === 0 ||
      actions.length > MAX_CONFIRMED_ACTIONS ||
      !actions.every(isPreparedAction)
    ) {
      return NextResponse.json(
        {
          success: false,
          error: `actions must contain 1-${MAX_CONFIRMED_ACTIONS} valid reviewed tool calls`,
          actions: [],
        },
        { status: 400 },
      );
    }

    if (actions.some((action) => PRO_ACTION_TOOLS.has(action.tool))) {
      const billingEmail = await resolveTrustedBillingEmail(request);
      if (!(await isProSubscriber(billingEmail))) {
        return NextResponse.json(
          {
            success: false,
            error: 'External agent and knowledge-store actions require Pro.',
            upgradeRequired: true,
            actions: [],
          },
          { status: 402 },
        );
      }
    }

    try {
      const fulfilled = await executePreparedActions({
        actions,
        jobId: typeof jobId === 'string' ? jobId : undefined,
      });
      return NextResponse.json({ success: true, provider: 'confirmed-plan', actions: fulfilled });
    } catch (error) {
      console.error('Confirmed action execution error:', error);
      return NextResponse.json(
        { success: false, error: 'Internal server error', actions: [] },
        { status: 502 },
      );
    }
  }

  if (mode !== undefined && mode !== 'preview') {
    return NextResponse.json(
      { success: false, error: 'mode must be "preview" or "execute"', actions: [] },
      { status: 400 },
    );
  }

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
      executeTools: false,
    });

    return NextResponse.json({
      success: true,
      provider: result.provider,
      actions: result.actions,
    });
  } catch (error) {
    console.error('Action agent error:', error);
    const rawMessage = error instanceof Error ? error.message : String(error);

    // Only the agent's own validation/config guards are client errors (400).
    // Match exact phrases so an upstream provider error that merely mentions
    // "API key" (e.g. OpenAI's 401 "Incorrect API key provided") is correctly
    // surfaced as an upstream failure (502), not mislabeled as a bad request.
    const isClientError =
      rawMessage.startsWith('No AI API key configured') ||
      rawMessage.includes('transcript is too short');

    // SECURITY: Prevent leaking internal stack traces or error text on 5xx failures.
    const safeError = isClientError ? rawMessage : 'Internal server error';

    return NextResponse.json(
      { success: false, error: safeError, actions: [] },
      { status: isClientError ? 400 : 502 },
    );
  }
}

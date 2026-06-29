import 'server-only';

/**
 * Transcription-Driven Action Agent — server-side orchestrator.
 *
 * Takes a finished transcript, asks the LLM which executable tools to call
 * (see `action-tools.ts`), runs the resulting tool calls, and returns the
 * fulfilled actions. This is the `extracting → dispatching → fulfilled` core of
 * the lifecycle defined in `action-lifecycle.ts`.
 *
 * Provider routing mirrors the rest of the app: OpenAI (Responses API,
 * multi-round function calling) is primary; Gemini is a single-round fallback
 * used only when OpenAI is unavailable or quota-limited.
 */

import OpenAI from 'openai';
import { getGeminiClient, hasGeminiKey } from '@/lib/gemini-client';
import type { AgentAction } from '@/lib/action-lifecycle';
import {
  ACTION_TOOLS,
  getTool,
  resolveBackendBaseUrl,
  toGeminiFunctionDeclarations,
  toOpenAITools,
  type ActionToolResult,
  type ToolContext,
} from '@/lib/action-tools';

let _openai: OpenAI | null = null;
function getOpenAI(): OpenAI {
  if (!_openai) _openai = new OpenAI();
  return _openai;
}

const MODEL_OPENAI = 'gpt-4o-mini';
const MODEL_GEMINI = 'gemini-3.1-pro-preview';
const MAX_TOOL_ROUNDS = 4;
const MAX_TRANSCRIPT_CHARS = 8000;

const SYSTEM_PROMPT = `You are an action agent for a video-to-workflow platform.
Read the transcript and decide which executable tools to call so the viewer can
act on what was said. Call a tool for every concrete, practical item — do not
invent actions that are not grounded in the transcript. Prefer create_workflow_task
and save_resource for everyday items; reserve dispatch_agent for substantial work.
When there is nothing actionable, call no tools.`;

function buildUserPrompt(transcript: string, videoTitle?: string): string {
  return `Video: ${videoTitle || 'Unknown'}\n\nTRANSCRIPT:\n${transcript.slice(0, MAX_TRANSCRIPT_CHARS)}`;
}

export interface RunActionAgentOptions {
  transcript: string;
  videoTitle?: string;
  jobId?: string;
  /** Injectable fetch passed through to tools (testability). */
  fetchImpl?: typeof fetch;
}

export interface RunActionAgentResult {
  provider: string;
  actions: AgentAction[];
}

function toAction(tool: string, input: Record<string, unknown>, result: ActionToolResult): AgentAction {
  return {
    tool,
    input,
    status: result.isError ? 'failed' : 'fulfilled',
    result: result.summary,
    isError: result.isError,
  };
}

function isQuotaError(err: unknown): boolean {
  const msg = err instanceof Error ? err.message : String(err);
  return msg.includes('429') || msg.includes('quota') || msg.includes('rate');
}

/** Tool arguments must be a plain JSON object — not a primitive, array, or null. */
function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

/** Run the OpenAI Responses-API tool-calling loop until the model stops calling tools. */
async function runWithOpenAI(opts: RunActionAgentOptions, ctx: ToolContext): Promise<AgentAction[]> {
  const openai = getOpenAI();
  const actions: AgentAction[] = [];

  let response = await openai.responses.create({
    model: MODEL_OPENAI,
    instructions: SYSTEM_PROMPT,
    input: buildUserPrompt(opts.transcript, opts.videoTitle),
    tools: toOpenAITools(),
  });

  for (let round = 0; round < MAX_TOOL_ROUNDS; round++) {
    const calls = response.output.filter(
      (item): item is OpenAI.Responses.ResponseFunctionToolCall => item.type === 'function_call',
    );
    if (calls.length === 0) break;

    const toolOutputs: OpenAI.Responses.ResponseInputItem[] = [];
    for (const call of calls) {
      const tool = getTool(call.name);
      let input: Record<string, unknown> = {};
      let result: ActionToolResult;

      try {
        const parsed = call.arguments ? JSON.parse(call.arguments) : {};
        // JSON.parse can yield a primitive, array, or null — reject anything
        // that isn't an object so tools never run with a bogus argument shape.
        if (!isPlainObject(parsed)) {
          throw new Error('tool arguments were not a JSON object');
        }
        input = parsed;
      } catch (err) {
        result = {
          summary: `Invalid tool arguments for "${call.name}": ${err instanceof Error ? err.message : String(err)}`,
          isError: true,
        };
        actions.push(toAction(call.name, input, result));
        toolOutputs.push({
          type: 'function_call_output',
          call_id: call.call_id,
          output: JSON.stringify(result),
        });
        continue;
      }

      // A throwing tool becomes a failed action — it must not abort the run
      // or drop the remaining tool calls.
      try {
        result = tool
          ? await tool.execute(input, ctx)
          : { summary: `Unknown tool: ${call.name}`, isError: true };
      } catch (err) {
        result = {
          summary: `Tool "${call.name}" threw: ${err instanceof Error ? err.message : String(err)}`,
          isError: true,
        };
      }

      actions.push(toAction(call.name, input, result));
      toolOutputs.push({
        type: 'function_call_output',
        call_id: call.call_id,
        output: JSON.stringify(result),
      });
    }

    response = await openai.responses.create({
      model: MODEL_OPENAI,
      previous_response_id: response.id,
      input: toolOutputs,
      tools: toOpenAITools(),
    });
  }

  return actions;
}

/** Single-round Gemini fallback: extract function calls and execute them once. */
async function runWithGemini(opts: RunActionAgentOptions, ctx: ToolContext): Promise<AgentAction[]> {
  const ai = getGeminiClient();
  const response = await ai.models.generateContent({
    model: MODEL_GEMINI,
    contents: `${SYSTEM_PROMPT}\n\n${buildUserPrompt(opts.transcript, opts.videoTitle)}`,
    config: {
      temperature: 0.3,
      tools: [{ functionDeclarations: toGeminiFunctionDeclarations() }],
    },
  });

  const calls = response.functionCalls ?? [];
  const actions: AgentAction[] = [];
  for (const call of calls) {
    if (!call.name) continue;
    const tool = getTool(call.name);
    const rawArgs = call.args ?? {};
    if (!isPlainObject(rawArgs)) {
      actions.push(
        toAction(call.name, {}, { summary: `Invalid tool arguments for "${call.name}"`, isError: true }),
      );
      continue;
    }
    const input: Record<string, unknown> = rawArgs;
    let result: ActionToolResult;
    try {
      result = tool
        ? await tool.execute(input, ctx)
        : { summary: `Unknown tool: ${call.name}`, isError: true };
    } catch (err) {
      result = {
        summary: `Tool "${call.name}" threw: ${err instanceof Error ? err.message : String(err)}`,
        isError: true,
      };
    }
    actions.push(toAction(call.name, input, result));
  }
  return actions;
}

/**
 * Orchestrate the action agent over a transcript. Throws only if no provider is
 * available; individual tool failures are captured as `failed` actions.
 */
export async function runActionAgent(opts: RunActionAgentOptions): Promise<RunActionAgentResult> {
  if (!opts.transcript || opts.transcript.trim().length < 20) {
    throw new Error('transcript is too short to extract actions from');
  }

  const ctx: ToolContext = {
    backendBaseUrl: resolveBackendBaseUrl(),
    fetchImpl: opts.fetchImpl,
    jobId: opts.jobId,
  };

  if (process.env.OPENAI_API_KEY) {
    try {
      return { provider: 'openai', actions: await runWithOpenAI(opts, ctx) };
    } catch (err) {
      if (isQuotaError(err) && hasGeminiKey()) {
        console.warn('OpenAI quota hit, falling back to Gemini for action extraction');
        return { provider: 'gemini', actions: await runWithGemini(opts, ctx) };
      }
      throw err;
    }
  }

  if (hasGeminiKey()) {
    return { provider: 'gemini', actions: await runWithGemini(opts, ctx) };
  }

  throw new Error('No AI API key configured. Set OPENAI_API_KEY or GEMINI_API_KEY.');
}

/** The tool names this agent can invoke — handy for UI affordances/tests. */
export const AVAILABLE_TOOL_NAMES = ACTION_TOOLS.map((t) => t.name);

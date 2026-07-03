/**
 * Executable tool registry for the Transcription-Driven Action Agent.
 *
 * These are the functions the LLM may call based on context extrapolated from a
 * video transcript. Each tool carries a JSON-Schema parameter definition (so it
 * can be advertised to OpenAI's Responses API and converted to Gemini function
 * declarations) plus an `execute` handler that performs the real action.
 *
 * REAL_MODE_ONLY: handlers never fabricate success. Tools that only need local
 * structuring (tasks, resources, reminders) return concrete structured output;
 * tools that require the FastAPI backend (agent dispatch, knowledge base) call
 * it for real and report an honest failure when `BACKEND_URL` is not configured.
 */

import type { FunctionDeclaration } from '@google/genai';

// ── JSON Schema (shared by OpenAI strict tools + Gemini declarations) ──

export interface JSONSchema {
  type: 'object';
  properties: Record<string, unknown>;
  required: string[];
  additionalProperties: false;
  /** Index signature so the schema is assignable to the SDKs' parameter types. */
  [key: string]: unknown;
}

export interface ActionToolResult {
  /** Short human-readable summary of what happened. */
  summary: string;
  /** Structured payload produced by the tool (task object, resource, etc.). */
  data?: Record<string, unknown>;
  /** True when the tool could not complete (e.g. backend unavailable). */
  isError?: boolean;
}

/** Runtime context handed to every tool execution. */
export interface ToolContext {
  /** Resolved FastAPI base URL, or null when no backend is configured. */
  backendBaseUrl: string | null;
  /** Injectable fetch (defaults to global fetch) so tools are testable. */
  fetchImpl?: typeof fetch;
  /** Correlates dispatched work with the originating prompt. */
  jobId?: string;
}

export interface ActionTool {
  name: string;
  description: string;
  parameters: JSONSchema;
  execute: (input: Record<string, unknown>, ctx: ToolContext) => Promise<ActionToolResult>;
}

// ── Helpers ──

function str(input: Record<string, unknown>, key: string): string {
  const v = input[key];
  return typeof v === 'string' ? v : '';
}

/** Coerce a value to a string array, dropping non-string entries. */
function strArray(input: Record<string, unknown>, key: string): string[] {
  const v = input[key];
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [];
}

/**
 * Resolve the configured backend URL, or null when running frontend-only.
 * Validates the URL and enforces an http(s) scheme so a malformed value can't
 * produce a broken endpoint when concatenated; the trailing slash is trimmed so
 * callers can safely append `/api/...`.
 */
export function resolveBackendBaseUrl(): string | null {
  const raw = (process.env.BACKEND_URL || '').trim();
  if (!raw) return null;
  try {
    const url = new URL(raw);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
    return raw.replace(/\/+$/, '');
  } catch {
    return null;
  }
}

// ── Tool definitions ──

const createWorkflowTask: ActionTool = {
  name: 'create_workflow_task',
  description:
    'Create an actionable task from something the speaker said the viewer should DO. ' +
    'Call this for each concrete, practical step (setup, build, deploy, learn, research, configure).',
  parameters: {
    type: 'object',
    properties: {
      title: { type: 'string', description: 'Short imperative task title' },
      description: { type: 'string', description: 'One-sentence explanation of the task' },
      category: {
        type: 'string',
        enum: ['setup', 'build', 'deploy', 'learn', 'research', 'configure'],
      },
      priority: { type: 'string', enum: ['high', 'medium', 'low'] },
    },
    required: ['title', 'description', 'category', 'priority'],
    additionalProperties: false,
  },
  async execute(input) {
    const title = str(input, 'title');
    return {
      summary: `Created task "${title}"`,
      data: {
        title,
        description: str(input, 'description'),
        category: str(input, 'category'),
        priority: str(input, 'priority'),
        createdAt: new Date().toISOString(),
      },
    };
  },
};

const saveResource: ActionTool = {
  name: 'save_resource',
  description:
    'Bookmark a tool, library, link, or resource the speaker referenced so the viewer can revisit it.',
  parameters: {
    type: 'object',
    properties: {
      name: { type: 'string', description: 'Name of the tool/resource' },
      kind: { type: 'string', enum: ['tool', 'library', 'article', 'video', 'docs', 'other'] },
      reason: { type: 'string', description: 'Why it matters / how it was used' },
    },
    required: ['name', 'kind', 'reason'],
    additionalProperties: false,
  },
  async execute(input) {
    const name = str(input, 'name');
    return {
      summary: `Saved resource "${name}"`,
      data: {
        name,
        kind: str(input, 'kind'),
        reason: str(input, 'reason'),
        savedAt: new Date().toISOString(),
      },
    };
  },
};

const scheduleFollowup: ActionTool = {
  name: 'schedule_followup',
  description:
    'Schedule a reminder/follow-up for the viewer when the speaker suggests revisiting something later.',
  parameters: {
    type: 'object',
    properties: {
      topic: { type: 'string', description: 'What to follow up on' },
      relativeWhen: {
        type: 'string',
        description: 'When, relative to now, e.g. "tomorrow", "in 1 week"',
      },
    },
    required: ['topic', 'relativeWhen'],
    additionalProperties: false,
  },
  async execute(input) {
    const topic = str(input, 'topic');
    return {
      summary: `Scheduled follow-up on "${topic}" (${str(input, 'relativeWhen')})`,
      data: {
        topic,
        relativeWhen: str(input, 'relativeWhen'),
        scheduledAt: new Date().toISOString(),
      },
    };
  },
};

const dispatchAgent: ActionTool = {
  name: 'dispatch_agent',
  description:
    'Hand an extracted event to the MCP agent orchestrator to be acted on autonomously. ' +
    'Use only for substantial work that warrants a dedicated backend agent.',
  parameters: {
    type: 'object',
    properties: {
      agentType: {
        type: 'string',
        enum: ['code_generator', 'researcher', 'deployer', 'summarizer'],
      },
      instruction: { type: 'string', description: 'Concrete instruction for the agent' },
    },
    required: ['agentType', 'instruction'],
    additionalProperties: false,
  },
  async execute(input, ctx) {
    const agentType = str(input, 'agentType');
    const instruction = str(input, 'instruction');

    // REAL_MODE_ONLY: the MCP orchestrator only exists behind the FastAPI
    // backend. Report honestly rather than pretending the dispatch happened.
    if (!ctx.backendBaseUrl) {
      return {
        summary: `Cannot dispatch ${agentType} agent — no backend configured (set BACKEND_URL).`,
        isError: true,
      };
    }

    const doFetch = ctx.fetchImpl ?? fetch;
    try {
      const res = await doFetch(`${ctx.backendBaseUrl}/api/v1/agents/dispatch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(process.env.EVENTRELAY_API_KEY?.trim()
            ? { 'X-API-Key': process.env.EVENTRELAY_API_KEY.trim() }
            : {}),
        },
        body: JSON.stringify({
          job_id: ctx.jobId,
          agent_types: [agentType],
          events: [{ title: instruction, description: instruction, type: 'action' }],
        }),
        signal: AbortSignal.timeout(30_000),
      });
      if (!res.ok) {
        const detail = await res.text();
        return { summary: `Agent dispatch failed: ${res.status} ${detail}`, isError: true };
      }
      const body = await res.json();
      return { summary: `Dispatched ${agentType} agent`, data: body };
    } catch (err) {
      return { summary: `Agent dispatch error: ${String(err)}`, isError: true };
    }
  },
};

const addToKnowledgeBase: ActionTool = {
  name: 'add_to_knowledge_base',
  description:
    'Persist a durable insight or fact from the transcript into the RAG knowledge store for later retrieval.',
  parameters: {
    type: 'object',
    properties: {
      insight: { type: 'string', description: 'The insight/fact to store' },
      tags: { type: 'array', items: { type: 'string' }, description: 'Topic tags' },
    },
    required: ['insight', 'tags'],
    additionalProperties: false,
  },
  async execute(input, ctx) {
    const insight = str(input, 'insight');

    if (!ctx.backendBaseUrl) {
      return {
        summary: 'Cannot persist insight — no knowledge-base backend configured (set BACKEND_URL).',
        isError: true,
      };
    }

    const doFetch = ctx.fetchImpl ?? fetch;
    try {
      const res = await doFetch(`${ctx.backendBaseUrl}/api/v1/knowledge/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(process.env.EVENTRELAY_API_KEY?.trim()
            ? { 'X-API-Key': process.env.EVENTRELAY_API_KEY.trim() }
            : {}),
        },
        body: JSON.stringify({ text: insight, tags: strArray(input, 'tags'), source: ctx.jobId }),
        signal: AbortSignal.timeout(30_000),
      });
      if (!res.ok) {
        const detail = await res.text();
        return { summary: `Knowledge ingest failed: ${res.status} ${detail}`, isError: true };
      }
      return { summary: 'Stored insight in knowledge base', data: await res.json() };
    } catch (err) {
      return { summary: `Knowledge ingest error: ${String(err)}`, isError: true };
    }
  },
};

// ── Registry ──

export const ACTION_TOOLS: readonly ActionTool[] = [
  createWorkflowTask,
  saveResource,
  scheduleFollowup,
  dispatchAgent,
  addToKnowledgeBase,
];

/** Look up a tool by name. */
export function getTool(name: string): ActionTool | undefined {
  return ACTION_TOOLS.find((t) => t.name === name);
}

// ── Provider adapters ──

/** Tool definitions in OpenAI Responses-API function-tool format. */
export function toOpenAITools(tools: readonly ActionTool[] = ACTION_TOOLS) {
  return tools.map((t) => ({
    type: 'function' as const,
    name: t.name,
    description: t.description,
    parameters: t.parameters,
    strict: true,
  }));
}

/** Tool definitions in Gemini `functionDeclarations` format. */
export function toGeminiFunctionDeclarations(
  tools: readonly ActionTool[] = ACTION_TOOLS,
): FunctionDeclaration[] {
  return tools.map((t) => ({
    name: t.name,
    description: t.description,
    // `parametersJsonSchema` accepts plain JSON Schema directly (unlike
    // `parameters`, which expects Gemini's OpenAPI-style `Schema` type).
    parametersJsonSchema: t.parameters,
  }));
}

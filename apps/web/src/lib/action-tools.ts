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
import { backendHeaders } from '@/lib/pipeline-backend';

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
        headers: backendHeaders(),
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
        headers: backendHeaders(),
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

const dispatchSubagents: ActionTool = {
  name: 'dispatch_subagents',
  description:
    'Spawn multiple specialized subagents in parallel for a complex task. ' +
    'Each subagent receives its own instruction and runs independently. ' +
    'Use this when a task needs analysis from multiple perspectives (e.g. code review + testing + deployment).',
  parameters: {
    type: 'object',
    properties: {
      parentTask: { type: 'string', description: 'Description of the overall goal the subagents serve' },
      subagents: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            agentType: {
              type: 'string',
              enum: ['code_generator', 'researcher', 'deployer', 'summarizer', 'analyzer'],
            },
            instruction: { type: 'string', description: 'Concrete instruction for this subagent' },
          },
          required: ['agentType', 'instruction'],
          additionalProperties: false,
        },
        description: 'List of subagents to dispatch',
      },
    },
    required: ['parentTask', 'subagents'],
    additionalProperties: false,
  },
  async execute(input, ctx) {
    const parentTask = str(input, 'parentTask');
    const subagents = input.subagents;

    if (!ctx.backendBaseUrl) {
      return {
        summary: `Cannot dispatch subagents — no backend configured (set BACKEND_URL).`,
        isError: true,
      };
    }

    if (!Array.isArray(subagents) || subagents.length === 0) {
      return { summary: 'No subagents specified', isError: true };
    }

    // Validate each entry's shape at runtime; a bare `as` cast would let a
    // malformed entry (missing/non-string agentType or instruction) through and
    // silently produce `undefined` in the request body.
    const isValidSubagent = (
      s: unknown,
    ): s is { agentType: string; instruction: string } =>
      typeof s === 'object' &&
      s !== null &&
      typeof (s as { agentType?: unknown }).agentType === 'string' &&
      typeof (s as { instruction?: unknown }).instruction === 'string';

    if (!(subagents as unknown[]).every(isValidSubagent)) {
      return {
        summary: 'Invalid subagent: each entry needs a string agentType and instruction',
        isError: true,
      };
    }

    const typed = subagents as Array<{ agentType: string; instruction: string }>;
    const doFetch = ctx.fetchImpl ?? fetch;

    // Dispatch each subagent independently. The backend /agents/dispatch endpoint
    // runs the cartesian product of agent_types × events, so batching all
    // subagents into a single call (a de-duplicated agent_types list plus a
    // parallel events list) would pair every agentType with every instruction —
    // mispairing each subagent's agentType with the wrong instruction. Sending
    // one (agent_type, event) pair per call keeps each agentType bound to its
    // own instruction.
    const dispatchOne = async (
      sub: { agentType: string; instruction: string },
      idx: number,
    ): Promise<unknown> => {
      const event = {
        id: `sub_${Date.now()}_${idx}_${Math.random().toString(36).slice(2, 8)}`,
        type: 'action',
        title: sub.instruction,
        description: `Subagent task for: ${parentTask}`,
      };
      const res = await doFetch(`${ctx.backendBaseUrl}/api/v1/agents/dispatch`, {
        method: 'POST',
        headers: backendHeaders(),
        body: JSON.stringify({
          job_id: ctx.jobId,
          agent_types: [sub.agentType],
          events: [event],
        }),
        signal: AbortSignal.timeout(30_000),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${sub.agentType}: ${res.status} ${detail}`);
      }
      return res.json();
    };

    const settled = await Promise.allSettled(typed.map(dispatchOne));
    const dispatches = settled
      .filter((r): r is PromiseFulfilledResult<unknown> => r.status === 'fulfilled')
      .map((r) => r.value);
    const failures = settled
      .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
      .map((r) => String(r.reason));

    if (failures.length) {
      console.error(
        `dispatch_subagents: ${failures.length} subagent dispatch(es) failed:`,
        failures,
      );
    }

    if (dispatches.length === 0) {
      return { summary: `Subagent dispatch failed: ${failures.join('; ')}`, isError: true };
    }

    const count = dispatches.reduce<number>((n, body) => {
      const execs = (body as { data?: { executions?: unknown[] } })?.data?.executions;
      return n + (Array.isArray(execs) ? execs.length : 1);
    }, 0);
    const summary = failures.length
      ? `Dispatched ${count} subagent(s) for: ${parentTask} (${failures.length} failed: ${failures.join('; ')})`
      : `Dispatched ${count} subagent(s) for: ${parentTask}`;
    // Partial-success semantics: on a mix of successes and failures we still
    // return the successful `dispatches` in `data`, but set `isError: true` so
    // the failures aren't silently swallowed. Callers that care about partial
    // success should inspect `data.dispatches`/`summary` rather than `isError`
    // alone.
    return { summary, data: { dispatches }, isError: failures.length > 0 };
  },
};

const getAgentSessionLogs: ActionTool = {
  name: 'get_agent_session_logs',
  description:
    'Retrieve session logs from previously dispatched agents to review their findings, ' +
    'identify pending tasks, and decide follow-up actions. Use this to implement a feedback loop.',
  parameters: {
    type: 'object',
    properties: {
      agentType: {
        type: 'string',
        description: 'Filter logs to a specific agent type, or omit for all agents',
      },
      limit: { type: 'number', description: 'Maximum number of log entries to return (default 20)' },
    },
    required: [],
    additionalProperties: false,
  },
  async execute(input, ctx) {
    if (!ctx.backendBaseUrl) {
      return {
        summary: 'Cannot retrieve session logs — no backend configured (set BACKEND_URL).',
        isError: true,
      };
    }

    const agentType = str(input, 'agentType');
    const limit = typeof input.limit === 'number' ? input.limit : 20;

    const params = new URLSearchParams();
    if (agentType) params.set('agent_type', agentType);
    params.set('limit', String(limit));

    const doFetch = ctx.fetchImpl ?? fetch;
    try {
      const res = await doFetch(
        `${ctx.backendBaseUrl}/api/v1/agents/sessions?${params.toString()}`,
        {
          headers: backendHeaders(),
          signal: AbortSignal.timeout(10_000),
        },
      );
      if (!res.ok) {
        const detail = await res.text();
        return { summary: `Session logs retrieval failed: ${res.status} ${detail}`, isError: true };
      }
      const body = await res.json();
      const sessions = body?.data?.sessions ?? [];
      return {
        summary: `Retrieved ${sessions.length} agent session log(s)`,
        data: { sessions, count: sessions.length },
      };
    } catch (err) {
      console.error('get_agent_session_logs failed:', err);
      return { summary: `Session logs error: ${String(err)}`, isError: true };
    }
  },
};

// ── Registry ──

export const ACTION_TOOLS: readonly ActionTool[] = [
  createWorkflowTask,
  saveResource,
  scheduleFollowup,
  dispatchAgent,
  dispatchSubagents,
  getAgentSessionLogs,
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

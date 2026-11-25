import type { AgentExecution, AgentStatus } from '@/lib/types';
import type { LiveDispatchRequest } from '@/lib/live-studio-tasks';

export type DispatchOutcome =
  | { kind: 'dispatched'; dispatchId: string; executions: AgentExecution[] }
  | { kind: 'upgrade-required'; message: string }
  | { kind: 'unavailable'; message: string }
  | { kind: 'error'; status: number | null; message: string };

export type AgentStatusOutcome =
  | { kind: 'status'; execution: AgentExecution }
  | { kind: 'unavailable'; message: string }
  | { kind: 'error'; status: number | null; message: string };

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

async function readJson(response: Response): Promise<Record<string, unknown> | null> {
  try {
    return record(await response.json());
  } catch (error) {
    console.warn('[live-studio] non-JSON agent response', response.status, error);
    return null;
  }
}

const AGENT_STATUSES: readonly AgentStatus[] = ['queued', 'running', 'complete', 'failed'];

function parseExecution(value: unknown): AgentExecution | null {
  const row = record(value);
  if (!row || typeof row.agent_id !== 'string' || typeof row.agent_type !== 'string') return null;
  const status = AGENT_STATUSES.find((item) => item === row.status) ?? 'queued';
  return {
    agent_id: row.agent_id,
    agent_type: row.agent_type,
    status,
    progress: typeof row.progress === 'number' ? row.progress : 0,
    ...(typeof row.event_id === 'string' ? { event_id: row.event_id } : {}),
    ...(record(row.result) ? { result: record(row.result) as Record<string, unknown> } : {}),
    ...(typeof row.error === 'string' ? { error: row.error } : {}),
  };
}

function errorText(body: Record<string, unknown> | null, fallback: string): string {
  return typeof body?.error === 'string' && body.error.trim() ? body.error : fallback;
}

export async function probeDispatchAvailability(fetchImpl: FetchLike = fetch): Promise<boolean | null> {
  try {
    const response = await fetchImpl('/api/agents/dispatch', { signal: AbortSignal.timeout(8_000) });
    const body = await readJson(response);
    return typeof body?.available === 'boolean' ? body.available : null;
  } catch (error) {
    console.warn('[live-studio] dispatch availability probe failed', error);
    return null;
  }
}

export async function dispatchLiveTasks(
  request: LiveDispatchRequest,
  { fetchImpl = fetch, signal }: { fetchImpl?: FetchLike; signal?: AbortSignal } = {},
): Promise<DispatchOutcome> {
  const timeout = AbortSignal.timeout(35_000);
  let response: Response;
  try {
    response = await fetchImpl('/api/agents/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
  } catch (error) {
    console.warn('[live-studio] dispatch request failed', error);
    return { kind: 'error', status: null, message: error instanceof Error ? error.message : 'Dispatch request failed.' };
  }
  const body = await readJson(response);
  if (response.status === 402) {
    return { kind: 'upgrade-required', message: errorText(body, 'Agent dispatch is a Pro feature.') };
  }
  if (response.status === 503) {
    return { kind: 'unavailable', message: errorText(body, 'Agent backend not configured.') };
  }
  if (!response.ok) {
    return { kind: 'error', status: response.status, message: errorText(body, `Dispatch failed (${response.status}).`) };
  }
  const executions = Array.isArray(body?.executions)
    ? body.executions.flatMap((item) => {
        const parsed = parseExecution(item);
        return parsed ? [parsed] : [];
      })
    : [];
  if (typeof body?.dispatch_id !== 'string') {
    return { kind: 'error', status: response.status, message: 'Dispatch response had no dispatch_id.' };
  }
  return { kind: 'dispatched', dispatchId: body.dispatch_id, executions };
}

export async function fetchAgentStatus(
  agentId: string,
  { fetchImpl = fetch, signal }: { fetchImpl?: FetchLike; signal?: AbortSignal } = {},
): Promise<AgentStatusOutcome> {
  const timeout = AbortSignal.timeout(12_000);
  let response: Response;
  try {
    response = await fetchImpl(`/api/agents/status?agentId=${encodeURIComponent(agentId)}`, {
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
  } catch (error) {
    console.warn('[live-studio] agent status request failed', error);
    return { kind: 'error', status: null, message: error instanceof Error ? error.message : 'Status request failed.' };
  }
  const body = await readJson(response);
  if (response.status === 503) return { kind: 'unavailable', message: errorText(body, 'Agent backend not configured.') };
  const execution = response.ok ? parseExecution(body) : null;
  if (!execution) {
    return { kind: 'error', status: response.status, message: errorText(body, `Status failed (${response.status}).`) };
  }
  return { kind: 'status', execution };
}

export type RunLineStatus = 'queued' | 'running' | 'done' | 'failed';

export interface RunLine {
  seq: number;
  status: RunLineStatus;
  subject: string;
  text: string;
}

export function runLineStatus(status: AgentStatus): RunLineStatus {
  switch (status) {
    case 'queued':
      return 'queued';
    case 'running':
      return 'running';
    case 'complete':
      return 'done';
    case 'failed':
      return 'failed';
    default: {
      const unreachable: never = status;
      return unreachable;
    }
  }
}

export function isTerminal(status: AgentStatus): boolean {
  return status === 'complete' || status === 'failed';
}

export function executionLine(execution: AgentExecution, seq: number): RunLine {
  const status = runLineStatus(execution.status);
  const detail =
    status === 'failed'
      ? execution.error || 'failed'
      : status === 'done'
        ? 'done'
        : `${status}${execution.progress > 0 ? ` · ${Math.round(execution.progress)}%` : ''}`;
  return {
    seq,
    status,
    subject: `${execution.agent_type}${execution.event_id ? ` → ${execution.event_id}` : ''}`,
    text: detail,
  };
}

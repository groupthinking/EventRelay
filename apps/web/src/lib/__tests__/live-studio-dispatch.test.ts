import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  dispatchLiveTasks,
  executionLine,
  fetchAgentStatus,
  isTerminal,
  probeDispatchAvailability,
  runLineStatus,
} from '@/lib/live-studio-dispatch';
import type { LiveDispatchRequest } from '@/lib/live-studio-tasks';

const request: LiveDispatchRequest = {
  events: [{ id: 'G-REQ-01', type: 'action', title: 'Task', description: 'Spec', owner_agent: 'builder' }],
  agent_types: ['builder'],
};

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

afterEach(() => vi.restoreAllMocks());

describe('dispatchLiveTasks', () => {
  it('POSTs the request body with a timeout signal', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json(200, { dispatch_id: 'd-1', executions: [] }));
    await dispatchLiveTasks(request, { fetchImpl });
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/agents/dispatch');
    expect(init.method).toBe('POST');
    expect(JSON.parse(String(init.body))).toEqual(request);
    expect(init.signal).toBeInstanceOf(AbortSignal);
  });

  it('maps 402 to upgrade-required and 503 to unavailable', async () => {
    await expect(
      dispatchLiveTasks(request, { fetchImpl: vi.fn().mockResolvedValue(json(402, { error: 'Pro feature', upgradeRequired: true })) }),
    ).resolves.toEqual({ kind: 'upgrade-required', message: 'Pro feature' });
    await expect(
      dispatchLiveTasks(request, { fetchImpl: vi.fn().mockResolvedValue(json(503, { error: 'Backend not configured' })) }),
    ).resolves.toEqual({ kind: 'unavailable', message: 'Backend not configured' });
  });

  it('parses accepted executions', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      json(200, {
        dispatch_id: 'd-1',
        executions: [
          { agent_id: 'a-1', agent_type: 'builder', status: 'running', progress: 10, event_id: 'G-REQ-01' },
          { nope: true },
        ],
      }),
    );
    await expect(dispatchLiveTasks(request, { fetchImpl })).resolves.toEqual({
      kind: 'dispatched',
      dispatchId: 'd-1',
      executions: [{ agent_id: 'a-1', agent_type: 'builder', status: 'running', progress: 10, event_id: 'G-REQ-01' }],
    });
  });

  it('reports a missing dispatch id and network failures as errors', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    await expect(dispatchLiveTasks(request, { fetchImpl: vi.fn().mockResolvedValue(json(200, {})) })).resolves.toMatchObject({
      kind: 'error',
      status: 200,
    });
    await expect(
      dispatchLiveTasks(request, { fetchImpl: vi.fn().mockRejectedValue(new TypeError('offline')) }),
    ).resolves.toMatchObject({ kind: 'error', status: null });
  });
});

describe('fetchAgentStatus', () => {
  it('reads one execution by agent id', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json(200, { agent_id: 'a-1', agent_type: 'qa', status: 'complete', progress: 100 }));
    await expect(fetchAgentStatus('a 1', { fetchImpl })).resolves.toEqual({
      kind: 'status',
      execution: { agent_id: 'a-1', agent_type: 'qa', status: 'complete', progress: 100 },
    });
    expect(fetchImpl.mock.calls[0][0]).toBe('/api/agents/status?agentId=a%201');
  });

  it('maps 503 to unavailable', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json(503, { error: 'Backend not configured' }));
    await expect(fetchAgentStatus('a-1', { fetchImpl })).resolves.toEqual({ kind: 'unavailable', message: 'Backend not configured' });
  });
});

describe('probeDispatchAvailability', () => {
  it('returns the available flag, or null when unknown', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    await expect(probeDispatchAvailability(vi.fn().mockResolvedValue(json(200, { available: false })))).resolves.toBe(false);
    await expect(probeDispatchAvailability(vi.fn().mockRejectedValue(new Error('down')))).resolves.toBeNull();
  });
});

describe('run log lines', () => {
  it('maps agent statuses to terminal-style run lines', () => {
    expect(runLineStatus('queued')).toBe('queued');
    expect(runLineStatus('running')).toBe('running');
    expect(runLineStatus('complete')).toBe('done');
    expect(runLineStatus('failed')).toBe('failed');
    expect(isTerminal('complete')).toBe(true);
    expect(isTerminal('running')).toBe(false);
    const line = executionLine({ agent_id: 'a-1', agent_type: 'builder', status: 'failed', progress: 40, error: 'boom', event_id: 'G-REQ-01' }, 3);
    expect(line).toMatchObject({ seq: 3, status: 'failed' });
    expect(line.text).toContain('boom');
  });
});

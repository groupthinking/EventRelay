import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/action-agent', () => ({
  AVAILABLE_TOOL_NAMES: ['create_workflow_task', 'dispatch_agent'],
  runActionAgent: vi.fn(),
  executePreparedActions: vi.fn(),
}));
vi.mock('@/lib/gemini-client', () => ({ hasGeminiKey: vi.fn(() => true) }));
vi.mock('@/lib/billing/billing-context', () => ({
  resolveTrustedBillingEmail: vi.fn(async () => null),
}));
vi.mock('@/lib/billing/entitlement-store', () => ({
  isProSubscriber: vi.fn(async () => false),
}));

import { POST } from '@/app/api/agents/actions/route';
import { executePreparedActions, runActionAgent } from '@/lib/action-agent';
import { isProSubscriber } from '@/lib/billing/entitlement-store';

const mockedRunActionAgent = vi.mocked(runActionAgent);
const mockedExecutePreparedActions = vi.mocked(executePreparedActions);
const mockedIsProSubscriber = vi.mocked(isProSubscriber);

function request(body: unknown): Request {
  return new Request('http://localhost/api/agents/actions', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

describe('POST /api/agents/actions review gate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedIsProSubscriber.mockResolvedValue(false);
  });

  it('prepares a review-only plan by default', async () => {
    const action = {
      tool: 'create_workflow_task',
      input: { title: 'Review captions' },
      status: 'pending' as const,
      result: 'Prepared for review. No tool has been executed.',
    };
    mockedRunActionAgent.mockResolvedValue({ provider: 'gemini', actions: [action] });

    const response = await POST(request({ transcript: 'A sufficiently long verified transcript.' }));
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.actions).toEqual([action]);
    expect(mockedRunActionAgent).toHaveBeenCalledWith(
      expect.objectContaining({ executeTools: false }),
    );
    expect(mockedExecutePreparedActions).not.toHaveBeenCalled();
  });

  it('executes an exact reviewed local-output plan only in execute mode', async () => {
    const prepared = {
      tool: 'create_workflow_task',
      input: { title: 'Review captions' },
      status: 'pending' as const,
    };
    mockedExecutePreparedActions.mockResolvedValue([{ ...prepared, status: 'fulfilled' }]);

    const response = await POST(request({ mode: 'execute', actions: [prepared], jobId: 'job_1' }));
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.provider).toBe('confirmed-plan');
    expect(mockedExecutePreparedActions).toHaveBeenCalledWith({
      actions: [prepared],
      jobId: 'job_1',
    });
    expect(mockedRunActionAgent).not.toHaveBeenCalled();
  });

  it('blocks external execution for a non-Pro user', async () => {
    const prepared = {
      tool: 'dispatch_agent',
      input: { agentType: 'researcher', instruction: 'Research the evidence' },
      status: 'pending' as const,
    };

    const response = await POST(request({ mode: 'execute', actions: [prepared] }));
    const body = await response.json();

    expect(response.status).toBe(402);
    expect(body.upgradeRequired).toBe(true);
    expect(mockedExecutePreparedActions).not.toHaveBeenCalled();
  });

  it('rejects malformed plans and unknown modes', async () => {
    expect((await POST(request({ mode: 'execute', actions: [] }))).status).toBe(400);
    expect((await POST(request({ mode: 'surprise' }))).status).toBe(400);
  });
});

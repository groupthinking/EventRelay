import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/workflow-task-store', () => ({ workflowTaskOwner: vi.fn(async () => 'user-1'), readWorkflowTask: vi.fn() }));

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

import { workflowTaskOwner, readWorkflowTask } from '@/lib/workflow-task-store';
import { GET, POST } from '@/app/api/agents/actions/route';
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
    vi.mocked(workflowTaskOwner).mockResolvedValue('user-1');
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
      ownerId: 'user-1',
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

  it('rejects duplicate reviewed action calls to prevent replays', async () => {
    const first = {
      tool: 'create_workflow_task',
      input: { title: 'Review captions' },
      status: 'pending' as const,
    };

    const response = await POST(
      request({ mode: 'execute', actions: [first, { ...first, input: { title: 'Review captions' } }] }),
    );
    const body = await response.json();

    expect(response.status).toBe(400);
    expect(body.error).toBe('Duplicate reviewed tool calls are not allowed');
    expect(mockedExecutePreparedActions).not.toHaveBeenCalled();
  });

  it('rejects malformed plans and unknown modes', async () => {
    expect((await POST(request({ mode: 'execute', actions: [] }))).status).toBe(400);
    expect((await POST(request({ mode: 'surprise' }))).status).toBe(400);
  });
  it('rejects unauthenticated task writes even with a supplied owner', async () => {
    vi.mocked(workflowTaskOwner).mockResolvedValue(null);
    const response = await POST(request({ mode: 'execute', ownerId: 'spoof', jobId: 'run', actions: [{ tool: 'create_workflow_task', input: {} }] }));
    expect(response.status).toBe(401);
    expect(mockedExecutePreparedActions).not.toHaveBeenCalled();
  });

  it('requires a stable run ID for task execution', async () => {
    const response = await POST(request({ mode: 'execute', actions: [{ tool: 'create_workflow_task', input: {} }] }));
    expect(response.status).toBe(400);
    expect(mockedExecutePreparedActions).not.toHaveBeenCalled();
  });

  it('reads only the current session owner namespace', async () => {
    const id = 'a'.repeat(64);
    vi.mocked(readWorkflowTask).mockResolvedValue(null);
    const response = await GET(new Request(`http://localhost/api/agents/actions?taskId=${id}&ownerId=other`));
    expect(response.status).toBe(404);
    expect(readWorkflowTask).toHaveBeenCalledWith('user-1', id);
    vi.mocked(workflowTaskOwner).mockResolvedValue(null);
    expect((await GET(new Request(`http://localhost/api/agents/actions?taskId=${id}`))).status).toBe(401);
  });

});

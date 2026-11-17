import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

const state = vi.hoisted(() => ({
  journal: null as null | { persist: ReturnType<typeof vi.fn> },
  model: vi.fn(),
  execute: vi.fn(),
  identity: 'trusted@example.invalid' as string | null,
}));
vi.mock('@/lib/action-review-journal.mjs', () => ({
  resolveActionReviewJournal: () => state.journal,
}));
vi.mock('@/lib/action-agent', () => ({
  AVAILABLE_TOOL_NAMES: ['create_workflow_task'],
  runActionAgent: state.model,
  executePreparedActions: state.execute,
}));
vi.mock('@/lib/billing/billing-context', () => ({
  resolveTrustedBillingEmail: async () => state.identity,
}));
vi.mock('@/lib/billing/entitlement-store', () => ({
  isProSubscriber: async () => false,
}));
vi.mock('@/lib/workflow-task-store', () => ({
  workflowTaskOwner: async () => null,
  readWorkflowTask: vi.fn(),
}));
vi.mock('@/lib/gemini-client', () => ({ hasGeminiKey: () => false }));

import { POST } from '@/app/api/agents/actions/route';

const action = {
  tool: 'create_workflow_task',
  input: { title: 'Review target' },
  status: 'pending' as const,
  result: 'Prepared for review. No tool has been executed.',
  isError: false,
};
function request(body: unknown) {
  return new NextRequest('http://localhost/api/agents/actions', {
    method: 'POST',
    headers: { 'content-type': 'application/json', origin: 'http://localhost' },
    body: JSON.stringify(body),
  });
}
describe('combined local journal and durable-task route boundary', () => {
  beforeEach(() => {
    state.model.mockReset();
    state.execute.mockReset();
    state.identity = 'trusted@example.invalid';
    state.journal = { persist: vi.fn().mockResolvedValue({
      version: 'relay.local-receipt.v1', taskId: 'local-task',
      scope: 'local_artifact_only', state: 'complete',
      artifactVerified: true, originalActionsExecuted: false,
      originalTaskComplete: false,
    }) };
    state.model.mockResolvedValue({ provider: 'test', actions: [action] });
  });
  afterEach(() => { state.journal = null; });

  it('persists exact preview fields and never issues an executable token in review-only mode', async () => {
    const response = await POST(request({ mode: 'preview', transcript: 'A sufficiently long source transcript' }));
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.actions).toEqual([action]);
    expect(body.confirmationToken).toBeUndefined();
    expect(body.localArtifactReceipt.originalActionsExecuted).toBe(false);
    expect(state.journal?.persist).toHaveBeenCalledWith([action], 'trusted@example.invalid');
    expect(state.model).toHaveBeenCalledWith(expect.objectContaining({ executeTools: false }));
    expect(state.execute).not.toHaveBeenCalled();
  });
  it('denies all execute requests before invoking any action', async () => {
    const response = await POST(request({ mode: 'execute', actions: [action], jobId: 'forged', confirmationToken: 'forged' }));
    expect(response.status).toBe(409);
    expect(state.model).not.toHaveBeenCalled();
    expect(state.execute).not.toHaveBeenCalled();
    expect(state.journal?.persist).not.toHaveBeenCalled();
  });
  it('requires trusted identity before preview and local persistence', async () => {
    state.identity = null;
    const response = await POST(request({ transcript: 'A sufficiently long source transcript' }));
    expect(response.status).toBe(401);
    expect(state.model).not.toHaveBeenCalled();
  });
  it('fails closed on journal persistence failure', async () => {
    state.journal?.persist.mockRejectedValueOnce(new Error('disk unavailable'));
    const response = await POST(request({ transcript: 'A sufficiently long source transcript' }));
    const body = await response.json();
    expect(response.status).toBe(502);
    expect(body.success).toBe(false);
    expect(body.actions).toEqual([]);
    expect(state.execute).not.toHaveBeenCalled();
  });
  it('preserves existing preview path when local journal is disabled', async () => {
    state.journal = null;
    const response = await POST(request({ transcript: 'A sufficiently long source transcript' }));
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.actions).toEqual([action]);
    expect(body.localArtifactReceipt).toBeUndefined();
    expect(state.execute).not.toHaveBeenCalled();
  });
});

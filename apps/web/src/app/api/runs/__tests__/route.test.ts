/**
 * Regression tests for the run API guards.
 *
 * Two of these encode audit findings directly:
 *   - a failed `start()` must leave a *blocked* run, never a run stuck in
 *     `sourcing` with no worker attached (silent loss);
 *   - approval must be refused unless the run is actually waiting, so a
 *     replayed request cannot re-approve a finished run.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const start = vi.fn();
const resumeHook = vi.fn();
const createRun = vi.fn();
const blockRun = vi.fn();
const listRuns = vi.fn();
const loadRun = vi.fn();
const latestSpec = vi.fn();
const latestApproval = vi.fn();
const getRunOwner = vi.fn();
const resolveRunUserId = vi.fn();

vi.mock('workflow/api', () => ({
  start: (...args: unknown[]) => start(...args),
  resumeHook: (...args: unknown[]) => resumeHook(...args),
}));

vi.mock('@/workflows/delivery-run', () => ({
  deliveryRunWorkflow: async () => ({}),
  approvalToken: (runId: string) => `delivery-approval:${runId}`,
}));

vi.mock('@/lib/db/delivery-repo', () => ({
  createRun: (...args: unknown[]) => createRun(...args),
  blockRun: (...args: unknown[]) => blockRun(...args),
  listRuns: (...args: unknown[]) => listRuns(...args),
  loadRun: (...args: unknown[]) => loadRun(...args),
  latestSpec: (...args: unknown[]) => latestSpec(...args),
  latestApproval: (...args: unknown[]) => latestApproval(...args),
  getRunOwner: (...args: unknown[]) => getRunOwner(...args),
}));

vi.mock('@/lib/run-identity', () => ({
  LOCAL_DEV_USER: 'local-dev@eventrelay.invalid',
  resolveRunUserId: (...args: unknown[]) => resolveRunUserId(...args),
}));

const VIDEO = 'https://www.youtube.com/watch?v=auJzb1D-fag';
const OWNER = 'owner@example.com';
const RUN_ID = '11111111-1111-4111-8111-111111111111';

function postRuns(body: unknown): Request {
  return new Request('https://uvai.io/api/runs', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

beforeEach(() => {
  vi.resetModules();
  for (const fn of [
    start,
    resumeHook,
    createRun,
    blockRun,
    listRuns,
    loadRun,
    latestSpec,
    latestApproval,
    getRunOwner,
    resolveRunUserId,
  ]) {
    fn.mockReset();
  }
  resolveRunUserId.mockResolvedValue(OWNER);
});

describe('POST /api/runs', () => {
  it('rejects an anonymous caller', async () => {
    resolveRunUserId.mockResolvedValue(null);
    const { POST } = await import('../route');
    const res = await POST(postRuns({ sourceUrl: VIDEO }));
    expect(res.status).toBe(401);
    expect(createRun).not.toHaveBeenCalled();
  });

  it('rejects a non-YouTube source instead of fetching it', async () => {
    const { POST } = await import('../route');
    const res = await POST(postRuns({ sourceUrl: 'http://169.254.169.254/latest/meta-data' }));
    expect(res.status).toBe(400);
    expect(createRun).not.toHaveBeenCalled();
  });

  it('requires either a source URL or an idea', async () => {
    const { POST } = await import('../route');
    const res = await POST(postRuns({}));
    expect(res.status).toBe(400);
  });

  it('starts the workflow and returns the run id', async () => {
    createRun.mockResolvedValue(RUN_ID);
    start.mockResolvedValue({ runId: 'wf_1' });

    const { POST } = await import('../route');
    const res = await POST(postRuns({ sourceUrl: VIDEO }));
    const json = (await res.json()) as Record<string, unknown>;

    expect(res.status).toBe(202);
    expect(json.runId).toBe(RUN_ID);
    expect(json.streamUrl).toBe(`/api/runs/${RUN_ID}/stream`);
    expect(start).toHaveBeenCalledOnce();
    expect(blockRun).not.toHaveBeenCalled();
  });

  it('blocks the run when workflow dispatch fails, never leaving it silently queued', async () => {
    createRun.mockResolvedValue(RUN_ID);
    start.mockRejectedValue(new Error('world not configured'));
    blockRun.mockResolvedValue(undefined);

    const { POST } = await import('../route');
    const res = await POST(postRuns({ idea: 'a delivery engine for internal ops teams' }));

    expect(res.status).toBe(500);
    expect(blockRun).toHaveBeenCalledWith(
      RUN_ID,
      'sourcing',
      expect.stringContaining('workflow dispatch failed'),
    );
  });

  it('reports 503 rather than 500 when run storage is unavailable', async () => {
    createRun.mockRejectedValue(new Error('NEON_DATABASE_URL is not set'));
    const { POST } = await import('../route');
    const res = await POST(postRuns({ sourceUrl: VIDEO }));
    expect(res.status).toBe(503);
    expect(start).not.toHaveBeenCalled();
  });
});

describe('POST /api/runs/:runId/approve', () => {
  const params = { params: Promise.resolve({ runId: RUN_ID }) };

  function approveRequest(body: unknown): Request {
    return new Request(`https://uvai.io/api/runs/${RUN_ID}/approve`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  it("returns 404 for another user's run rather than confirming it exists", async () => {
    getRunOwner.mockResolvedValue('someone-else@example.com');
    const { POST } = await import('../[runId]/approve/route');
    const res = await POST(approveRequest({ approved: true }), params);
    expect(res.status).toBe(404);
    expect(resumeHook).not.toHaveBeenCalled();
  });

  it('refuses to approve a run that is not awaiting approval', async () => {
    getRunOwner.mockResolvedValue(OWNER);
    loadRun.mockResolvedValue({ id: RUN_ID, phase: 'delivered' });

    const { POST } = await import('../[runId]/approve/route');
    const res = await POST(approveRequest({ approved: true }), params);

    expect(res.status).toBe(409);
    expect(resumeHook).not.toHaveBeenCalled();
  });

  it('refuses approval when no spec version was persisted', async () => {
    getRunOwner.mockResolvedValue(OWNER);
    loadRun.mockResolvedValue({ id: RUN_ID, phase: 'awaiting_approval' });
    latestSpec.mockResolvedValue(null);

    const { POST } = await import('../[runId]/approve/route');
    const res = await POST(approveRequest({ approved: true }), params);

    expect(res.status).toBe(409);
    expect(resumeHook).not.toHaveBeenCalled();
  });

  it('resumes the hook with the session identity, not a client-supplied one', async () => {
    getRunOwner.mockResolvedValue(OWNER);
    loadRun.mockResolvedValue({ id: RUN_ID, phase: 'awaiting_approval' });
    latestSpec.mockResolvedValue({ id: 'spec-1', version: 2 });
    resumeHook.mockResolvedValue({ runId: 'wf_1' });

    const { POST } = await import('../[runId]/approve/route');
    const res = await POST(
      approveRequest({ approved: true, decidedBy: 'attacker@example.com', note: 'ship it' }),
      params,
    );
    const json = (await res.json()) as Record<string, unknown>;

    expect(res.status).toBe(200);
    expect(json.decidedBy).toBe(OWNER);
    expect(json.specVersion).toBe(2);
    expect(resumeHook).toHaveBeenCalledWith(`delivery-approval:${RUN_ID}`, {
      approved: true,
      decidedBy: OWNER,
      note: 'ship it',
    });
  });

  it('requires an explicit boolean decision', async () => {
    getRunOwner.mockResolvedValue(OWNER);
    const { POST } = await import('../[runId]/approve/route');
    const res = await POST(approveRequest({ note: 'looks fine' }), params);
    expect(res.status).toBe(400);
  });
});

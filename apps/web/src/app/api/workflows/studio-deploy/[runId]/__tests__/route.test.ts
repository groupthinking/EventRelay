import { beforeEach, describe, expect, it, vi } from 'vitest';

const getRun = vi.fn();

vi.mock('workflow/api', () => ({
  getRun: (...args: unknown[]) => getRun(...args),
}));

function runHandle(overrides: {
  exists?: boolean;
  status?: string;
  returnValue?: Promise<unknown>;
}) {
  return {
    exists: Promise.resolve(overrides.exists ?? true),
    status: Promise.resolve(overrides.status ?? 'completed'),
    workflowName: Promise.resolve('studioDeployWorkflow'),
    createdAt: Promise.resolve(new Date('2026-09-12T00:00:00.000Z')),
    startedAt: Promise.resolve(new Date('2026-09-12T00:00:00.000Z')),
    completedAt: Promise.resolve(new Date('2026-09-12T00:00:01.000Z')),
    returnValue: overrides.returnValue ?? Promise.resolve({ kind: 'job' }),
  };
}

describe('GET /api/workflows/studio-deploy/:runId', () => {
  beforeEach(() => {
    getRun.mockReset();
  });

  it('surfaces the failed-run cause instead of a generic unread return value', async () => {
    const cause = new Error('Deploy job job_1 still complete');
    const failed = new Error('Workflow run failed');
    Object.assign(failed, { cause });
    const rejected = Promise.reject(failed);
    rejected.catch(() => undefined);
    getRun.mockReturnValue(
      runHandle({
        status: 'failed',
        returnValue: rejected,
      }),
    );

    const { GET } = await import('../route');
    const res = await GET(new Request('https://uvai.io/api/workflows/studio-deploy/wrun_1'), {
      params: Promise.resolve({ runId: 'wrun_1' }),
    });
    const json = (await res.json()) as Record<string, unknown>;
    expect(res.status).toBe(200);
    expect(json.runStatus).toBe('failed');
    expect(json.error).toBe('Deploy job job_1 still complete');
    expect(json.error).not.toBe('Failed to read workflow return value');
  });

  it('does not HOLD with Failed to read workflow run when getRun fetch gets a Request', async () => {
    const parseErr = new TypeError('Failed to parse URL from [object Request]');
    Object.assign(parseErr, {
      cause: Object.assign(new TypeError('Invalid URL'), {
        code: 'ERR_INVALID_URL',
        input: '[object Request]',
      }),
    });
    getRun.mockImplementation(() => {
      throw parseErr;
    });

    const { GET } = await import('../route');
    const res = await GET(new Request('https://uvai.io/api/workflows/studio-deploy/wrun_req'), {
      params: Promise.resolve({ runId: 'wrun_req' }),
    });
    const json = (await res.json()) as Record<string, unknown>;
    expect(json.error).not.toBe('Failed to read workflow run');
    expect(json.error).not.toBe('Failed to read workflow return value');
    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(json.runId).toBe('wrun_req');
    expect(json.runStatus).toBe('running');
  });

  it('returns a completed live result when returnValue is readable', async () => {
    getRun.mockReturnValue(
      runHandle({
        status: 'completed',
        returnValue: Promise.resolve({
          kind: 'live',
          live_url: 'https://xy.vercel.app',
          jobId: 'job_1',
        }),
      }),
    );

    const { GET } = await import('../route');
    const res = await GET(new Request('https://uvai.io/api/workflows/studio-deploy/wrun_2'), {
      params: Promise.resolve({ runId: 'wrun_2' }),
    });
    const json = (await res.json()) as Record<string, unknown>;
    expect(res.status).toBe(200);
    expect(json.error).toBeUndefined();
    expect(json.result).toEqual({
      kind: 'live',
      live_url: 'https://xy.vercel.app',
      jobId: 'job_1',
    });
  });
});

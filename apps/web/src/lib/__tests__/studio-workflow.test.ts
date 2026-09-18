import { generateKeyPairSync, sign } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { canonicalGateJson, type GateDecision } from '@/lib/gate-transition';
import { evaluateOriginGate, type OriginGateEvaluation } from '@/lib/origin-gate';
import {
  getStudioDeployStatus,
  getVideoToActionsStatus,
  pollStudioDeploy,
  pollVideoToActions,
  startStudioDeploy,
  startVideoToActions,
  isTransientWorkflowRunReadError,
  isUnreadWorkflowRun,
  workflowReturnErrorMessage,
  studioDeployPollResidual,
  STUDIO_DEPLOY_POLL_ATTEMPTS,
  STUDIO_DEPLOY_POLL_DELAY_MS,
} from '@/lib/studio-workflow';
import {
  STUDIO_ORIGIN_KICKOFF_NO_JOB_HOLD,
  STUDIO_ORIGIN_NO_HOSTNAME_HOLD,
  STUDIO_ORIGIN_STILL_POLLABLE_HOLD,
} from '@/lib/studio-pipeline-status';

const receiptTime = Date.parse('2026-09-13T12:00:00.000Z');
const receiptIssuers = [generateKeyPairSync('ed25519'), generateKeyPairSync('ed25519')];
async function serverReceipt(decision: GateDecision, retained = true) {
  const binding = { transitionId: 'consumer-transition', kind: 'studio.deploy', fromState: 'proposed', toState: 'live', subject: 'consumer-owner', runId: 'consumer-run', artifactHash: 'a'.repeat(64), target: { provider: 'vercel', projectId: 'consumer-project', environment: 'preview', liveUrl: 'https://consumer.example.test' } };
  const attestations = receiptIssuers.map((key, index) => {
    const payload = { version: 'origin.attestation.v1', type: index ? 'deployment' : 'approval', issuer: `consumer-${index}`, nonce: `consumer-nonce-${index}`, issuedAt: new Date(receiptTime - 1000).toISOString(), expiresAt: new Date(receiptTime + 60_000).toISOString(), binding, verdict: index ? (decision === 'HOLD' ? 'unverified' : decision === 'REJECT' ? 'unreal' : 'real') : (decision === 'ESCALATE' ? 'unknown' : 'allow'), ...(index ? { providerReceiptId: 'consumer-provider-receipt', providerReceiptHash: 'b'.repeat(64) } : {}) };
    return { payload, signature: sign(null, Buffer.from(`origin.attestation.v1\n${canonicalGateJson(payload)}`), key.privateKey).toString('base64url') };
  });
  const { subject, ...proposal } = binding;
  return evaluateOriginGate({ ...proposal, approval: attestations[0], evidence: attestations[1] }, {
    subject, now: receiptTime, signingSecret: 'consumer-offline-secret-at-least-32-characters',
    store: {
      readPolicy: async () => ({ version: 1, issuers: receiptIssuers.map((key, index) => ({ id: `consumer-${index}`, role: index ? 'deployment-verifier' : 'loop', publicKey: key.publicKey.export({ type: 'spki', format: 'pem' }).toString(), projectIds: ['consumer-project'], revoked: false })) }),
      commit: async () => { if (!retained) throw new Error('offline retention failure'); return { status: 'stored' }; },
    },
  });
}
function respondWithGate(gate: unknown, status = 409) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: status === 200, status, json: async () => ({ ok: status === 200, gate }) }));
}

describe('studio-workflow (WDK Product v1)', () => {
  it.each(['PASS', 'HOLD', 'REJECT', 'ESCALATE'] as const)('preserves an evaluator-issued %s receipt without claiming execution success', async (decision) => {
    const gate = await serverReceipt(decision);
    expect(gate.decision).toBe(decision);
    respondWithGate(gate, decision === 'PASS' ? 200 : 409);
    const result = await startStudioDeploy({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' });
    expect(result).toMatchObject({ ok: false, gate: { decision, reason: gate.reason, reason_code: gate.reason_code, receiptId: gate.receipt.id, receiptHash: gate.receipt.receipt_hash, version: gate.receipt.version, transitionId: gate.receipt.transition_id, retained: true } });
    expect(result.runId).toBeUndefined();
  });

  it('preserves an actual unretained runtime HOLD', async () => {
    const gate = await serverReceipt('PASS', false);
    respondWithGate(gate);
    expect(await startStudioDeploy({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' })).toMatchObject({ ok: false, gate: { decision: 'HOLD', retained: false, reason_code: 'GATE_HOLD_RUNTIME_UNAVAILABLE' } });
  });

  it.each([
    ['unknown decision', (gate: OriginGateEvaluation) => ({ ...gate, decision: 'MAYBE' })],
    ['mismatched decision', (gate: OriginGateEvaluation) => ({ ...gate, receipt: { ...gate.receipt, decision: 'HOLD' } })],
    ['wrong version', (gate: OriginGateEvaluation) => ({ ...gate, receipt: { ...gate.receipt, version: 'eventrelay.gate-receipt.v1' } })],
    ['malformed hash', (gate: OriginGateEvaluation) => ({ ...gate, receipt: { ...gate.receipt, receipt_hash: 'invalid' } })],
    ['unsigned PASS', (gate: OriginGateEvaluation) => ({ ...gate, receipt: { ...gate.receipt, signature: null } })],
    ['unretained PASS', (gate: OriginGateEvaluation) => ({ ...gate, receipt: { ...gate.receipt, retained: false } })],
    ['mismatched reason', (gate: OriginGateEvaluation) => ({ ...gate, reason: 'An altered claim' })],
    ['mismatched reason code', (gate: OriginGateEvaluation) => ({ ...gate, reason_code: 'ALTERED' })],
  ] as const)('does not display a %s as an authoritative server receipt', async (_label, alter) => {
    respondWithGate(alter(await serverReceipt('PASS')));
    const result = await startStudioDeploy({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' });
    expect(result.ok).toBe(false);
    expect(result.gate).toBeUndefined();
  });
  it('preserves the server gate receipt on a blocked deployment', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 409,
      json: async () => ({ ok: false, gate: {
        decision: 'HOLD', reason: 'Artifact-bound evidence required.', reason_code: 'GATE_HOLD_MISSING_EVIDENCE',
        receipt: { version: 'eventrelay.gate-receipt.v2', decision: 'HOLD', reason: 'Artifact-bound evidence required.', reason_code: 'GATE_HOLD_MISSING_EVIDENCE', id: 'er:gate:v2:test', receipt_hash: 'a'.repeat(64), transition_id: 'transition-test', retained: false },
      } }),
    }));
    const result = await startStudioDeploy({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' });
    expect(result.ok).toBe(false);
    expect(result.gate).toEqual({ decision: 'HOLD', reason: 'Artifact-bound evidence required.', reason_code: 'GATE_HOLD_MISSING_EVIDENCE', receiptId: 'er:gate:v2:test', receiptHash: 'a'.repeat(64), version: 'eventrelay.gate-receipt.v2', transitionId: 'transition-test', retained: false });
  });

  it('prefers a failed-run cause over a generic unread-return message', () => {
    const cause = new Error('Deploy job job_1 still complete');
    const failed = new Error('Workflow run failed');
    Object.assign(failed, { cause });
    expect(workflowReturnErrorMessage(failed)).toBe('Deploy job job_1 still complete');
    expect(workflowReturnErrorMessage(new Error('fetch failed'))).toBe('fetch failed');
  });

  it('treats Request-parse GET failures as unread workflow run, not a terminal HOLD', () => {
    const parseErr = new TypeError('Failed to parse URL from [object Request]');
    Object.assign(parseErr, {
      cause: Object.assign(new TypeError('Invalid URL'), { code: 'ERR_INVALID_URL' }),
    });
    expect(isTransientWorkflowRunReadError(parseErr)).toBe(true);
    expect(
      isUnreadWorkflowRun({
        status: 500,
        error: 'Failed to read workflow run',
      }),
    ).toBe(true);
    expect(
      isUnreadWorkflowRun({
        runStatus: 'completed',
        result: { kind: 'live', live_url: 'https://ready.example.app' },
      }),
    ).toBe(false);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('startVideoToActions parses runId and statusUrl', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_abc',
          message: 'started',
        }),
      }),
    );

    const result = await startVideoToActions({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      videoTitle: 'Demo',
    });
    expect(result.ok).toBe(true);
    expect(result.runId).toBe('wrun_abc');
    expect(fetch).toHaveBeenCalledWith(
      '/api/workflows/video-to-actions',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('startVideoToActions posts the same-run transcript and events', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, runId: 'wrun_same' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await startVideoToActions({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      videoTitle: 'Fixture',
      transcript: 'x'.repeat(50),
      events: [{ type: 'action', title: 'Ship', description: 'now' }],
    });
    expect(result.ok).toBe(true);
    expect(result.runId).toBe('wrun_same');
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const body = JSON.parse(String(init.body));
    expect(body.url).toContain('auJzb1D-fag');
    expect(body.transcript).toHaveLength(50);
    expect(body.events).toEqual([{ type: 'action', title: 'Ship', description: 'now' }]);
  });

  it('startVideoToActions fails closed when ok but no runId', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      }),
    );
    const result = await startVideoToActions({
      url: 'https://www.youtube.com/watch?v=x',
    });
    expect(result.ok).toBe(false);
  });

  it('getVideoToActionsStatus maps completed result', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_1',
          runStatus: 'completed',
          result: {
            url: 'https://youtu.be/x',
            transcriptChars: 120,
            actionCount: 1,
            provider: 'openai',
            actions: [{ tool: 'create_workflow_task', status: 'fulfilled', result: 'ok' }],
          },
        }),
      }),
    );

    const poll = await getVideoToActionsStatus('wrun_1');
    expect(poll.ok).toBe(true);
    expect(poll.runStatus).toBe('completed');
    expect(poll.result?.actionCount).toBe(1);
    expect(poll.result?.actions[0].tool).toBe('create_workflow_task');
  });

  it('getVideoToActionsStatus maps usedProvidedTranscript', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_same',
          runStatus: 'completed',
          result: {
            url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
            transcriptChars: 80,
            actionCount: 1,
            usedProvidedTranscript: true,
            actions: [{ tool: 'create_workflow_task', status: 'fulfilled', result: 'ok' }],
          },
        }),
      }),
    );
    const poll = await getVideoToActionsStatus('wrun_same');
    expect(poll.result?.usedProvidedTranscript).toBe(true);
    expect(poll.result?.url).toContain('auJzb1D-fag');
  });

  it('pollVideoToActions returns when status becomes terminal', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ ok: true, runId: 'wrun_2', runStatus: 'running' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_2',
          runStatus: 'completed',
          result: {
            url: 'https://youtu.be/x',
            transcriptChars: 50,
            actionCount: 0,
            actions: [],
          },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const poll = await pollVideoToActions('wrun_2', { attempts: 5, delayMs: 1 });
    expect(poll.runStatus).toBe('completed');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('pollVideoToActions uses the durable statusUrl returned at start', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ok: true,
        runId: 'wrun_status_url',
        runStatus: 'completed',
        result: {
          url: 'https://youtu.be/x',
          transcriptChars: 50,
          actionCount: 0,
          actions: [],
        },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await pollVideoToActions('wrun_status_url', {
      statusUrl: '/api/workflows/video-to-actions/wrun_status_url',
      attempts: 1,
      delayMs: 1,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/workflows/video-to-actions/wrun_status_url',
      expect.any(Object),
    );
  });

  it('startStudioDeploy succeeds when the route returns a runId', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_c',
          message: 'started',
        }),
      }),
    );
    const started = await startStudioDeploy({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    });
    expect(started.ok).toBe(true);
    expect(started.runId).toBe('wrun_c');
    expect(fetch).toHaveBeenCalledWith(
      '/api/workflows/studio-deploy',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('keeps gate preflight bounded instead of resubmitting a large transcript', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ ok: false, message: 'Artifact-bound evidence required.' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const url = 'https://www.youtube.com/watch?v=auJzb1D-fag';
    const started = await startStudioDeploy({ url, transcript: 'x'.repeat(40_000) });
    expect(started.ok).toBe(false);
    const init = fetchMock.mock.calls[0]?.[1] as { body?: string };
    expect(JSON.parse(String(init.body))).toEqual({ url });
  });

  it('pollStudioDeploy returns on handoff result', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ok: true,
        runId: 'wrun_c2',
        runStatus: 'completed',
        result: { kind: 'handoff', message: 'BACKEND_URL is not configured' },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_c2', { attempts: 3, delayMs: 1 });
    expect(poll.runStatus).toBe('completed');
    expect(poll.result?.kind).toBe('handoff');
    expect(poll.result?.message).toMatch(/BACKEND_URL/);
  });

  it('startStudioDeploy is not ok when runId is missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      }),
    );
    const started = await startStudioDeploy({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    });
    expect(started.ok).toBe(false);
  });

  it('emits only a verified https live_url on the studio.deploy receipt path', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2B1Q97XA9GHVSG1FZY92N19',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'https://xy.vercel.app' },
        }),
      }),
    );
    const verified = await getStudioDeployStatus('wrun_01M2B1Q97XA9GHVSG1FZY92N19');
    expect(verified.result?.live_url).toBe('https://xy.vercel.app');

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2B1Q97XA9GHVSG1FZY92N19',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'http://xy.vercel.app' },
        }),
      }),
    );
    const rejected = await getStudioDeployStatus('wrun_01M2B1Q97XA9GHVSG1FZY92N19');
    expect(rejected.result?.live_url).toBeNull();
  });

  it('pollStudioDeploy keeps polling when GET cannot read the workflow run yet', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({
          ok: false,
          runId: 'wrun_01M2A9Z9SYXD59NG211W9N8EQA',
          error: 'Failed to read workflow run',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2A9Z9SYXD59NG211W9N8EQA',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'https://ready.example.app' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_01M2A9Z9SYXD59NG211W9N8EQA', {
      attempts: 4,
      delayMs: 1,
    });
    expect(poll.result?.live_url).toBe('https://ready.example.app');
    expect(poll.error).not.toBe('Failed to read workflow run');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('pollStudioDeploy keeps polling when completed has no result yet', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_unread',
          runStatus: 'completed',
          error: 'Failed to read workflow return value',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_unread',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'https://ready.example.app' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_unread', { attempts: 4, delayMs: 1 });
    expect(poll.result?.live_url).toBe('https://ready.example.app');
    expect(poll.error).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('pollStudioDeploy returns immediately on 404', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ error: 'Workflow run not found' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_missing', { attempts: 5, delayMs: 1 });
    expect(poll.status).toBe(404);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('pollStudioDeploy keeps polling while the run is still running until a live URL exists', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
          runStatus: 'running',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
          runStatus: 'running',
          result: { kind: 'job', jobId: 'job_96f498640b', jobStatus: 'transcribing' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'https://xy.vercel.app' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_01M2ABB1NJ5TFZ153CTRNTPNW9', {
      attempts: 5,
      delayMs: 1,
    });
    expect(poll.result?.live_url).toBe('https://xy.vercel.app');
    expect(poll.runStatus).toBe('completed');
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('pollStudioDeploy exhausted while WDK still running HOLDs still-pollable, not kickoff-no-job or attempt-started', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ok: true,
        runId: 'wrun_01M2B9NW5JA5JQNBTWDRRSHXD6',
        runStatus: 'running',
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_01M2B9NW5JA5JQNBTWDRRSHXD6', {
      attempts: 3,
      delayMs: 1,
    });
    const text = `${poll.error || ''} ${poll.message || ''}`;
    expect(poll.error).toBe(STUDIO_ORIGIN_STILL_POLLABLE_HOLD);
    expect(poll.message).toBe(STUDIO_ORIGIN_STILL_POLLABLE_HOLD);
    expect(text).toContain(STUDIO_ORIGIN_STILL_POLLABLE_HOLD);
    expect(text).not.toMatch(/kickoff returned no job id/i);
    expect(text).not.toMatch(/Deploy attempt started/i);
    expect(text).not.toMatch(/Waiting for a verified https live URL/i);
    expect(text).not.toMatch(/Deploy still running after 3 polls/i);
    expect(text).not.toMatch(/UNKNOWN checks are not a live URL/);
    expect(text).not.toMatch(/Failed to read workflow run/);
    expect(text).not.toMatch(/Failed to read workflow return value/);
    expect(text).not.toMatch(/BACKEND_URL is not configured/);
    expect(text).not.toMatch(/Origin deploy finished without a backend-supplied https hostname/i);
    expect(text).not.toMatch(/Origin video-to-software returned no verified live URL/i);
    expect(text).not.toMatch(/Ready transcript was not reused/i);
    expect(text).not.toMatch(/aborted due to timeout/i);
    expect(text).not.toMatch(/HTTP 524/);
    expect(text).not.toMatch(/Sign in to confirm you.?re not a bot/i);
    expect(poll.runId).toBe('wrun_01M2B9NW5JA5JQNBTWDRRSHXD6');
    expect(poll.runStatus).toBe('running');
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('classifies poll residuals: still-pollable vs kickoff-no-job vs hostname-finished', () => {
    expect(
      studioDeployPollResidual({
        ok: true,
        status: 200,
        runId: 'wrun_01M2B9NW5JA5JQNBTWDRRSHXD6',
        runStatus: 'running',
      }),
    ).toBe(STUDIO_ORIGIN_STILL_POLLABLE_HOLD);
    expect(
      studioDeployPollResidual({
        ok: true,
        status: 200,
        runId: 'wrun_01M2B9NW5JA5JQNBTWDRRSHXD6',
        runStatus: 'completed',
        result: { kind: 'handoff', message: STUDIO_ORIGIN_KICKOFF_NO_JOB_HOLD },
      }),
    ).toBe(STUDIO_ORIGIN_KICKOFF_NO_JOB_HOLD);
    expect(
      studioDeployPollResidual({
        ok: true,
        status: 200,
        runId: 'wrun_01M2B9NW5JA5JQNBTWDRRSHXD6',
        runStatus: 'completed',
        result: { kind: 'job', jobId: 'job_xy', jobStatus: 'complete' },
      }),
    ).toBe(STUDIO_ORIGIN_NO_HOSTNAME_HOLD);
    expect(
      studioDeployPollResidual({
        ok: true,
        status: 200,
        runId: 'wrun_01M2B9NW5JA5JQNBTWDRRSHXD6',
        runStatus: 'completed',
        result: { kind: 'live', live_url: 'https://xy.vercel.app' },
      }),
    ).toBeNull();
  });

  it('getStudioDeployStatus extracts a nested vercel live_url without inventing one', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2B9NW5JA5JQNBTWDRRSHXD6',
          runStatus: 'completed',
          result: {
            kind: 'live',
            live_url: null,
            deployment: { urls: { vercel: 'https://xy.vercel.app' } },
          },
        }),
      }),
    );
    const verified = await getStudioDeployStatus('wrun_01M2B9NW5JA5JQNBTWDRRSHXD6');
    expect(verified.result?.live_url).toBe('https://xy.vercel.app');
  });

  it('pollStudioDeploy exhausted in-flight cites the job status, not UNKNOWN checks', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ok: true,
        runId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
        runStatus: 'running',
        result: { kind: 'job', jobId: 'job_96f498640b', jobStatus: 'transcribing' },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_01M2ABB1NJ5TFZ153CTRNTPNW9', {
      attempts: 2,
      delayMs: 1,
    });
    const text = `${poll.error || ''} ${poll.message || ''}`;
    expect(text).toMatch(/job_96f498640b still transcribing/);
    expect(text).not.toMatch(/UNKNOWN checks are not a live URL/);
    expect(text).not.toMatch(/Failed to read workflow run/);
    expect(text).not.toMatch(/Failed to read workflow return value/);
    expect(text).not.toMatch(/BACKEND_URL is not configured/);
    expect(poll.runStatus).toBe('running');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('pollStudioDeploy keeps polling after a status-read abort timeout until a live URL exists', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(
        Object.assign(new Error('The operation was aborted due to timeout'), {
          name: 'TimeoutError',
        }),
      )
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2AKRAVZ0SEBM670BGXEMCQZ',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'https://xy.vercel.app' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_01M2AKRAVZ0SEBM670BGXEMCQZ', {
      attempts: 4,
      delayMs: 1,
    });
    expect(poll.result?.live_url).toBe('https://xy.vercel.app');
    expect(poll.runStatus).toBe('completed');
    expect(poll.error ?? '').not.toMatch(/aborted due to timeout/i);
    expect(poll.message ?? '').not.toMatch(/aborted due to timeout/i);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('client poll window covers kickoff retry plus the durable WDK job wait', () => {
    expect(STUDIO_DEPLOY_POLL_DELAY_MS).toBe(2000);
    expect(STUDIO_DEPLOY_POLL_ATTEMPTS * STUDIO_DEPLOY_POLL_DELAY_MS).toBeGreaterThanOrEqual(
      45_000 + 10_000 + 45_000 + 360_000,
    );
  });

  it('startStudioDeploy remaps a kickoff abort timeout instead of throwing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(
        Object.assign(new Error('The operation was aborted due to timeout'), {
          name: 'TimeoutError',
        }),
      ),
    );
    const started = await startStudioDeploy({
      url: 'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
      transcript:
        'Studio Video Pack for XYMcBrFSJ4c already has a usable transcript ready for deploy.',
    });
    expect(started.ok).toBe(false);
    expect(started.error ?? '').not.toMatch(/aborted due to timeout/i);
    expect(started.error ?? started.message ?? '').toMatch(/timed out|retry|origin/i);
  });

  it('pollStudioDeploy stops when the abort signal fires', async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn().mockImplementation(async () => {
      controller.abort();
      return {
        ok: true,
        status: 200,
        json: async () => ({ ok: true, runId: 'wrun_c3', runStatus: 'running' }),
      };
    });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_c3', {
      attempts: 8,
      delayMs: 20,
      signal: controller.signal,
    });
    expect(poll.message).toMatch(/abort/i);
    expect(fetchMock.mock.calls.length).toBeLessThan(8);
  });
});

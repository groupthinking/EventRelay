import { generateKeyPairSync, sign } from 'node:crypto';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { canonicalGateJson, hashCanonical } from '@/lib/gate-transition';
import { evaluateOriginGate, type OriginGateEvaluation, type OriginGateStore } from '@/lib/origin-gate';
import { COMMIT_ORIGIN_GATE_SCRIPT, createOriginGateStore, ORIGIN_GATE_POLICY_KEY } from '@/lib/origin-gate-store';

const now = Date.parse('2026-09-13T12:00:00.000Z');
const loop = generateKeyPairSync('ed25519');
const verifier = generateKeyPairSync('ed25519');
const policy = {
  version: 1,
  issuers: [
    { id: 'loop-test', role: 'loop', publicKey: loop.publicKey.export({ type: 'spki', format: 'pem' }).toString(), projectIds: ['prj_test'], revoked: false },
    { id: 'verifier-test', role: 'deployment-verifier', publicKey: verifier.publicKey.export({ type: 'spki', format: 'pem' }).toString(), projectIds: ['prj_test'], revoked: false },
  ],
};
const binding = {
  transitionId: 'transition-test', kind: 'studio.deploy', fromState: 'proposed', toState: 'live',
  subject: 'owner-test', runId: 'run-test', artifactHash: 'a'.repeat(64),
  target: { provider: 'vercel', projectId: 'prj_test', environment: 'preview', liveUrl: 'https://test.example.com' },
};
function attestation(type: 'approval' | 'deployment', changes = {}) {
  const payload = {
    version: 'origin.attestation.v1', type, issuer: type === 'approval' ? 'loop-test' : 'verifier-test',
    nonce: `nonce-${type}`, issuedAt: new Date(now - 1000).toISOString(), expiresAt: new Date(now + 60_000).toISOString(),
    binding, verdict: type === 'approval' ? 'allow' : 'real',
    ...(type === 'deployment' ? { providerReceiptId: 'deployment-test', providerReceiptHash: 'b'.repeat(64) } : {}), ...changes,
  };
  return { payload, signature: sign(null, Buffer.from(`origin.attestation.v1\n${canonicalGateJson(payload)}`), type === 'approval' ? loop.privateKey : verifier.privateKey).toString('base64url') };
}
function input(changes = {}) {
  const { subject: _subject, ...proposal } = binding;
  return { ...proposal, approval: attestation('approval'), evidence: attestation('deployment'), ...changes };
}
function setup(trust: unknown = policy) {
  const receipts = new Map<string, unknown>();
  const transitions = new Map<string, string>();
  const nonces = new Map<string, string>();
  const store: OriginGateStore = {
    readPolicy: vi.fn(async () => trust),
    commit: vi.fn<OriginGateStore['commit']>(async ({ requestHash, transitionKey, nonceKeys, evaluation }) => {
      if (receipts.has(requestHash)) return { status: 'existing', evaluation: receipts.get(requestHash) };
      if (evaluation.decision === 'PASS') {
        if (transitions.has(transitionKey) || nonceKeys.some((key) => nonces.has(key))) return { status: 'conflict' };
        transitions.set(transitionKey, requestHash);
        nonceKeys.forEach((key) => nonces.set(key, requestHash));
      }
      receipts.set(requestHash, evaluation);
      return { status: 'stored' };
    }),
  };
  const context = { subject: 'owner-test', now, signingSecret: 'unit-test-signing-secret-at-least-32-characters', store };
  return { store, context };
}

describe('Origin G.A.T.E. signed server boundary', () => {
  it('PASSes independently signed, exact-bound approval and evidence and retains a signed receipt', async () => {
    const { context, store } = setup();
    const result = await evaluateOriginGate(input(), context);
    expect(result.decision).toBe('PASS');
    expect(result.receipt).toMatchObject({ version: 'eventrelay.gate-receipt.v2', transition_id: binding.transitionId, artifact_hash: binding.artifactHash, run_id: binding.runId, retained: true });
    expect(result.receipt.signature).toMatch(/^[a-f0-9]{64}$/);
    const { receipt_hash, signature: _signature, ...body } = result.receipt;
    expect(receipt_hash).toBe(hashCanonical(canonicalGateJson(body)));
    expect(store.commit).toHaveBeenCalledTimes(1);
  });

  it('ESCALATEs without an authenticated subject; browser actor labels are not authority', async () => {
    const { context, store } = setup();
    expect((await evaluateOriginGate(input(), { ...context, subject: null })).decision).toBe('ESCALATE');
    expect(store.commit).not.toHaveBeenCalled();
  });

  it('HOLDs an evidence workspace with no artifact and never manufactures a live receipt', async () => {
    const { context } = setup();
    const result = await evaluateOriginGate({ transitionId: 'attempt-test', kind: 'studio.deploy', fromState: 'proposed', toState: 'live' }, context);
    expect(result.decision).toBe('HOLD');
    expect(result.reason_code).toBe('GATE_HOLD_MISSING_EVIDENCE');
    expect(result.receipt.to_state).toBe('live');
  });

  it('REJECTs a raw live claim without signed deployment evidence', async () => {
    const { context } = setup();
    expect((await evaluateOriginGate(input({ evidence: undefined }), context)).decision).toBe('REJECT');
  });

  it('HOLDs missing Loop approval even when deployment evidence is real', async () => {
    const { context } = setup();
    expect((await evaluateOriginGate(input({ approval: undefined }), context)).decision).toBe('HOLD');
  });

  it.each(['kind', 'fromState', 'toState'])('REJECTs unsupported %s', async (field) => {
    const { context } = setup();
    expect((await evaluateOriginGate(input({ [field]: 'not-authorized' }), context)).decision).toBe('REJECT');
  });

  it.each(['subject', 'runId', 'artifactHash', 'transitionId', 'target'])('REJECTs evidence bound to a different %s', async (field) => {
    const { context } = setup();
    const mismatch = { ...binding, [field]: field === 'target' ? { ...binding.target, projectId: 'other-project' } : field === 'artifactHash' ? 'c'.repeat(64) : 'other-value' };
    expect((await evaluateOriginGate(input({ evidence: attestation('deployment', { binding: mismatch }) }), context)).decision).toBe('REJECT');
  });

  it('REJECTs tampered signatures', async () => {
    const { context } = setup();
    const evidence = attestation('deployment');
    evidence.payload.providerReceiptId = 'tampered';
    expect((await evaluateOriginGate(input({ evidence }), context)).decision).toBe('REJECT');
  });

  it('REJECTs malformed artifact hashes and unknown request fields', async () => {
    const { context } = setup();
    expect((await evaluateOriginGate(input({ artifactHash: 'not-a-hash' }), context)).decision).toBe('REJECT');
    expect((await evaluateOriginGate(input({ authority: { actor: 'system' } }), context)).decision).toBe('REJECT');
  });

  it('ESCALATEs missing or invalid trust configuration', async () => {
    for (const trust of [null, {}, { version: 1, issuers: [] }]) {
      const { context } = setup(trust);
      expect((await evaluateOriginGate(input(), context)).decision).toBe('ESCALATE');
    }
  });

  it('REJECTs revoked signers and project-scope mismatches', async () => {
    for (const changes of [{ revoked: true }, { projectIds: ['other-project'] }]) {
      const { context } = setup({ ...policy, issuers: [{ ...policy.issuers[0], ...changes }, policy.issuers[1]] });
      expect((await evaluateOriginGate(input(), context)).decision).toBe('REJECT');
    }
  });

  it.each(['unverified', 'unreal', 'unknown'])('preserves the signed Zero-Sim %s verdict', async (verdict) => {
    const { context } = setup();
    expect((await evaluateOriginGate(input({ evidence: attestation('deployment', { verdict }) }), context)).decision).toBe(verdict === 'unverified' ? 'HOLD' : verdict === 'unreal' ? 'REJECT' : 'ESCALATE');
  });

  it('HOLDs expired, future-dated, and overlong attestations', async () => {
    for (const changes of [
      { expiresAt: new Date(now - 1).toISOString() },
      { issuedAt: new Date(now + 60_000).toISOString() },
      { expiresAt: new Date(now + 3_600_000).toISOString() },
    ]) {
      const { context } = setup();
      expect((await evaluateOriginGate(input({ approval: attestation('approval', changes) }), context)).decision).toBe('HOLD');
    }
  });

  it('REJECTs one cryptographic key impersonating both independent roles', async () => {
    const { context } = setup({ ...policy, issuers: [policy.issuers[0], { ...policy.issuers[1], publicKey: `${policy.issuers[0].publicKey}\n` }] });
    const evidence = attestation('deployment');
    evidence.signature = sign(null, Buffer.from(`origin.attestation.v1\n${canonicalGateJson(evidence.payload)}`), loop.privateKey).toString('base64url');
    expect((await evaluateOriginGate(input({ evidence }), context)).decision).toBe('REJECT');
  });

  it('REJECTs reused nonces on a separately signed transition', async () => {
    const { context } = setup();
    await evaluateOriginGate(input(), context);
    const changedBinding = { ...binding, transitionId: 'other-transition' };
    const result = await evaluateOriginGate(input({ transitionId: changedBinding.transitionId, approval: attestation('approval', { binding: changedBinding }), evidence: attestation('deployment', { binding: changedBinding }) }), context);
    expect(result.decision).toBe('REJECT');
    expect(result.reason_code).toBe('GATE_REJECT_REPLAY');
  });

  it('HOLDs an altered retained receipt instead of trusting storage blindly', async () => {
    const { context, store } = setup();
    const accepted = await evaluateOriginGate(input(), context);
    vi.mocked(store.commit).mockResolvedValue({ status: 'existing', evaluation: { ...accepted, receipt: { ...accepted.receipt, artifact_hash: 'f'.repeat(64) } } });
    expect((await evaluateOriginGate(input(), context)).decision).toBe('HOLD');
  });

  it('returns the identical receipt for concurrent identical retries', async () => {
    const { context } = setup();
    const [first, second] = await Promise.all([evaluateOriginGate(input(), context), evaluateOriginGate(input(), { ...context, now: now + 1000 })]);
    expect(first.decision).toBe('PASS');
    expect(second).toEqual(first);
  });

  it('REJECTs a second acceptance on the same transition, even with fresh nonces', async () => {
    const { context } = setup();
    await evaluateOriginGate(input(), context);
    const result = await evaluateOriginGate(input({ approval: attestation('approval', { nonce: 'fresh-approval' }), evidence: attestation('deployment', { nonce: 'fresh-evidence' }) }), context);
    expect(result.decision).toBe('REJECT');
    expect(result.reason_code).toBe('GATE_REJECT_REPLAY');
  });

  it('does not replay a previous PASS after issuer revocation', async () => {
    const { context, store } = setup();
    expect((await evaluateOriginGate(input(), context)).decision).toBe('PASS');
    vi.mocked(store.readPolicy).mockResolvedValue({ ...policy, issuers: [{ ...policy.issuers[0], revoked: true }, policy.issuers[1]] });
    expect((await evaluateOriginGate(input(), context)).decision).toBe('REJECT');
  });

  it('does not replay a previous PASS after attestation expiry', async () => {
    const { context } = setup();
    expect((await evaluateOriginGate(input(), context)).decision).toBe('PASS');
    expect((await evaluateOriginGate(input(), { ...context, now: now + 60_001 })).decision).toBe('HOLD');
  });

  it('HOLDs storage and signing failures instead of permitting a transition', async () => {
    const { context, store } = setup();
    vi.mocked(store.commit).mockRejectedValue(new Error('offline'));
    const result = await evaluateOriginGate(input(), context);
    expect(result.decision).toBe('HOLD');
    expect(result.receipt.retained).toBe(false);
    expect((await evaluateOriginGate(input(), { ...context, signingSecret: '' })).decision).toBe('HOLD');
  });
});

describe('Origin G.A.T.E. Upstash REST adapter', () => {
  const rawPolicy = JSON.stringify(policy);
  let evaluation: OriginGateEvaluation;
  const fetchMock = vi.fn();
  beforeEach(async () => {
    evaluation = await evaluateOriginGate(input(), setup().context);
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
    vi.stubEnv('KV_REST_API_URL', '');
    vi.stubEnv('KV_REST_API_TOKEN', '');
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://redis.example.test');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'test-rest-token');
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
  const commitInput = () => ({ requestHash: evaluation.receipt.request_hash, transitionKey: 'transition-hash', nonceKeys: ['approval-hash', 'verifier-hash'], evaluation });
  const response = (result: unknown) => ({ ok: true, json: async () => ({ result }) });

  it('atomically binds a PASS to the exact policy snapshot read for verification', async () => {
    fetchMock.mockResolvedValueOnce(response(rawPolicy)).mockResolvedValueOnce(response(['stored']));
    const store = createOriginGateStore();
    expect(await store.readPolicy()).toEqual(policy);
    expect(await store.commit(commitInput())).toEqual({ status: 'stored' });
    const [url, options] = fetchMock.mock.calls[1];
    expect(url).toBe('https://redis.example.test');
    expect(options).toMatchObject({ method: 'POST', cache: 'no-store', redirect: 'error' });
    const args = JSON.parse(options.body);
    expect(args[0]).toBe('EVAL');
    expect(args[1]).toBe(COMMIT_ORIGIN_GATE_SCRIPT);
    expect(args).toContain(ORIGIN_GATE_POLICY_KEY);
    expect(args.at(-1)).toBe(rawPolicy);
  });

  it('refuses a PASS commit without a loaded policy snapshot', async () => {
    fetchMock.mockResolvedValue(response(['stored']));
    await expect(createOriginGateStore().commit(commitInput())).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(['existing', 'conflict', 'unexpected', 'policy_changed'])('handles the atomic result %s without fabricating acceptance', async (status) => {
    const result = status === 'existing' ? [status, JSON.stringify(evaluation)] : [status];
    fetchMock.mockResolvedValueOnce(response(rawPolicy)).mockResolvedValueOnce(response(result));
    const store = createOriginGateStore();
    await store.readPolicy();
    if (status === 'existing') expect(await store.commit(commitInput())).toEqual({ status, evaluation });
    else if (status === 'conflict') expect(await store.commit(commitInput())).toEqual({ status });
    else await expect(store.commit(commitInput())).rejects.toThrow();
  });

  it('uses the injected KV REST alias pair without a TCP client', async () => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', '');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', '');
    vi.stubEnv('KV_REST_API_URL', 'https://kv.example.test');
    vi.stubEnv('KV_REST_API_TOKEN', 'offline-kv-token');
    fetchMock.mockResolvedValue(response(rawPolicy));
    expect(await createOriginGateStore().readPolicy()).toEqual(policy);
    expect(fetchMock).toHaveBeenCalledWith('https://kv.example.test', expect.objectContaining({
      method: 'POST',
      headers: { authorization: 'Bearer offline-kv-token', 'content-type': 'application/json' },
      body: JSON.stringify(['GET', ORIGIN_GATE_POLICY_KEY]),
    }));
  });

  it.each(['both', 'url', 'token'])('HOLDs without retained evidence when REST credentials are missing: %s', async (missing) => {
    if (missing !== 'token') vi.stubEnv('UPSTASH_REDIS_REST_URL', '');
    if (missing !== 'url') vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', '');
    const result = await evaluateOriginGate(input(), { ...setup().context, store: createOriginGateStore() });
    expect(result).toMatchObject({ decision: 'HOLD', reason_code: 'GATE_HOLD_RUNTIME_UNAVAILABLE', receipt: { retained: false } });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('fails closed on an unavailable REST runtime', async () => {
    fetchMock.mockResolvedValue({ ok: false });
    await expect(createOriginGateStore().readPolicy()).rejects.toThrow();
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'http://redis.example.test');
    await expect(createOriginGateStore().readPolicy()).rejects.toThrow();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

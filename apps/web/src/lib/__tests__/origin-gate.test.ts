import { createHash, createHmac, generateKeyPairSync, sign } from 'node:crypto';
import { encode } from 'next-auth/jwt';
import { NextRequest } from 'next/server';
import { POST as acceptTransition } from '@/app/api/gate/transitions/route';
import { POST as deploymentPreflight } from '@/app/api/workflows/studio-deploy/route';
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createClient } from 'redis';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { canonicalGateJson, hashCanonical } from '@/lib/gate-transition';
import { evaluateOriginGate, type OriginGateEvaluation, type OriginGateStore } from '@/lib/origin-gate';
import { COMMIT_ORIGIN_GATE_SCRIPT, createOriginGateStore, ORIGIN_GATE_POLICY_KEY } from '@/lib/origin-gate-store';

const { start } = vi.hoisted(() => ({ start: vi.fn() }));
vi.mock('workflow/api', () => ({ start }));
vi.mock('node:dns/promises', () => ({
  lookup: async (host: string) => {
    if (host !== 'www.youtube.com') throw new Error('Unexpected offline DNS request');
    return [{ address: '142.250.72.206', family: 4 }];
  },
}));

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
  const receipts = new Map<string, OriginGateEvaluation>();
  const transitions = new Map<string, string>();
  const nonces = new Map<string, string>();
  const store: OriginGateStore = {
    readPolicy: vi.fn(async () => trust),
    commit: vi.fn<OriginGateStore['commit']>(async ({ requestHash, transitionKey, nonceKeys, evaluation }) => {
      if (receipts.get(requestHash)?.decision === 'PASS') return { status: 'existing', evaluation: receipts.get(requestHash) };
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

function expectAuthenticReceipt(result: OriginGateEvaluation, secret = setup().context.signingSecret) {
  const { receipt_hash, signature, ...body } = result.receipt;
  const digest = createHash('sha256').update(canonicalGateJson(body), 'utf8').digest('hex');
  expect(receipt_hash).toBe(digest);
  expect(signature).toBe(createHmac('sha256', secret).update(`origin.gate-receipt.v2\n${digest}`).digest('hex'));
  expect(result).toMatchObject({ decision: body.decision, reason: body.reason, reason_code: body.reason_code });
}

describe('Origin G.A.T.E. signed server boundary', () => {
  describe.each(['approval', 'deployment'] as const)('%s contract matrix', (type) => {
    const field = type === 'approval' ? 'approval' : 'evidence';
    const signerIndex = type === 'approval' ? 0 : 1;
    const withAttestation = (changes: object) => input({ [field]: attestation(type, changes) });

    it.each([
      ['subject', { subject: 'another-owner' }],
      ['transition', { transitionId: 'another-transition' }],
      ['run', { runId: 'another-run' }],
      ['artifact', { artifactHash: 'c'.repeat(64) }],
      ['project', { target: { ...binding.target, projectId: 'another-project' } }],
      ['environment', { target: { ...binding.target, environment: 'production' } }],
      ['URL', { target: { ...binding.target, liveUrl: 'https://other.example.com' } }],
    ])('rejects a separately signed mismatched %s', async (_label, changes) => {
      const result = await evaluateOriginGate(withAttestation({ binding: { ...binding, ...changes } }), setup().context);
      expect(result).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_ATTESTATION_MISMATCH' });
    });

    it.each([
      ['revoked', { revoked: true }],
      ['wrong role', { role: type === 'approval' ? 'deployment-verifier' : 'loop' }],
      ['wrong project', { projectIds: ['other-project'] }],
    ])('rejects a %s issuer', async (_label, changes) => {
      const trust = { ...policy, issuers: policy.issuers.map((issuer, i) => i === signerIndex ? { ...issuer, ...changes } : issuer) };
      expect(await evaluateOriginGate(input(), setup(trust).context)).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_AUTHORITY_SCOPE' });
    });

    it('escalates an unknown issuer and an unusable registered key', async () => {
      expect(await evaluateOriginGate(withAttestation({ issuer: 'unknown' }), setup().context)).toMatchObject({ decision: 'ESCALATE', reason_code: 'GATE_ESCALATE_AUTHORITY_UNKNOWN' });
      const trust = { ...policy, issuers: policy.issuers.map((issuer, i) => i === signerIndex ? { ...issuer, publicKey: 'not-a-public-key' } : issuer) };
      expect(await evaluateOriginGate(input(), setup(trust).context)).toMatchObject({ decision: 'ESCALATE', reason_code: 'GATE_ESCALATE_AUTHORITY_UNKNOWN' });
    });

    it.each([
      ['issuance skew inclusive', 30_000, 60_000, 'PASS'],
      ['issuance skew exceeded', 30_001, 60_000, 'HOLD'],
      ['expiry exclusive', -1000, 0, 'HOLD'],
      ['just before expiry', -1000, 1, 'PASS'],
      ['maximum validity inclusive', -1000, 899_000, 'PASS'],
      ['maximum validity exceeded', -1000, 899_001, 'HOLD'],
      ['nonpositive lifetime', 1000, 1000, 'HOLD'],
    ] as const)('enforces %s', async (_label, issued, expires, decision) => {
      const result = await evaluateOriginGate(withAttestation({ issuedAt: new Date(now + issued).toISOString(), expiresAt: new Date(now + expires).toISOString() }), setup().context);
      expect(result).toMatchObject({ decision, reason_code: decision === 'PASS' ? 'GATE_PASS' : 'GATE_HOLD_STALE_EVIDENCE' });
    });

    it('rejects post-signature payload tampering and a valid signature over the wrong type', async () => {
      const envelope = attestation(type);
      envelope.payload.nonce = 'tampered-after-signing';
      expect(await evaluateOriginGate(input({ [field]: envelope }), setup().context)).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_ATTESTATION_MISMATCH' });
      expect(await evaluateOriginGate(withAttestation({ type: type === 'approval' ? 'deployment' : 'approval' }), setup().context)).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_ATTESTATION_MISMATCH' });
    });
  });

  it.each(['providerReceiptId', 'providerReceiptHash'])('holds signed real evidence without %s', async (field) => {
    expect(await evaluateOriginGate(input({ evidence: attestation('deployment', { [field]: undefined }) }), setup().context)).toMatchObject({ decision: 'HOLD', reason_code: 'GATE_HOLD_MISSING_EVIDENCE' });
  });

  it.each([
    ['allow', 'PASS', 'GATE_PASS'],
    ['deny', 'REJECT', 'GATE_REJECT_AUTHORITY_DENIED'],
    ['unknown', 'ESCALATE', 'GATE_ESCALATE_AUTHORITY_UNKNOWN'],
  ])('honors the signed Loop %s verdict', async (verdict, decision, reason_code) => {
    expect(await evaluateOriginGate(input({ approval: attestation('approval', { verdict }) }), setup().context)).toMatchObject({ decision, reason_code });
  });

  it('escalates duplicate issuer IDs rather than selecting a preferred record', async () => {
    expect(await evaluateOriginGate(input(), setup({ ...policy, issuers: [...policy.issuers, policy.issuers[0]] }).context)).toMatchObject({ decision: 'ESCALATE', reason_code: 'GATE_ESCALATE_AUTHORITY_UNKNOWN' });
  });

  it.each(['http://test.example.com', 'https://', ' https://test.example.com', 'https://test.example.com '])('rejects invalid or untrimmed target %s', async (liveUrl) => {
    expect(await evaluateOriginGate(input({ target: { ...binding.target, liveUrl } }), setup().context)).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_INVALID_TRANSITION', receipt: { retained: false } });
  });

  it.each(['https://127.0.0.1', 'https://user:pass@test.example.com', 'https://TEST.example.com', 'https://test.example.com/'])('requires exact signed URL bytes for %s, not URL-parser equivalence', async (liveUrl) => {
    const target = { ...binding.target, liveUrl };
    expect(await evaluateOriginGate(input({ target }), setup().context)).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_ATTESTATION_MISMATCH' });
    const exact = { ...binding, target };
    expect(await evaluateOriginGate(input({ target, approval: attestation('approval', { binding: exact }), evidence: attestation('deployment', { binding: exact }) }), setup().context)).toMatchObject({ decision: 'PASS' });
  });

  it('binds production explicitly without inventing an issuer environment allowlist', async () => {
    const production = { ...binding, target: { ...binding.target, environment: 'production' } };
    expect(await evaluateOriginGate(input({ target: production.target, approval: attestation('approval', { binding: production }), evidence: attestation('deployment', { binding: production }) }), setup().context)).toMatchObject({ decision: 'PASS' });
  });

  it('checks approval before evidence, and freshness before signed verdicts', async () => {
    expect(await evaluateOriginGate(input({ approval: attestation('approval', { verdict: 'unknown' }), evidence: attestation('deployment', { verdict: 'unreal' }) }), setup().context)).toMatchObject({ decision: 'ESCALATE', reason_code: 'GATE_ESCALATE_AUTHORITY_UNKNOWN' });
    expect(await evaluateOriginGate(input({ approval: attestation('approval', { verdict: 'deny', expiresAt: new Date(now).toISOString() }) }), setup().context)).toMatchObject({ decision: 'HOLD', reason_code: 'GATE_HOLD_STALE_EVIDENCE' });
    expect(await evaluateOriginGate(input({ evidence: undefined, approval: undefined }), setup().context)).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_CLAIM_MISMATCH' });
  });

  it('independently authenticates all four decision receipts with Node crypto', async () => {
    for (const proposal of [input(), input({ approval: undefined }), input({ evidence: undefined }), input({ approval: attestation('approval', { verdict: 'unknown' }) })]) {
      expectAuthenticReceipt(await evaluateOriginGate(proposal, setup().context));
    }
  });

  it.each(['decision', 'reason', 'reason_code', 'body', 'signature', 'hash', 'request', 'retained'])('fails closed on a retained receipt with altered %s', async (field) => {
    const { context, store } = setup();
    const accepted = await evaluateOriginGate(input(), context);
    const altered = structuredClone(accepted);
    if (field === 'decision') altered.decision = 'HOLD';
    if (field === 'reason') altered.reason = 'Forged reason';
    if (field === 'reason_code') altered.reason_code = 'FORGED';
    if (field === 'body') altered.receipt.artifact_hash = 'f'.repeat(64);
    if (field === 'signature') altered.receipt.signature = '0'.repeat(64);
    if (field === 'hash') altered.receipt.receipt_hash = '0'.repeat(64);
    if (field === 'request') altered.receipt.request_hash = '0'.repeat(64);
    if (field === 'retained') altered.receipt.retained = false;
    vi.mocked(store.commit).mockResolvedValue({ status: 'existing', evaluation: altered });
    expect(await evaluateOriginGate(input(), context)).toMatchObject({ decision: 'HOLD', reason_code: 'GATE_HOLD_RUNTIME_UNAVAILABLE', receipt: { retained: false } });
  });

  it('does not reaccept a retained PASS after signing-secret rotation or a policy read failure', async () => {
    const { context, store } = setup();
    expect((await evaluateOriginGate(input(), context)).decision).toBe('PASS');
    expect(await evaluateOriginGate(input(), { ...context, signingSecret: 'rotated-offline-secret-at-least-32-characters' })).toMatchObject({ decision: 'HOLD', receipt: { retained: false } });
    vi.mocked(store.readPolicy).mockRejectedValue(new Error('offline'));
    expect(await evaluateOriginGate(input(), context)).toMatchObject({ decision: 'HOLD', receipt: { retained: false } });
  });
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

  it('does not claim retention when the per-user receipt quota is exhausted', async () => {
    const { context, store } = setup();
    vi.mocked(store.commit).mockResolvedValue({ status: 'quota' });
    const result = await evaluateOriginGate({ transitionId: 'quota-test', kind: 'studio.deploy', fromState: 'proposed', toState: 'live' }, context);
    expect(result).toMatchObject({ decision: 'HOLD', reason_code: 'GATE_HOLD_RETENTION_LIMIT', receipt: { retained: false } });
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

// Opt-in executes the production Lua against a disposable Unix-socket Redis, never a configured store.
describe.runIf(process.env.ORIGIN_GATE_REDIS_TESTS === '1')('Origin G.A.T.E. isolated Redis atomic commits', () => {
  let server: ChildProcess;
  let directory: string;
  let redis: ReturnType<typeof createClient>;
  const receiptKey = (result: OriginGateEvaluation) => `er:gate:v2:receipt:${result.receipt.request_hash}`;
  const pending = (transitionId: string) => ({ transitionId, kind: 'studio.deploy', fromState: 'proposed', toState: 'live' });
  const futureProposal = () => input({
    approval: attestation('approval', { issuedAt: new Date(now + 60_000).toISOString(), expiresAt: new Date(now + 180_000).toISOString() }),
    evidence: attestation('deployment', { expiresAt: new Date(now + 180_000).toISOString() }),
  });
  const evaluate = (proposal: unknown, time = now, subject = binding.subject) => evaluateOriginGate(proposal, {
    subject, now: time, signingSecret: setup().context.signingSecret, store: createOriginGateStore(),
  });
  const quotaKey = async () => {
    const keys = await redis.keys('er:gate:v2:pending:*');
    expect(keys).toHaveLength(1);
    return keys[0];
  };

  beforeAll(async () => {
    const binary = ['redis-server', 'redis6-server'].find((name) => spawnSync(name, ['--version']).status === 0);
    if (!binary) throw new Error('ORIGIN_GATE_REDIS_TESTS requires redis-server or redis6-server; no external store is used.');
    directory = await mkdtemp(join(tmpdir(), 'origin-gate-test-'));
    const socketPath = join(directory, 'redis.sock');
    server = spawn(binary, ['--port', '0', '--unixsocket', socketPath, '--unixsocketperm', '700', '--save', '', '--appendonly', 'no'], {
      env: { PATH: process.env.PATH, NODE_ENV: 'test' }, stdio: ['ignore', 'pipe', 'pipe'],
    });
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Isolated Redis did not become ready')), 5000);
      server.once('error', (error) => { clearTimeout(timeout); reject(error); });
      server.once('exit', (code) => { clearTimeout(timeout); reject(new Error(`Isolated Redis exited: ${code}`)); });
      server.stdout!.on('data', (data: Buffer) => {
        if (/ready to accept connections/i.test(data.toString())) { clearTimeout(timeout); resolve(); }
      });
    });
    redis = createClient({ socket: { path: socketPath, reconnectStrategy: false } });
    await redis.connect();
  });
  afterAll(async () => {
    if (redis?.isOpen) redis.destroy();
    if (server && server.exitCode === null) {
      await new Promise<void>((resolve) => { server.once('exit', () => resolve()); server.kill(); });
    }
    if (directory) await rm(directory, { recursive: true, force: true });
  });
  beforeEach(async () => {
    await redis.flushDb();
    await redis.set(ORIGIN_GATE_POLICY_KEY, JSON.stringify(policy));
    vi.stubEnv('NODE_ENV', 'test');
    vi.stubEnv('NEXTAUTH_URL', 'https://offline-studio.example.test');
    vi.stubEnv('NEXTAUTH_SECRET', setup().context.signingSecret);
    for (const key of ['V0_SANDBOX_URL', 'V0_RUNTIME_URL', 'V0_BUILD_URL', 'KV_REST_API_READ_ONLY_TOKEN']) vi.stubEnv(key, '');
    start.mockClear();
    vi.stubEnv('KV_REST_API_URL', '');
    vi.stubEnv('KV_REST_API_TOKEN', '');
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://offline-gate.example.test');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'offline-only');
    vi.stubGlobal('fetch', vi.fn(async (url: string, options: RequestInit) => {
      expect(url).toBe('https://offline-gate.example.test');
      expect(options).toMatchObject({ method: 'POST', cache: 'no-store', redirect: 'error' });
      expect(new Headers(options.headers).get('authorization')).toBe('Bearer offline-only');
      const args = JSON.parse(String(options.body)) as Array<string | number>;
      expect(['GET', 'EVAL']).toContain(args[0]);
      const result = await redis.sendCommand(args.map(String));
      return { ok: true, json: async () => ({ result }) };
    }));
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

  it.each(['HOLD', 'REJECT', 'ESCALATE'])('bounds %s receipt and quota-index retention to 24 hours', async (decision) => {
    const proposal = decision === 'HOLD' ? pending('pending-test') : decision === 'REJECT' ? input({ evidence: undefined }) : input({ approval: attestation('approval', { issuer: 'unknown-issuer' }) });
    const result = await evaluate(proposal);
    expect(result).toMatchObject({ decision, receipt: { retained: true } });
    expect(await redis.ttl(receiptKey(result))).toBeGreaterThan(0);
    expect(await redis.ttl(receiptKey(result))).toBeLessThanOrEqual(86400);
    expect(await redis.zCard(await quotaKey())).toBe(1);
    expect(await redis.ttl(await quotaKey())).toBeGreaterThan(0);
    expect(await redis.ttl(await quotaKey())).toBeLessThanOrEqual(86400);
    expect(await redis.keys('er:gate:v2:transition:*')).toEqual([]);
    expect(await redis.keys('er:gate:v2:nonce:*')).toEqual([]);
  });

  it('atomically caps one subject at 100 pending receipts, including concurrent requests', async () => {
    const results = await Promise.all(Array.from({ length: 105 }, (_, i) => evaluate(pending(`pending-${i}`))));
    expect(results.filter((result) => result.receipt.retained)).toHaveLength(100);
    expect(results.filter((result) => result.reason_code === 'GATE_HOLD_RETENTION_LIMIT')).toHaveLength(5);
    expect(await redis.keys('er:gate:v2:receipt:*')).toHaveLength(100);
    expect(await redis.zCard(await quotaKey())).toBe(100);
    expect(await quotaKey()).not.toContain(binding.subject);
    const retained = results.find((result) => result.receipt.retained)!;
    expect((await evaluate(pending(retained.receipt.transition_id))).receipt.retained).toBe(true);
    expect(await redis.zCard(await quotaKey())).toBe(100);
    expect((await evaluate(pending('other-owner'), now, 'owner-other')).receipt.retained).toBe(true);
    expect((await evaluate(input())).decision).toBe('PASS');
  });

  it('prunes expired quota members using storage time rather than caller time', async () => {
    await Promise.all(Array.from({ length: 99 }, (_, i) => evaluate(pending(`pending-${i}`))));
    const key = await quotaKey();
    await redis.zAdd(key, { score: 0, value: 'expired-receipt' });
    expect(await redis.zCard(key)).toBe(100);
    const result = await evaluate(pending('new-after-expiry'), now - 86400_000);
    expect(result.receipt.retained).toBe(true);
    expect(await redis.zCard(key)).toBe(100);
    expect(await redis.zScore(key, 'expired-receipt')).toBeNull();
  });

  it('re-evaluates a future-dated HOLD and atomically promotes it to one permanent PASS', async () => {
    const proposal = futureProposal();
    const held = await evaluate(proposal);
    expect(held).toMatchObject({ decision: 'HOLD', reason_code: 'GATE_HOLD_STALE_EVIDENCE', receipt: { retained: true } });
    const [first, retry] = await Promise.all([evaluate(proposal, now + 65_000), evaluate(proposal, now + 66_000)]);
    expect(first.decision).toBe('PASS');
    expect(retry).toEqual(first);
    expect(first.receipt.request_hash).toBe(held.receipt.request_hash);
    expect(await redis.ttl(receiptKey(first))).toBe(-1);
    expect(await redis.keys('er:gate:v2:pending:*')).toEqual([]);
    for (const pattern of ['er:gate:v2:transition:*', 'er:gate:v2:nonce:*']) {
      const keys = await redis.keys(pattern);
      expect(keys).toHaveLength(pattern.includes('nonce') ? 2 : 1);
      for (const key of keys) expect(await redis.ttl(key)).toBe(-1);
    }
  });

  it('keeps accepted receipts immutable and replay markers permanent after a negative retry', async () => {
    const accepted = await evaluate(input());
    const raw = await redis.get(receiptKey(accepted));
    const expired = await evaluate(input(), now + 60_001);
    expect(expired.decision).toBe('HOLD');
    expect(expired.receipt.retained).toBe(false);
    expect(await redis.get(receiptKey(accepted))).toBe(raw);
    expect(await redis.ttl(receiptKey(accepted))).toBe(-1);
    const replayed = await evaluate(input({ approval: attestation('approval', { nonce: 'fresh-approval' }), evidence: attestation('deployment', { nonce: 'fresh-evidence' }) }));
    expect(replayed).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_REPLAY', receipt: { retained: false } });
    const changed = { ...binding, transitionId: 'another-transition' };
    expect(await evaluate(input({ transitionId: changed.transitionId, approval: attestation('approval', { binding: changed }), evidence: attestation('deployment', { binding: changed }) }))).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_REPLAY' });
  });

  it('cannot promote a held receipt if the policy changes before commit', async () => {
    const proposal = futureProposal();
    const held = await evaluate(proposal);
    const raw = await redis.get(receiptKey(held));
    const evaluation = await evaluateOriginGate(proposal, { ...setup().context, now: now + 65_000 });
    expect(evaluation.decision).toBe('PASS');
    expect(evaluation.receipt.request_hash).toBe(held.receipt.request_hash);
    const store = createOriginGateStore();
    await store.readPolicy();
    await redis.set(ORIGIN_GATE_POLICY_KEY, JSON.stringify({ ...policy, issuers: [] }));
    await expect(store.commit({ evaluation, requestHash: evaluation.receipt.request_hash, transitionKey: 'transition-test', nonceKeys: ['approval', 'verifier'] })).rejects.toThrow();
    expect(await redis.get(receiptKey(held))).toBe(raw);
    expect(await redis.zCard(await quotaKey())).toBe(1);
    expect(await redis.keys('er:gate:v2:transition:*')).toEqual([]);
    expect(await redis.keys('er:gate:v2:nonce:*')).toEqual([]);
  });

  it('does not promote a held request after another request accepts its transition', async () => {
    const proposal = futureProposal();
    const held = await evaluate(proposal);
    const raw = await redis.get(receiptKey(held));
    const accepted = await evaluate(input({
      approval: attestation('approval', { nonce: 'other-approval' }),
      evidence: attestation('deployment', { nonce: 'other-evidence' }),
    }));
    expect(accepted.decision).toBe('PASS');
    expect(await evaluate(proposal, now + 65_000)).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_REPLAY', receipt: { retained: false } });
    expect(await redis.get(receiptKey(held))).toBe(raw);
    expect(await redis.ttl(receiptKey(accepted))).toBe(-1);
    expect(await redis.zCard(await quotaKey())).toBe(1);
  });

  describe('real route → NextAuth → evaluator → REST adapter → Lua', () => {
    let session: string;
    beforeEach(async () => {
      // Freeze JWT and evaluator time together, leaving process/socket cleanup timers real.
      vi.useFakeTimers({ toFake: ['Date'] });
      vi.setSystemTime(now);
      session = await encode({ secret: setup().context.signingSecret, token: { sub: binding.subject }, maxAge: 900 });
    });
    afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

    function request(body: unknown, options: { session?: string; origin?: string; path?: string; contentType?: string; raw?: string } = {}) {
      return new NextRequest(`https://offline-studio.example.test${options.path ?? '/api/gate/transitions'}`, {
        method: 'POST',
        headers: {
          origin: options.origin ?? 'https://offline-studio.example.test',
          'content-type': options.contentType ?? 'application/json',
          cookie: `__Secure-next-auth.session-token=${options.session ?? session}`,
        },
        body: options.raw ?? JSON.stringify(body),
      });
    }
    async function submit(proposal: unknown = input()) {
      const response = await acceptTransition(request(proposal));
      expect(response.headers.get('cache-control')).toBe('no-store');
      const payload = await response.json() as { ok: boolean; gate: OriginGateEvaluation };
      expectAuthenticReceipt(payload.gate);
      return { response, ...payload };
    }

    it('returns HTTP 200 only with the authentic retained record and permanent replay markers', async () => {
      const { response, ok, gate } = await submit();
      expect(response.status).toBe(200);
      expect(ok).toBe(true);
      expect(gate).toMatchObject({ decision: 'PASS', receipt: { retained: true, authority: { claim: binding.subject }, artifact_hash: binding.artifactHash, target: binding.target } });
      expect(JSON.parse((await redis.get(receiptKey(gate)))!)).toEqual(gate);
      expect(await redis.ttl(receiptKey(gate))).toBe(-1);
      const markers = [...await redis.keys('er:gate:v2:transition:*'), ...await redis.keys('er:gate:v2:nonce:*')];
      expect(markers).toHaveLength(3);
      for (const key of markers) {
        expect(await redis.get(key)).toBe(gate.receipt.request_hash);
        expect(await redis.ttl(key)).toBe(-1);
      }
      expect(start).not.toHaveBeenCalled();
    });

    it.each(['HOLD', 'REJECT', 'ESCALATE'])('returns HTTP 409 with a real retained %s', async (decision) => {
      const proposal = decision === 'HOLD' ? pending('missing') : decision === 'REJECT' ? input({ evidence: attestation('deployment', { verdict: 'unreal' }) }) : input({ approval: attestation('approval', { issuer: 'unregistered' }) });
      const { response, ok, gate } = await submit(proposal);
      expect(response.status).toBe(409);
      expect(ok).toBe(false);
      expect(gate.decision).toBe(decision);
      expect(JSON.parse((await redis.get(receiptKey(gate)))!)).toEqual(gate);
      expect(await redis.keys('er:gate:v2:transition:*')).toEqual([]);
      expect(await redis.keys('er:gate:v2:nonce:*')).toEqual([]);
    });

    it.each(['missing', 'forged', 'expired', 'cross-origin'])('denies %s identity before any storage call', async (kind) => {
      const invalidSession = kind === 'forged' ? await encode({ secret: 'not-the-offline-session-secret', token: { sub: binding.subject } }) : kind === 'expired' ? await encode({ secret: setup().context.signingSecret, token: { sub: binding.subject }, maxAge: -60 }) : '';
      const response = await acceptTransition(request(input(), kind === 'cross-origin' ? { origin: 'https://untrusted.example.test' } : { session: invalidSession }));
      expect(response.status).toBe(kind === 'cross-origin' ? 403 : 401);
      expect(response.headers.get('cache-control')).toBe('no-store');
      expect(fetch).not.toHaveBeenCalled();
      expect(await redis.keys('er:gate:v2:receipt:*')).toEqual([]);
    });

    it('rejects caller-supplied identity and signed evidence belonging to another session', async () => {
      const supplied = await submit(input({ subject: 'forged-owner' }));
      expect(supplied.gate).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_INVALID_TRANSITION', receipt: { retained: false } });
      expect(fetch).not.toHaveBeenCalled();
      session = await encode({ secret: setup().context.signingSecret, token: { sub: 'different-authenticated-owner' } });
      const other = await submit();
      expect(other.gate).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_ATTESTATION_MISMATCH', receipt: { authority: { claim: 'different-authenticated-owner' } } });
      expect(await redis.keys('er:gate:v2:transition:*')).toEqual([]);
    });

    it.each([
      ['malformed JSON', { raw: '{' }, 400],
      ['wrong content type', { contentType: 'text/plain' }, 415],
      ['oversized JSON', { raw: JSON.stringify({ padding: 'x'.repeat(33_000) }) }, 413],
    ])('denies %s before evaluation', async (_label, options, status) => {
      const response = await acceptTransition(request({}, options as Parameters<typeof request>[1]));
      expect(response.status).toBe(status);
      expect(fetch).not.toHaveBeenCalled();
    });

    it('never authorizes a transition when the REST transport is unavailable', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('offline-only transport failure'));
      const { response, ok, gate } = await submit();
      expect(response.status).toBe(409);
      expect(ok).toBe(false);
      expect(gate).toMatchObject({ decision: 'HOLD', reason_code: 'GATE_HOLD_RUNTIME_UNAVAILABLE', receipt: { retained: false } });
      expect(await redis.keys('er:gate:v2:receipt:*')).toEqual([]);
    });

    it('returns one identical retained PASS for concurrent authenticated retries', async () => {
      const results = await Promise.all([submit(), submit(), submit()]);
      for (const result of results) {
        expect(result.response.status).toBe(200);
        expect(result.gate).toEqual(results[0].gate);
      }
      expect(await redis.keys('er:gate:v2:receipt:*')).toHaveLength(1);
      expect(await redis.keys('er:gate:v2:transition:*')).toHaveLength(1);
      expect(await redis.keys('er:gate:v2:nonce:*')).toHaveLength(2);
    });

    it('allows only one conflicting authenticated acceptance for the same transition', async () => {
      const results = await Promise.all([submit(), submit(input({ approval: attestation('approval', { nonce: 'other-approval' }), evidence: attestation('deployment', { nonce: 'other-evidence' }) }))]);
      expect(results.map((result) => result.response.status).sort()).toEqual([200, 409]);
      const rejected = results.find((result) => !result.ok)!;
      expect(rejected.gate).toMatchObject({ decision: 'REJECT', reason_code: 'GATE_REJECT_REPLAY', receipt: { retained: false } });
      expect(await redis.keys('er:gate:v2:receipt:*')).toHaveLength(1);
      expect(await redis.keys('er:gate:v2:nonce:*')).toHaveLength(2);
    });

    it('does not execute the legacy deployment even with a valid envelope and retained PASS', async () => {
      const accepted = await submit();
      expect(accepted.response.status).toBe(200);
      const response = await deploymentPreflight(request({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag', ...input(), gate: accepted.gate }, { path: '/api/workflows/studio-deploy' }));
      expect(response.status).toBe(409);
      expect(response.headers.get('cache-control')).toBe('no-store');
      const payload = await response.json();
      expect(payload).toMatchObject({ ok: false, gate: { decision: 'HOLD', reason_code: 'GATE_HOLD_MISSING_EVIDENCE', receipt: { retained: true, artifact_hash: null } } });
      expect(payload).not.toHaveProperty('runId');
      expect(start).not.toHaveBeenCalled();
      expect(JSON.parse((await redis.get(receiptKey(accepted.gate)))!)).toEqual(accepted.gate);
      expect(await redis.keys('er:gate:v2:transition:*')).toHaveLength(1);
    });
  });

  it('bounds a legacy permanent non-PASS receipt when it is next re-evaluated', async () => {
    const proposal = pending('legacy-hold');
    const held = await evaluate(proposal);
    await redis.persist(receiptKey(held));
    await redis.del(await quotaKey());
    expect(await redis.ttl(receiptKey(held))).toBe(-1);
    expect((await evaluate(proposal, now + 1000)).receipt.retained).toBe(true);
    expect(await redis.ttl(receiptKey(held))).toBeGreaterThan(0);
    expect(await redis.ttl(receiptKey(held))).toBeLessThanOrEqual(86400);
    expect(await redis.zCard(await quotaKey())).toBe(1);
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
    expect(args.slice(-3)).toEqual([rawPolicy, 86400, 100]);
    expect(args).toContain(`er:gate:v2:pending:${hashCanonical(binding.subject)}`);
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

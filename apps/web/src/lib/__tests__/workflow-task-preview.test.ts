import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createHmac } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { issueWorkflowTaskPreview, verifyWorkflowTaskPreview } from '../workflow-task-preview';
import type { AgentAction } from '../action-lifecycle';

const secret = 'isolated-preview-unit-secret';
const action: AgentAction = { tool: 'create_workflow_task', input: { title: 'Inspect source', description: 'Inspect the provided source', category: 'research', priority: 'high' }, status: 'pending' };
const owner = JSON.stringify(['github', 'alice']);

describe('immutable task preview receipt', () => {
  beforeEach(() => vi.stubEnv('NEXTAUTH_SECRET', secret));
  afterEach(() => vi.unstubAllEnvs());

  it('round-trips server-issued proofs and distinguishes separately issued runs', () => {
    const proof = issueWorkflowTaskPreview(owner, [action]);
    expect(verifyWorkflowTaskPreview(proof.confirmationToken, owner, proof.jobId, [action])).toBe(true);
    expect(issueWorkflowTaskPreview(owner, [action]).jobId).not.toBe(proof.jobId);
    expect(verifyWorkflowTaskPreview(proof.confirmationToken, JSON.stringify(['google', 'alice']), proof.jobId, [action])).toBe(false);
  });

  it('verifies the original receipt in a fresh process without a plan cache', () => {
    const proof = issueWorkflowTaskPreview(owner, [action]);
    const moduleUrl = new URL('../workflow-task-preview.ts', import.meta.url).href;
    const source = `import { verifyWorkflowTaskPreview } from ${JSON.stringify(moduleUrl)}; const [token, owner, jobId, actions] = JSON.parse(process.argv[1]); process.stdout.write(String(verifyWorkflowTaskPreview(token, owner, jobId, actions)));`;
    const output = execFileSync(process.execPath, ['--conditions=react-server', '--input-type=module', '-e', source,
      JSON.stringify([proof.confirmationToken, owner, proof.jobId, [action]])], {
      encoding: 'utf8', env: { PATH: process.env.PATH, NODE_ENV: 'test', NEXTAUTH_SECRET: secret },
    });
    expect(output).toBe('true');
  });

  it('binds semantic inputs while allowing display-summary changes', () => {
    const proof = issueWorkflowTaskPreview(owner, [{ ...action, result: 'Original display text', isError: false }]);
    expect(verifyWorkflowTaskPreview(proof.confirmationToken, owner, proof.jobId, [{ ...action, result: 'Display text only' }])).toBe(true);
    expect(verifyWorkflowTaskPreview(proof.confirmationToken, owner, proof.jobId, [{ ...action, data: { id: 'forged-receipt' } }])).toBe(false);
  });

  it.each([null, undefined, '', 'forged', 'a'.repeat(1025), 'e30=.' + 'a'.repeat(64)])('rejects malformed proof %s', token => {
    expect(verifyWorkflowTaskPreview(token, owner, 'preview_fake', [action])).toBe(false);
  });

  it('rejects altered signed payload bytes even with an unchanged signature', () => {
    const proof = issueWorkflowTaskPreview(owner, [action]);
    const [payload, signature] = proof.confirmationToken.split('.');
    const data = JSON.parse(Buffer.from(payload, 'base64url').toString());
    data[2] = 'preview_' + 'a'.repeat(36);
    const altered = Buffer.from(JSON.stringify(data)).toString('base64url');
    expect(verifyWorkflowTaskPreview(`${altered}.${signature}`, owner, data[2], [action])).toBe(false);
  });

  it.each(['version', 'shape', 'time'])('rejects invalid %s in an otherwise correctly signed payload', kind => {
    const proof = issueWorkflowTaskPreview(owner, [action]);
    const data = JSON.parse(Buffer.from(proof.confirmationToken.split('.')[0], 'base64url').toString());
    if (kind === 'version') data[0] = 2;
    if (kind === 'shape') data.push('unexpected');
    if (kind === 'time') data[4] = 'yesterday';
    const payload = Buffer.from(JSON.stringify(data)).toString('base64url');
    const signature = createHmac('sha256', secret).update('eventrelay.workflow-task-preview.v1\n' + payload).digest('hex');
    expect(verifyWorkflowTaskPreview(`${payload}.${signature}`, owner, proof.jobId, [action])).toBe(false);
  });

  it('fails closed when signing configuration is missing or rotated', () => {
    const proof = issueWorkflowTaskPreview(owner, [action]);
    vi.stubEnv('NEXTAUTH_SECRET', '');
    expect(() => issueWorkflowTaskPreview(owner, [action])).toThrow();
    expect(verifyWorkflowTaskPreview(proof.confirmationToken, owner, proof.jobId, [action])).toBe(false);
    vi.stubEnv('NEXTAUTH_SECRET', 'rotated-secret');
    expect(verifyWorkflowTaskPreview(proof.confirmationToken, owner, proof.jobId, [action])).toBe(false);
  });

  it.each([
    [], [action, action], [{ ...action, status: 'fulfilled' }], [{ ...action, isError: true }],
    [{ ...action, result: {} }], [{ ...action, approved: true }], [{ ...action, input: [] }],
    [{ ...action, input: { value: Infinity } }], [{ ...action, input: { value: undefined } }],
    [{ ...action, input: { value: new Date() } }], [{ ...action, input: { value: Array(2) } }],
    [{ ...action, input: { value: 'x'.repeat(512 * 1024) } }],
  ].map(actions => ({ actions })))('refuses invalid preview actions %#', ({ actions }) => {
    expect(() => issueWorkflowTaskPreview(owner, actions as AgentAction[])).toThrow();
  });

  it('rejects excessive nesting without recursive overflow', () => {
    let input: Record<string, unknown> = { title: 'nested' };
    for (let i = 0; i < 20; i++) input = { nested: input };
    expect(() => issueWorkflowTaskPreview(owner, [{ ...action, input }])).toThrow();
  });

  it('handles JSON prototype-named keys without mutating prototypes', () => {
    const input = JSON.parse('{"__proto__":{"polluted":true},"title":"source"}');
    const plan = [{ ...action, input }];
    const proof = issueWorkflowTaskPreview(owner, plan);
    expect(verifyWorkflowTaskPreview(proof.confirmationToken, owner, proof.jobId, plan)).toBe(true);
    expect(Object.hasOwn(Object.prototype, 'polluted')).toBe(false);
  });
});

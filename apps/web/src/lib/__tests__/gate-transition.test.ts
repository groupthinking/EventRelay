import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  GATE_RECEIPT_VERSION,
  assessZeroSim,
  canonicalGateJson,
  evaluateStudioDeployTransition,
  evaluateTransition,
  hashCanonical,
  type GateTransitionRequest,
} from '@/lib/gate-transition';

const ISSUED_AT = '2026-09-08T18:00:00.000Z';

function baseRequest(
  overrides: Partial<GateTransitionRequest> = {},
): GateTransitionRequest {
  return {
    transitionId: 'tr_auJzb1D-fag',
    kind: 'studio.deploy',
    fromState: 'proposed',
    toState: 'live',
    evidenceRefs: [
      {
        kind: 'live_url',
        id: 'https://uvai-demo.vercel.app',
        uri: 'https://uvai-demo.vercel.app',
      },
    ],
    authority: { actor: 'signed-in', claim: 'session' },
    zeroSim: { verdict: 'real', reason_code: 'ZERO_SIM_REAL' },
    issuedAt: ISSUED_AT,
    ...overrides,
  };
}

describe('G.A.T.E. transition contract', () => {
  it('PASS when Zero-Sim is real, authority is known, and live evidence is verified', () => {
    const result = evaluateTransition(baseRequest());
    expect(result.decision).toBe('PASS');
    expect(result.reason_code).toBe('GATE_PASS');
    expect(result.reason).toMatch(/permit/i);
    expect(result.receipt.version).toBe(GATE_RECEIPT_VERSION);
    expect(result.receipt.decision).toBe('PASS');
    expect(result.receipt.receipt_hash).toMatch(/^[a-f0-9]{64}$/);
  });

  it('HOLD when required evidence is missing (not REJECT)', () => {
    const result = evaluateTransition(
      baseRequest({
        toState: 'proposed',
        evidenceRefs: [],
        zeroSim: undefined,
      }),
    );
    expect(result.decision).toBe('HOLD');
    expect(result.reason_code).toBe('GATE_HOLD_MISSING_EVIDENCE');
    expect(result.receipt.decision).toBe('HOLD');
  });

  it('HOLD when evidence is present but Zero-Sim is unverified (weak, not invented)', () => {
    const result = evaluateTransition(
      baseRequest({
        kind: 'evidence.cite',
        toState: 'proposed',
        evidenceRefs: [{ kind: 'run_id', id: 'wrun_1' }],
        zeroSim: { verdict: 'unverified', reason_code: 'ZERO_SIM_UNVERIFIED' },
      }),
    );
    expect(result.decision).toBe('HOLD');
    expect(result.reason_code).toBe('GATE_HOLD_WEAK_EVIDENCE');
  });

  it('REJECT when Zero-Sim marks evidence unreal', () => {
    const result = evaluateTransition(
      baseRequest({
        evidenceRefs: [{ kind: 'content_sha256', hash: 'not-a-hash' }],
        zeroSim: { verdict: 'unreal', reason_code: 'ZERO_SIM_UNREAL' },
      }),
    );
    expect(result.decision).toBe('REJECT');
    expect(result.reason_code).toBe('GATE_REJECT_UNREAL_EVIDENCE');
  });

  it('REJECT when the caller claims live with a malformed live URL', () => {
    const result = evaluateTransition(
      baseRequest({
        toState: 'live',
        evidenceRefs: [{ kind: 'live_url', uri: 'https://' }],
        zeroSim: undefined,
      }),
    );
    expect(result.decision).toBe('REJECT');
    expect(result.reason_code).toBe('GATE_REJECT_CLAIM_MISMATCH');
  });

  it('ESCALATE when authority actor is unknown', () => {
    const result = evaluateTransition(
      baseRequest({
        authority: { actor: 'mystery-role' },
      }),
    );
    expect(result.decision).toBe('ESCALATE');
    expect(result.reason_code).toBe('GATE_ESCALATE_AUTHORITY_UNKNOWN');
  });

  it('does not invent a Zero-Sim real verdict from empty refs', () => {
    const assessed = assessZeroSim({ evidenceRefs: [] });
    expect(assessed.verdict).toBe('unverified');
    expect(assessed.reason_code).toBe('ZERO_SIM_MISSING_EVIDENCE');
  });

  it('emits a versioned receipt whose hash matches canonical JSON without the hash field', () => {
    const result = evaluateTransition(baseRequest());
    const { receipt_hash, ...body } = result.receipt;
    const expected = createHash('sha256')
      .update(canonicalGateJson(body))
      .digest('hex');
    expect(receipt_hash).toBe(expected);
    expect(hashCanonical(canonicalGateJson(body))).toBe(expected);
  });
});

describe('evaluateStudioDeployTransition', () => {
  it('PASS only for a verified https live URL with hostname', () => {
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_live',
      runId: 'wrun_live',
      liveUrl: 'https://example.vercel.app',
      runStatus: 'completed',
      kind: 'live',
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('PASS');
    expect(result.reason_code).toBe('GATE_PASS');
  });

  it('HOLD when workflow completed without a live receipt (no Deploy completed claim)', () => {
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_done',
      runId: 'wrun_done',
      runStatus: 'completed',
      kind: 'handoff',
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('HOLD');
    expect(result.reason_code).toBe('GATE_HOLD_MISSING_EVIDENCE');
    expect(result.reason.toLowerCase()).not.toMatch(/deploy completed/);
  });

  it('REJECT a presented live URL that fails the hostname bar', () => {
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_fake',
      runId: 'wrun_fake',
      liveUrl: 'https://',
      runStatus: 'completed',
      kind: 'live',
      authority: { actor: 'signed-in' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('REJECT');
    expect(result.reason_code).toBe('GATE_REJECT_CLAIM_MISMATCH');
  });

  it('ESCALATE when Studio deploy authority is not a known actor', () => {
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_esc',
      runId: 'wrun_esc',
      liveUrl: 'https://example.vercel.app',
      runStatus: 'completed',
      authority: { actor: 'contractor-bot' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('ESCALATE');
    expect(result.reason_code).toBe('GATE_ESCALATE_AUTHORITY_UNKNOWN');
  });
});

describe('Studio deploy call site', () => {
  it('runs G.A.T.E. before claiming a live deploy receipt', () => {
    const studio = readFileSync(
      join(process.cwd(), 'src/components/OneLoopStudio.tsx'),
      'utf8',
    );
    const deployFn = studio.slice(studio.indexOf('const deploy = async'));
    expect(deployFn).toContain('evaluateStudioDeployTransition');
    const gateIdx = deployFn.indexOf('evaluateStudioDeployTransition');
    const claimIdx = deployFn.indexOf('studioDeployOutcomeMessage');
    expect(gateIdx).toBeGreaterThan(-1);
    expect(claimIdx).toBeGreaterThan(gateIdx);
    expect(studio).not.toContain('Deploy ${polled.runStatus');
  });
});

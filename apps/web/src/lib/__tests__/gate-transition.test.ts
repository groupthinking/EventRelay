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
  studioDeployAttemptTransitionId,
  studioGateReceiptView,
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

    const forcedReal = assessZeroSim({
      result: { verdict: 'real', reason_code: 'ZERO_SIM_REAL' },
      evidenceRefs: [],
    });
    expect(forcedReal.verdict).toBe('unverified');
    expect(forcedReal.reason_code).toBe('ZERO_SIM_MISSING_EVIDENCE');
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

  it('HOLD when BACKEND_URL is missing — cites backend reason, no live claim', () => {
    const backendReason = 'BACKEND_URL is not configured';
    const result = evaluateStudioDeployTransition({
      transitionId: 'attempt:auJzb1D-fag',
      authority: { actor: 'anonymous' },
      kind: 'handoff',
      backendReason,
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('HOLD');
    expect(result.reason_code).toBe('GATE_HOLD_MISSING_EVIDENCE');
    expect(result.reason.toLowerCase()).not.toMatch(/deploy completed/);
    expect(result.receipt.evidence_refs.some((ref) => ref.id === backendReason)).toBe(true);

    const view = studioGateReceiptView(result, { backendReason });
    expect(view.decision).toBe('HOLD');
    expect(view.reason).toContain(backendReason);
    expect(view.receiptId).toBe('er:gate:v1:attempt:auJzb1D-fag');
    expect(view.receiptHash).toBe(result.receipt.receipt_hash);
    expect(view.receiptHash).toMatch(/^[a-f0-9]{64}$/);
    expect(view.version).toBe(GATE_RECEIPT_VERSION);
  });

  it('HOLD when the workflow return is missing a live URL — no Deploy completed claim', () => {
    const backendReason = 'Backend job finished with no verified live URL';
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_01M2A8RXT1HS8NPW70HV6AA0YV',
      runId: 'wrun_01M2A8RXT1HS8NPW70HV6AA0YV',
      runStatus: 'completed',
      kind: 'job',
      backendReason,
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('HOLD');
    expect(result.reason_code).toBe('GATE_HOLD_MISSING_EVIDENCE');
    expect(result.reason.toLowerCase()).not.toMatch(/deploy completed/);
    const view = studioGateReceiptView(result, { backendReason });
    expect(view.reason).toContain(backendReason);
    expect(view.reason).not.toMatch(/Failed to read workflow return value/);
    expect(view.reason).not.toMatch(/Failed to read workflow run/);
    expect(view.receiptId).toBe('er:gate:v1:wrun_01M2A8RXT1HS8NPW70HV6AA0YV');
  });

  it('HOLD while deploy is still running cites the job, not UNKNOWN checks', () => {
    const backendReason = 'Deploy job job_96f498640b still transcribing';
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
      runId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
      jobId: 'job_96f498640b',
      runStatus: 'running',
      kind: 'job',
      backendReason,
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('HOLD');
    expect(result.reason.toLowerCase()).not.toMatch(/deploy completed/);
    const view = studioGateReceiptView(result, { backendReason });
    expect(view.reason).toContain(backendReason);
    expect(view.reason).not.toMatch(/UNKNOWN checks are not a live URL/);
    expect(view.reason).not.toMatch(/Failed to read workflow run/);
    expect(view.reason).not.toMatch(/Failed to read workflow return value/);
    expect(view.reason).not.toMatch(/BACKEND_URL is not configured/);
    expect(view.receiptId).toBe('er:gate:v1:wrun_01M2ABB1NJ5TFZ153CTRNTPNW9');
  });

  it('HOLD after ready-transcript reuse miss is not the YouTube bot string', () => {
    const backendReason =
      'Ready transcript was not reused. Deploy must not re-fetch YouTube. No verified deploy receipt.';
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_01M2ACYVYXBHM0YVMX1WHMQ1PJ',
      runId: 'wrun_01M2ACYVYXBHM0YVMX1WHMQ1PJ',
      runStatus: 'failed',
      kind: 'handoff',
      backendReason,
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('HOLD');
    expect(result.reason.toLowerCase()).not.toMatch(/deploy completed/);
    const view = studioGateReceiptView(result, { backendReason });
    expect(view.reason).toContain(backendReason);
    expect(view.reason).not.toMatch(/Sign in to confirm you.?re not a bot/i);
    expect(view.reason).not.toMatch(/UNKNOWN checks are not a live URL/);
    expect(view.reason).not.toMatch(/Failed to read workflow run/);
    expect(view.reason).not.toMatch(/Failed to read workflow return value/);
    expect(view.reason).not.toMatch(/BACKEND_URL is not configured/);
    expect(view.receiptId).toBe('er:gate:v1:wrun_01M2ACYVYXBHM0YVMX1WHMQ1PJ');
  });

  it('HOLD after #1875 process re-hit is not the YouTube bot wall', () => {
    const backendReason =
      'Ready transcript was not reused. Deploy must not re-fetch YouTube. No verified deploy receipt.';
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_01M2AF8WD3G4VCB63KEBX311HV',
      runId: 'wrun_01M2AF8WD3G4VCB63KEBX311HV',
      runStatus: 'failed',
      kind: 'handoff',
      backendReason,
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('HOLD');
    expect(result.reason.toLowerCase()).not.toMatch(/deploy completed/);
    const view = studioGateReceiptView(result, { backendReason });
    expect(view.reason).not.toMatch(/Sign in to confirm you.?re not a bot/i);
    expect(view.reason).not.toMatch(/Backend kickoff returned HTTP 524/i);
    expect(view.reason).not.toMatch(/UNKNOWN checks are not a live URL/);
    expect(view.reason).not.toMatch(/Failed to read workflow run/);
    expect(view.reason).not.toMatch(/Failed to read workflow return value/);
    expect(view.reason).not.toMatch(/BACKEND_URL is not configured/);
    expect(view.receiptId).toBe('er:gate:v1:wrun_01M2AF8WD3G4VCB63KEBX311HV');
  });

  it('HOLD after a 524 miss is not Backend kickoff returned HTTP 524', () => {
    const backendReason = 'Deploy job job_01M2AE6Z9Q2KZRBA0Z0Q455B0S still pending';
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_01M2AE6Z9Q2KZRBA0Z0Q455B0S',
      runId: 'wrun_01M2AE6Z9Q2KZRBA0Z0Q455B0S',
      jobId: 'job_01M2AE6Z9Q2KZRBA0Z0Q455B0S',
      runStatus: 'running',
      kind: 'job',
      backendReason,
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('HOLD');
    expect(result.reason.toLowerCase()).not.toMatch(/deploy completed/);
    const view = studioGateReceiptView(result, { backendReason });
    expect(view.reason).not.toMatch(/Backend kickoff returned HTTP 524/i);
    expect(view.reason).not.toMatch(/Sign in to confirm you.?re not a bot/i);
    expect(view.reason).not.toMatch(/UNKNOWN checks are not a live URL/);
    expect(view.reason).not.toMatch(/Failed to read workflow run/);
    expect(view.reason).not.toMatch(/Failed to read workflow return value/);
    expect(view.reason).not.toMatch(/BACKEND_URL is not configured/);
    expect(view.receiptId).toBe('er:gate:v1:wrun_01M2AE6Z9Q2KZRBA0Z0Q455B0S');
  });

  it('HOLD after origin reused the transcript is not the reuse-miss copy', () => {
    const backendReason =
      'Studio transcript was reused. Origin video-to-software returned no verified live URL.';
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_01M2B05JJZNTD7MKANV0RN0J28',
      runId: 'wrun_01M2B05JJZNTD7MKANV0RN0J28',
      runStatus: 'failed',
      kind: 'handoff',
      backendReason,
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('HOLD');
    expect(result.reason.toLowerCase()).not.toMatch(/deploy completed/);
    const view = studioGateReceiptView(result, { backendReason });
    expect(view.reason).toContain(backendReason);
    expect(view.reason).not.toMatch(/Ready transcript was not reused/i);
    expect(view.reason).not.toMatch(/aborted due to timeout/i);
    expect(view.reason).not.toMatch(/Backend kickoff returned HTTP 524/i);
    expect(view.reason).not.toMatch(/Sign in to confirm you.?re not a bot/i);
    expect(view.reason).not.toMatch(/UNKNOWN checks are not a live URL/);
    expect(view.reason).not.toMatch(/Failed to read workflow run/);
    expect(view.reason).not.toMatch(/Failed to read workflow return value/);
    expect(view.reason).not.toMatch(/BACKEND_URL is not configured/);
    expect(view.receiptId).toBe('er:gate:v1:wrun_01M2B05JJZNTD7MKANV0RN0J28');
  });

  it('HOLD after timeout abort is not the raw AbortSignal message', () => {
    const backendReason =
      'Deploy kickoff timed out before a verified live URL. Waiting for the origin job — not aborting the attempt.';
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_01M2AKRAVZ0SEBM670BGXEMCQZ',
      runId: 'wrun_01M2AKRAVZ0SEBM670BGXEMCQZ',
      runStatus: 'running',
      kind: 'job',
      jobId: 'job_01M2AKRAVZ0SEBM670BGXEMCQZ',
      backendReason,
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('HOLD');
    expect(result.reason.toLowerCase()).not.toMatch(/deploy completed/);
    const view = studioGateReceiptView(result, { backendReason });
    expect(view.reason).not.toMatch(/aborted due to timeout/i);
    expect(view.reason).not.toMatch(/Backend kickoff returned HTTP 524/i);
    expect(view.reason).not.toMatch(/Sign in to confirm you.?re not a bot/i);
    expect(view.reason).not.toMatch(/UNKNOWN checks are not a live URL/);
    expect(view.reason).not.toMatch(/Failed to read workflow run/);
    expect(view.reason).not.toMatch(/Failed to read workflow return value/);
    expect(view.reason).not.toMatch(/BACKEND_URL is not configured/);
    expect(view.receiptId).toBe('er:gate:v1:wrun_01M2AKRAVZ0SEBM670BGXEMCQZ');
  });

  it('PASS when a verified live URL arrives after a timeout abort residual', () => {
    const result = evaluateStudioDeployTransition({
      transitionId: 'wrun_01M2AKRAVZ0SEBM670BGXEMCQZ',
      runId: 'wrun_01M2AKRAVZ0SEBM670BGXEMCQZ',
      jobId: 'job_01M2AKRAVZ0SEBM670BGXEMCQZ',
      liveUrl: 'https://xy.vercel.app',
      runStatus: 'completed',
      kind: 'live',
      authority: { actor: 'anonymous' },
      issuedAt: ISSUED_AT,
    });
    expect(result.decision).toBe('PASS');
    expect(result.receipt.id).toBe('er:gate:v1:wrun_01M2AKRAVZ0SEBM670BGXEMCQZ');
  });
});

describe('studioGateReceiptView', () => {
  it('exposes PASS | HOLD | REJECT | ESCALATE plus receipt id/hash for the Studio chip', () => {
    const pass = studioGateReceiptView(
      evaluateStudioDeployTransition({
        transitionId: 'wrun_live',
        liveUrl: 'https://example.vercel.app',
        authority: { actor: 'anonymous' },
        issuedAt: ISSUED_AT,
      }),
    );
    expect(pass.decision).toBe('PASS');
    expect(pass.reason.length).toBeGreaterThan(0);
    expect(pass.receiptId).toBe('er:gate:v1:wrun_live');
    expect(pass.receiptHash).toMatch(/^[a-f0-9]{64}$/);

    const reject = studioGateReceiptView(
      evaluateStudioDeployTransition({
        transitionId: 'wrun_fake',
        liveUrl: 'https://',
        authority: { actor: 'anonymous' },
        issuedAt: ISSUED_AT,
      }),
    );
    expect(reject.decision).toBe('REJECT');

    const escalate = studioGateReceiptView(
      evaluateStudioDeployTransition({
        transitionId: 'wrun_esc',
        liveUrl: 'https://example.vercel.app',
        authority: { actor: 'contractor-bot' },
        issuedAt: ISSUED_AT,
      }),
    );
    expect(escalate.decision).toBe('ESCALATE');
  });

  it('uses attempt:{videoId} when the deploy backend never issued a runId', () => {
    expect(studioDeployAttemptTransitionId({ videoId: 'auJzb1D-fag' })).toBe(
      'attempt:auJzb1D-fag',
    );
    expect(studioDeployAttemptTransitionId({ runId: 'wrun_1', videoId: 'auJzb1D-fag' })).toBe(
      'wrun_1',
    );
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
    expect(studio).toContain('studioGateReceiptView');
    expect(studio).toContain('data-testid="studio-gate-receipt"');
    expect(studio).toContain('data-testid="studio-gate-decision"');
    expect(studio).toContain('data-testid="studio-gate-reason"');
    expect(studio).toContain('data-testid="studio-gate-receipt-hash"');
    expect(studio).toContain('data-testid="studio-gate-live-url"');
    expect(studio).toContain('scopedDeployReceipt');
    const failIdx = deployFn.indexOf('if (!started.ok || !started.runId)');
    expect(failIdx).toBeGreaterThan(-1);
    const failBlock = deployFn.slice(failIdx, deployFn.indexOf('return;', failIdx));
    expect(failBlock).toContain('evaluateStudioDeployTransition');
    expect(failBlock).toContain('studioGateReceiptView');
  });
});

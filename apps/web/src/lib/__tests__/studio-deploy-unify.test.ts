import { describe, expect, it } from 'vitest';
import { GATE_RECEIPT_VERSION, type StudioGateReceiptView } from '@/lib/gate-transition';
import {
  studioGateDecisionChipClass,
  studioGateLiveUrlForDecision,
  studioGateReceiptClaimsLive,
  studioGateVersionNote,
} from '@/lib/studio-deploy-unify';

const FIXTURE_URL = 'https://www.youtube.com/watch?v=auJzb1D-fag';

function receipt(decision: StudioGateReceiptView['decision']): StudioGateReceiptView {
  return {
    decision,
    reason: `${decision} for ${FIXTURE_URL}`,
    reason_code: `GATE_${decision}`,
    receiptId: 'er:gate:test',
    receiptHash: 'a'.repeat(64),
    version: GATE_RECEIPT_VERSION,
  };
}

describe('studio-deploy-unify (Cut 5)', () => {
  it('PASS surfaces a verified https live URL', () => {
    expect(studioGateLiveUrlForDecision('PASS', 'https://demo.vercel.app')).toBe(
      'https://demo.vercel.app',
    );
    expect(studioGateReceiptClaimsLive(receipt('PASS'))).toBe(true);
  });

  it.each(['HOLD', 'REJECT', 'ESCALATE'] as const)(
    '%s never claims live even when a URL string is present',
    (decision) => {
      expect(studioGateLiveUrlForDecision(decision, 'https://demo.vercel.app')).toBeNull();
      expect(studioGateReceiptClaimsLive(receipt(decision))).toBe(false);
    },
  );

  it('rejects non-https and incomplete URLs on PASS', () => {
    expect(studioGateLiveUrlForDecision('PASS', 'http://demo.vercel.app')).toBeNull();
    expect(studioGateLiveUrlForDecision('PASS', 'https://')).toBeNull();
    expect(studioGateLiveUrlForDecision('PASS', null)).toBeNull();
  });

  it('labels v2 vs local diagnostic distinctly', () => {
    expect(studioGateVersionNote('eventrelay.gate-receipt.v2')).toMatch(/Server decision/i);
    expect(studioGateVersionNote(GATE_RECEIPT_VERSION)).toMatch(/Local diagnostic/i);
  });

  it('maps every decision to a chip class (exhaustive)', () => {
    expect(studioGateDecisionChipClass('PASS')).toContain('pass');
    expect(studioGateDecisionChipClass('HOLD')).toContain('hold');
    expect(studioGateDecisionChipClass('REJECT')).toContain('reject');
    expect(studioGateDecisionChipClass('ESCALATE')).toContain('escalate');
  });
});

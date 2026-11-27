import { describe, expect, it } from 'vitest';
import { GATE_RECEIPT_VERSION } from '@/lib/gate-transition';
import {
  studioGateDecisionChipClass,
  studioGateLiveUrlForDecision,
  studioGateVersionNote,
} from '@/lib/studio-deploy-unify';

describe('studio-deploy-unify', () => {
  it('PASS surfaces a verified https live URL', () => {
    expect(studioGateLiveUrlForDecision('PASS', 'https://demo.vercel.app')).toBe(
      'https://demo.vercel.app',
    );
  });

  it.each(['HOLD', 'REJECT', 'ESCALATE'] as const)(
    '%s never claims live even when a URL string is present',
    (decision) => {
      expect(studioGateLiveUrlForDecision(decision, 'https://demo.vercel.app')).toBeNull();
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

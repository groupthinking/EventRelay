import type { GateDecision, StudioGateReceiptView } from '@/lib/gate-transition';
import { studioVerifiedLiveUrl } from '@/lib/studio-pipeline-status';

/** Live URL is only eligible when the gate decision is PASS. */
export function studioGateLiveUrlForDecision(
  decision: GateDecision | null | undefined,
  liveUrl?: string | null,
): string | null {
  if (decision !== 'PASS') return null;
  return studioVerifiedLiveUrl(liveUrl);
}

export function studioGateDecisionChipClass(decision: GateDecision): string {
  switch (decision) {
    case 'PASS':
      return 'studio-gate-chip studio-gate-chip--pass';
    case 'HOLD':
      return 'studio-gate-chip studio-gate-chip--hold';
    case 'REJECT':
      return 'studio-gate-chip studio-gate-chip--reject';
    case 'ESCALATE':
      return 'studio-gate-chip studio-gate-chip--escalate';
    default: {
      const _exhaustive: never = decision;
      return _exhaustive;
    }
  }
}

export function studioGateVersionNote(version: StudioGateReceiptView['version']): string {
  return version === 'eventrelay.gate-receipt.v2'
    ? 'Server decision. Later stages require separate Loop approval.'
    : 'Local diagnostic only — not an authorization receipt.';
}

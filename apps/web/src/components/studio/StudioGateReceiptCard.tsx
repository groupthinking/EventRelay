'use client';

import { clsx } from 'clsx';
import type { StudioGateReceiptView } from '@/lib/gate-transition';
import {
  studioGateDecisionChipClass,
  studioGateLiveUrlForDecision,
  studioGateVersionNote,
} from '@/lib/studio-deploy-unify';

export type StudioGateReceiptCardProps = {
  receipt: StudioGateReceiptView;
  /** Candidate live URL — only rendered when decision is PASS and URL verifies. */
  liveUrl?: string | null;
  className?: string;
};

/** https link renders only when the decision is PASS and the URL verifies. */
export default function StudioGateReceiptCard({
  receipt,
  liveUrl,
  className,
}: StudioGateReceiptCardProps) {
  const verifiedLive = studioGateLiveUrlForDecision(receipt.decision, liveUrl);

  return (
    <div
      data-testid="studio-gate-receipt"
      role="status"
      className={clsx('studio-gate-receipt', className)}
    >
      <span
        data-testid="studio-gate-decision"
        className={clsx(
          'inline-flex rounded-full border px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em]',
          studioGateDecisionChipClass(receipt.decision),
        )}
      >
        {receipt.decision}
      </span>
      <div className="studio-gate-receipt__body min-w-0 flex-1">
        <p data-testid="studio-gate-reason" className="text-sm text-[var(--uvai-ink)]">
          {receipt.reason}
        </p>
        <p className="text-sm text-[var(--uvai-ink-soft)]">{studioGateVersionNote(receipt.version)}</p>
        <p className="mt-1 font-mono text-[11px] text-[var(--uvai-ink-faint)]">
          <span data-testid="studio-gate-receipt-id">{receipt.receiptId}</span>
          {' · '}
          <span data-testid="studio-gate-receipt-hash">{receipt.receiptHash}</span>
          {' · '}
          {receipt.version}
        </p>
        {receipt.transitionId ? (
          <p className="break-all text-sm text-[var(--uvai-ink-faint)]">
            Transition: {receipt.transitionId}
            {' · '}
            {receipt.retained ? 'Receipt retained' : 'Receipt not retained'}
          </p>
        ) : null}
        {verifiedLive ? (
          <p className="mt-1">
            <a
              data-testid="studio-gate-live-url"
              href={verifiedLive}
              target="_blank"
              rel="noopener noreferrer"
              className="break-all text-sm text-[var(--uvai-accent-ink)] underline"
            >
              {verifiedLive}
            </a>
          </p>
        ) : null}
      </div>
    </div>
  );
}

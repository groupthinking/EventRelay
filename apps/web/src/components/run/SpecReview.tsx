'use client';

import { useState } from 'react';
import { LoaderCircle, ThumbsDown, ThumbsUp } from 'lucide-react';
import type { RunApprovalView, RunSpecView } from '@/hooks/use-run';

/**
 * The human gate.
 *
 * The workflow is suspended until this returns a decision, so the requirements
 * and plan are shown in full rather than summarised — the approval is recorded
 * against this exact spec version, and a later re-plan creates a new version
 * instead of changing what was signed.
 */

export interface SpecReviewProps {
  spec: RunSpecView | null;
  approval: RunApprovalView | null;
  awaitingApproval: boolean;
  submitting: boolean;
  onDecide: (approved: boolean, note?: string) => Promise<void>;
}

export default function SpecReview({
  spec,
  approval,
  awaitingApproval,
  submitting,
  onDecide,
}: SpecReviewProps) {
  const [note, setNote] = useState('');

  if (!spec) {
    return (
      <p className="text-sm" style={{ color: 'var(--evidence-muted)' }}>
        Requirements and the execution plan appear here once the run finishes planning.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <span
          className="rounded-full border px-3 py-1 font-mono text-xs"
          style={{ borderColor: 'var(--evidence-border)', color: 'var(--evidence-muted)' }}
        >
          spec v{spec.version}
        </span>
        {approval && (
          <span
            className="rounded-full px-3 py-1 text-xs font-medium"
            style={{
              background:
                approval.decision === 'approved'
                  ? 'rgba(54,189,161,0.12)'
                  : 'rgba(239,68,68,0.12)',
              color:
                approval.decision === 'approved' ? 'var(--evidence-accent)' : '#fca5a5',
            }}
          >
            {approval.decision} by {approval.decidedBy}
          </span>
        )}
      </div>

      <Section title="Requirements" body={textOf(spec.requirements)} />
      <Section title="Execution plan" body={textOf(spec.plan)} />

      {awaitingApproval && (
        <div
          className="flex flex-col gap-3 rounded-lg border p-4"
          style={{
            borderColor: 'var(--evidence-accent-strong)',
            background: 'rgba(54,189,161,0.06)',
          }}
        >
          <p className="text-sm" style={{ color: 'var(--evidence-text)' }}>
            The run is suspended here. Nothing is built until you approve this spec.
          </p>
          <label className="flex flex-col gap-2">
            <span className="text-xs" style={{ color: 'var(--evidence-muted)' }}>
              Note (recorded with your decision)
            </span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={2}
              className="input text-sm"
              placeholder="Optional context for the audit trail"
            />
          </label>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={submitting}
              onClick={() => void onDecide(true, note.trim() || undefined)}
              className="evidence-primary-button inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {submitting ? (
                <LoaderCircle size={15} className="animate-spin" aria-hidden="true" />
              ) : (
                <ThumbsUp size={15} aria-hidden="true" />
              )}
              Approve and build
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={() => void onDecide(false, note.trim() || undefined)}
              className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold disabled:opacity-50"
              style={{ borderColor: 'rgba(239,68,68,0.4)', color: '#fca5a5' }}
            >
              <ThumbsDown size={15} aria-hidden="true" />
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <section className="flex flex-col gap-2">
      <h3
        className="text-xs font-semibold uppercase tracking-widest"
        style={{ color: 'var(--evidence-muted)' }}
      >
        {title}
      </h3>
      <pre
        className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border p-4 font-mono text-xs leading-relaxed"
        style={{
          borderColor: 'var(--evidence-border)',
          background: 'var(--evidence-surface-raised)',
          color: 'var(--evidence-text)',
        }}
      >
        {body}
      </pre>
    </section>
  );
}

/** Specs are stored as JSONB; `{ text }` is the shape the workflow writes. */
function textOf(value: unknown): string {
  if (typeof value === 'string') return value;
  if (value && typeof value === 'object' && 'text' in value) {
    const text = (value as { text?: unknown }).text;
    if (typeof text === 'string') return text;
  }
  return JSON.stringify(value, null, 2);
}

'use client';

import { Check, CircleDashed, LoaderCircle, OctagonAlert } from 'lucide-react';
import type { DeliveryPhase } from '@/lib/delivery-lifecycle';

/**
 * The spine of the run surface: the ordered phases and where the run stopped.
 *
 * `blocked` is rendered *in place* — on the phase it stopped at — rather than
 * as an extra step at the end. A run that failed to deploy should read as "got
 * to deploying, stopped there", not as a run that quietly ended.
 */

const ORDER: readonly DeliveryPhase[] = [
  'sourcing',
  'requirements',
  'planning',
  'awaiting_approval',
  'building',
  'verifying',
  'deploying',
  'delivered',
] as const;

const LABELS: Record<DeliveryPhase, string> = {
  sourcing: 'Source',
  requirements: 'Requirements',
  planning: 'Plan',
  awaiting_approval: 'Approval',
  building: 'Build',
  verifying: 'Verify',
  deploying: 'Deploy',
  delivered: 'Delivered',
  blocked: 'Blocked',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

type StepState = 'done' | 'active' | 'stopped' | 'pending';

function stateFor(
  step: DeliveryPhase,
  phase: DeliveryPhase,
  stoppedAt: DeliveryPhase | null,
): StepState {
  if (stoppedAt) {
    const stoppedIndex = ORDER.indexOf(stoppedAt);
    const index = ORDER.indexOf(step);
    if (index < stoppedIndex) return 'done';
    if (index === stoppedIndex) return 'stopped';
    return 'pending';
  }
  if (phase === 'delivered') return 'done';
  const current = ORDER.indexOf(phase);
  const index = ORDER.indexOf(step);
  if (index < current) return 'done';
  if (index === current) return 'active';
  return 'pending';
}

export interface RunTimelineProps {
  phase: DeliveryPhase;
  /** Phase the run was in when it blocked, if any. */
  blockedFrom?: DeliveryPhase;
  live?: boolean;
}

export default function RunTimeline({ phase, blockedFrom, live }: RunTimelineProps) {
  const halted = phase === 'blocked' || phase === 'failed' || phase === 'cancelled';
  const stoppedAt: DeliveryPhase | null = halted ? (blockedFrom ?? 'sourcing') : null;

  return (
    <ol
      className="flex flex-wrap items-center gap-x-1 gap-y-3"
      aria-label={`Run progress — currently ${LABELS[phase]}`}
    >
      {ORDER.map((step, index) => {
        const state = stateFor(step, phase, stoppedAt);
        return (
          <li key={step} className="flex items-center gap-1">
            <div
              className="flex items-center gap-2 rounded-full border px-3 py-1.5"
              style={{
                borderColor:
                  state === 'stopped'
                    ? 'rgba(239,68,68,0.45)'
                    : state === 'active'
                      ? 'var(--evidence-accent-strong)'
                      : 'var(--evidence-border)',
                background:
                  state === 'done'
                    ? 'rgba(54,189,161,0.10)'
                    : state === 'stopped'
                      ? 'rgba(239,68,68,0.10)'
                      : 'transparent',
              }}
            >
              <StepIcon state={state} live={Boolean(live)} />
              <span
                className="text-xs font-medium tracking-wide"
                style={{
                  color:
                    state === 'pending' ? 'var(--evidence-muted)' : 'var(--evidence-text)',
                }}
              >
                {LABELS[step]}
              </span>
            </div>
            {index < ORDER.length - 1 && (
              <span
                aria-hidden="true"
                className="h-px w-4"
                style={{ background: 'var(--evidence-border)' }}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function StepIcon({ state, live }: { state: StepState; live: boolean }) {
  if (state === 'done') {
    return <Check size={14} style={{ color: 'var(--evidence-accent)' }} aria-hidden="true" />;
  }
  if (state === 'stopped') {
    return <OctagonAlert size={14} className="text-red-400" aria-hidden="true" />;
  }
  if (state === 'active') {
    return (
      <LoaderCircle
        size={14}
        className={live ? 'animate-spin' : ''}
        style={{ color: 'var(--evidence-accent)' }}
        aria-hidden="true"
      />
    );
  }
  return (
    <CircleDashed size={14} style={{ color: 'var(--evidence-muted)' }} aria-hidden="true" />
  );
}

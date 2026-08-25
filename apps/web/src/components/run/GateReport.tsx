'use client';

import { CircleCheck, CircleMinus, CircleX } from 'lucide-react';
import type { DeliveryGate } from '@/lib/delivery-lifecycle';

/**
 * The centrepiece of the surface: every gate, its verdict, and the proof.
 *
 * The product's claim is not "a run finished" but "a run finished and here is
 * why you can believe it". Evidence is therefore rendered verbatim — exit
 * codes, counts, status codes, commit SHAs — instead of being summarised into
 * a badge that would be indistinguishable from a fabricated one.
 */

const GATE_LABELS: Record<string, string> = {
  source_evidence: 'Source evidence',
  requirements_complete: 'Requirements complete',
  plan_executable: 'Plan executable',
  human_approved: 'Human approved',
  build_succeeded: 'Build succeeded',
  tests_passed: 'Tests passed',
  deployment_live: 'Deployment live',
};

export interface GateReportProps {
  gates: DeliveryGate[];
}

export default function GateReport({ gates }: GateReportProps) {
  if (gates.length === 0) {
    return (
      <p className="text-sm" style={{ color: 'var(--evidence-muted)' }}>
        No gates have been evaluated yet. Every claim this run makes will appear here with
        its evidence.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {gates.map((gate, index) => (
        <li
          key={`${gate.kind}-${gate.evaluatedAt}-${index}`}
          className="rounded-lg border p-4"
          style={{
            borderColor:
              gate.result === 'fail' ? 'rgba(239,68,68,0.35)' : 'var(--evidence-border)',
            background: 'var(--evidence-surface-raised)',
          }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <GateIcon result={gate.result} />
              <span className="text-sm font-semibold" style={{ color: 'var(--evidence-text)' }}>
                {GATE_LABELS[gate.kind] ?? gate.kind}
              </span>
            </div>
            <time
              className="font-mono text-xs"
              style={{ color: 'var(--evidence-muted)' }}
              dateTime={gate.evaluatedAt}
            >
              {new Date(gate.evaluatedAt).toLocaleTimeString()}
            </time>
          </div>

          <dl className="mt-3 grid gap-x-6 gap-y-1 sm:grid-cols-2">
            {Object.entries(gate.evidence).map(([key, value]) => (
              <div key={key} className="flex items-baseline gap-2 overflow-hidden">
                <dt
                  className="shrink-0 font-mono text-xs"
                  style={{ color: 'var(--evidence-muted)' }}
                >
                  {key}
                </dt>
                <dd
                  className="truncate font-mono text-xs"
                  style={{ color: 'var(--evidence-text)' }}
                  title={format(value)}
                >
                  {format(value)}
                </dd>
              </div>
            ))}
          </dl>
        </li>
      ))}
    </ul>
  );
}

function GateIcon({ result }: { result: DeliveryGate['result'] }) {
  if (result === 'pass') {
    return (
      <CircleCheck
        size={16}
        style={{ color: 'var(--evidence-accent)' }}
        aria-label="Passed"
      />
    );
  }
  if (result === 'fail') {
    return <CircleX size={16} className="text-red-400" aria-label="Failed" />;
  }
  return (
    <CircleMinus size={16} style={{ color: 'var(--evidence-muted)' }} aria-label="Skipped" />
  );
}

function format(value: unknown): string {
  if (value === null) return 'null';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return JSON.stringify(value);
}

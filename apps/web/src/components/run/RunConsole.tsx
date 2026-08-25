'use client';

import { useCallback, useState } from 'react';
import { Radio, RotateCcw } from 'lucide-react';
import { useRun } from '@/hooks/use-run';
import DeliveryCard from './DeliveryCard';
import GateReport from './GateReport';
import RunTimeline from './RunTimeline';
import SourceStep from './SourceStep';
import SpecReview from './SpecReview';

/**
 * The single run surface.
 *
 * Composition only: every piece of state comes from `useRun`, which mirrors the
 * persisted run. Audit finding F6 was a 1200-line component that mixed
 * fetching, state, and every phase of UI; the phases are separate presentational
 * components here so a change to one cannot silently alter another.
 */

export default function RunConsole() {
  const [runId, setRunId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const { run, spec, approval, loading, error, live, submitting, approve } = useRun(runId);

  const start = useCallback(async (input: { sourceUrl?: string; idea?: string }) => {
    setStarting(true);
    setStartError(null);
    try {
      const response = await fetch('/api/runs', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(input),
      });
      const body = (await response.json().catch(() => ({}))) as {
        runId?: string;
        error?: string;
      };
      if (!response.ok || !body.runId) {
        throw new Error(body.error || `Could not start the run (${response.status})`);
      }
      setRunId(body.runId);
    } catch (e: unknown) {
      setStartError(e instanceof Error ? e.message : String(e));
    } finally {
      setStarting(false);
    }
  }, []);

  return (
    <main className="evidence-workspace min-h-screen px-6 py-10">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
        <header className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1
              className="text-2xl font-bold tracking-tight"
              style={{ color: 'var(--evidence-text)' }}
            >
              Delivery run
            </h1>
            <div className="flex items-center gap-3">
              {live && (
                <span
                  className="inline-flex items-center gap-1.5 text-xs font-medium"
                  style={{ color: 'var(--evidence-accent)' }}
                >
                  <Radio size={13} className="animate-pulse" aria-hidden="true" />
                  live
                </span>
              )}
              {runId && (
                <button
                  type="button"
                  onClick={() => setRunId(null)}
                  className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium"
                  style={{
                    borderColor: 'var(--evidence-border)',
                    color: 'var(--evidence-muted)',
                  }}
                >
                  <RotateCcw size={13} aria-hidden="true" />
                  New run
                </button>
              )}
            </div>
          </div>
          <p className="max-w-2xl text-sm leading-relaxed" style={{ color: 'var(--evidence-muted)' }}>
            Source to shipped product, one gate at a time. Nothing is reported as delivered
            without a repository, a passing build, and a live URL that answered a request.
          </p>
          {runId && (
            <p className="font-mono text-xs" style={{ color: 'var(--evidence-muted)' }}>
              run {runId}
            </p>
          )}
        </header>

        {!runId && (
          <Panel title="Start">
            <SourceStep onStart={start} starting={starting} error={startError} />
          </Panel>
        )}

        {runId && loading && !run && (
          <p className="text-sm" style={{ color: 'var(--evidence-muted)' }}>
            Loading run…
          </p>
        )}

        {error && (
          <p className="text-sm text-red-400" role="alert">
            {error}
          </p>
        )}

        {run && (
          <>
            <Panel title="Progress">
              <RunTimeline phase={run.phase} blockedFrom={run.blockedFrom} live={live} />
            </Panel>

            <Panel title="Spec">
              <SpecReview
                spec={spec}
                approval={approval}
                awaitingApproval={run.phase === 'awaiting_approval'}
                submitting={submitting}
                onDecide={approve}
              />
            </Panel>

            <Panel title="Gate report">
              <GateReport gates={run.evidence.gates} />
            </Panel>

            <Panel title="Outcome">
              <DeliveryCard run={run} />
            </Panel>
          </>
        )}
      </div>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section
      className="flex flex-col gap-4 rounded-xl border p-5"
      style={{
        borderColor: 'var(--evidence-border)',
        background: 'var(--evidence-surface)',
      }}
    >
      <h2
        className="text-xs font-semibold uppercase tracking-widest"
        style={{ color: 'var(--evidence-muted)' }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

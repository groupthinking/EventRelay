'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { DeliveryPhase, DeliveryRun } from '@/lib/delivery-lifecycle';

/**
 * One delivery run, live.
 *
 * State is fetched once for the full picture (run + spec + approval) and then
 * kept current over SSE. The stream carries the same `DeliveryRun` shape the
 * server persists, so the UI never derives a phase locally — what is rendered
 * is what is stored, which is the only way the gate report can be trusted.
 */

export interface RunSpecView {
  id: string;
  version: number;
  requirements: unknown;
  plan: unknown;
  createdAt: string;
}

export interface RunApprovalView {
  decision: string;
  decidedBy: string;
}

export interface UseRunResult {
  run: DeliveryRun | null;
  spec: RunSpecView | null;
  approval: RunApprovalView | null;
  loading: boolean;
  error: string | null;
  /** True while the SSE connection is open. */
  live: boolean;
  submitting: boolean;
  approve: (approved: boolean, note?: string) => Promise<void>;
}

/** Phases where no further server-side progress will happen on its own. */
function isSettled(phase: DeliveryPhase): boolean {
  return (
    phase === 'delivered' || phase === 'failed' || phase === 'cancelled' || phase === 'blocked'
  );
}

export function useRun(runId: string | null): UseRunResult {
  const [run, setRun] = useState<DeliveryRun | null>(null);
  const [spec, setSpec] = useState<RunSpecView | null>(null);
  const [approval, setApproval] = useState<RunApprovalView | null>(null);
  const [loading, setLoading] = useState(Boolean(runId));
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const phaseRef = useRef<DeliveryPhase | null>(null);

  const refresh = useCallback(async (id: string) => {
    const response = await fetch(`/api/runs/${id}`, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(
        response.status === 404 ? 'Run not found' : `Could not load run (${response.status})`,
      );
    }
    const data = (await response.json()) as {
      run: DeliveryRun;
      spec: RunSpecView | null;
      approval: RunApprovalView | null;
    };
    setRun(data.run);
    setSpec(data.spec);
    setApproval(data.approval);
    phaseRef.current = data.run.phase;
  }, []);

  // Initial load.
  useEffect(() => {
    if (!runId) {
      setRun(null);
      setSpec(null);
      setApproval(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    refresh(runId)
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId, refresh]);

  // Live updates.
  useEffect(() => {
    if (!runId) return;
    const source = new EventSource(`/api/runs/${runId}/stream`);

    source.addEventListener('open', () => setLive(true));

    source.addEventListener('run', (event) => {
      const next = JSON.parse((event as MessageEvent<string>).data) as DeliveryRun;
      const previous = phaseRef.current;
      phaseRef.current = next.phase;
      setRun(next);
      // The spec appears once planning completes, and the approval once it is
      // recorded; both live outside the streamed run, so re-fetch on the phase
      // change that produces them rather than polling for them.
      if (previous !== next.phase) {
        void refresh(runId).catch(() => {});
      }
    });

    source.addEventListener('done', () => {
      setLive(false);
      source.close();
      void refresh(runId).catch(() => {});
    });

    source.addEventListener('error', () => {
      setLive(false);
      // EventSource reconnects on its own; a settled run has nothing left to
      // stream, so stop rather than reconnecting forever.
      if (phaseRef.current && isSettled(phaseRef.current)) source.close();
    });

    return () => {
      setLive(false);
      source.close();
    };
  }, [runId, refresh]);

  const approve = useCallback(
    async (approved: boolean, note?: string) => {
      if (!runId) return;
      setSubmitting(true);
      setError(null);
      try {
        const response = await fetch(`/api/runs/${runId}/approve`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ approved, note }),
        });
        if (!response.ok) {
          const body = (await response.json().catch(() => ({}))) as { error?: string };
          throw new Error(body.error || `Approval failed (${response.status})`);
        }
        await refresh(runId);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setSubmitting(false);
      }
    },
    [runId, refresh],
  );

  return { run, spec, approval, loading, error, live, submitting, approve };
}

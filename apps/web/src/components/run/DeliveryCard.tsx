'use client';

import { ExternalLink, GitBranch, OctagonAlert, ShieldCheck } from 'lucide-react';
import type { DeliveryRun } from '@/lib/delivery-lifecycle';

/**
 * The outcome, stated plainly.
 *
 * A blocked run gets the same prominence as a delivered one and names the gate
 * that stopped it. Presenting a partial result as a success is the exact
 * failure this pipeline was built to prevent, so the UI refuses to do it.
 */

export interface DeliveryCardProps {
  run: DeliveryRun;
}

export default function DeliveryCard({ run }: DeliveryCardProps) {
  const { repoUrl, deploymentUrl, testsPassedAt } = run.evidence;

  if (run.phase === 'blocked' || run.phase === 'failed' || run.phase === 'cancelled') {
    return (
      <div
        className="flex flex-col gap-2 rounded-xl border p-5"
        style={{ borderColor: 'rgba(239,68,68,0.35)', background: 'rgba(239,68,68,0.06)' }}
      >
        <div className="flex items-center gap-2">
          <OctagonAlert size={18} className="text-red-400" aria-hidden="true" />
          <h2 className="text-base font-semibold" style={{ color: 'var(--evidence-text)' }}>
            {run.phase === 'cancelled' ? 'Run cancelled' : 'Not delivered'}
          </h2>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--evidence-text)' }}>
          {run.blockedReason || run.error || 'The run stopped without recording a reason.'}
        </p>
        {run.blockedFrom && (
          <p className="font-mono text-xs" style={{ color: 'var(--evidence-muted)' }}>
            stopped in: {run.blockedFrom}
          </p>
        )}
      </div>
    );
  }

  if (run.phase !== 'delivered') {
    return (
      <p className="text-sm" style={{ color: 'var(--evidence-muted)' }}>
        The repository, test evidence, and live URL appear here when every gate has passed.
      </p>
    );
  }

  return (
    <div
      className="flex flex-col gap-4 rounded-xl border p-5"
      style={{
        borderColor: 'var(--evidence-accent-strong)',
        background: 'rgba(54,189,161,0.07)',
      }}
    >
      <div className="flex items-center gap-2">
        <ShieldCheck size={18} style={{ color: 'var(--evidence-accent)' }} aria-hidden="true" />
        <h2 className="text-base font-semibold" style={{ color: 'var(--evidence-text)' }}>
          Delivered
        </h2>
      </div>

      <dl className="flex flex-col gap-3">
        {deploymentUrl && (
          <Row label="Live URL">
            <a
              href={deploymentUrl}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 font-mono text-sm underline underline-offset-4"
              style={{ color: 'var(--evidence-accent)' }}
            >
              {deploymentUrl}
              <ExternalLink size={13} aria-hidden="true" />
            </a>
          </Row>
        )}
        {repoUrl && (
          <Row label="Repository">
            <a
              href={repoUrl}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 font-mono text-sm underline underline-offset-4"
              style={{ color: 'var(--evidence-text)' }}
            >
              <GitBranch size={13} aria-hidden="true" />
              {repoUrl}
            </a>
          </Row>
        )}
        {testsPassedAt && (
          <Row label="Tests passed">
            <span className="font-mono text-sm" style={{ color: 'var(--evidence-text)' }}>
              {new Date(testsPassedAt).toLocaleString()}
            </span>
          </Row>
        )}
      </dl>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <dt
        className="text-xs font-semibold uppercase tracking-widest"
        style={{ color: 'var(--evidence-muted)' }}
      >
        {label}
      </dt>
      <dd className="break-all">{children}</dd>
    </div>
  );
}

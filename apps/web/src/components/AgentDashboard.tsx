'use client';

import { clsx } from 'clsx';
import { Loader2, RefreshCw, Check, X } from 'lucide-react';
import type { AgentExecution } from '@/lib/types';

interface AgentDashboardProps {
  executions: AgentExecution[];
  loading?: boolean;
  className?: string;
}

const STATUS_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  queued:   { bg: 'bg-white/[0.03]', text: 'text-white/50', dot: 'bg-white/30' },
  running:  { bg: 'bg-primary-500/5', text: 'text-primary-400', dot: 'bg-primary-400' },
  complete: { bg: 'bg-green-500/5', text: 'text-green-400', dot: 'bg-green-400' },
  failed:   { bg: 'bg-red-500/5', text: 'text-red-400', dot: 'bg-red-400' },
};

export default function AgentDashboard({ executions, loading, className }: AgentDashboardProps) {
  if (loading) {
    return (
      <div className={clsx('space-y-3', className)}>
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Agent Executions
        </h3>
        <div
          role="status"
          aria-live="polite"
          className="flex items-center gap-2 text-sm text-white/40 py-6 justify-center"
        >
          <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" /> Dispatching agents…
        </div>
      </div>
    );
  }

  if (executions.length === 0) return null;

  const complete = executions.filter((e) => e.status === 'complete').length;
  const running = executions.filter((e) => e.status === 'running').length;
  const failed = executions.filter((e) => e.status === 'failed').length;

  return (
    <div className={clsx('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Agent Executions
        </h3>
        <div className="flex gap-3 text-xs" role="status" aria-live="polite">
          {running > 0 && (
            <span className="inline-flex items-center gap-1 text-primary-400">
              <RefreshCw className="h-3 w-3 animate-spin motion-reduce:animate-none" aria-hidden="true" /> {running} running
            </span>
          )}
          {complete > 0 && (
            <span className="inline-flex items-center gap-1 text-green-400">
              <Check className="h-3 w-3" aria-hidden="true" /> {complete} done
            </span>
          )}
          {failed > 0 && (
            <span className="inline-flex items-center gap-1 text-red-400">
              <X className="h-3 w-3" aria-hidden="true" /> {failed} failed
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {executions.map((exec) => {
          const style = STATUS_STYLES[exec.status] || STATUS_STYLES.queued;
          return (
            <div
              key={exec.agent_id}
              className={clsx(
                'p-3.5 rounded-xl border border-white/[0.06] transition-colors',
                style.bg,
              )}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={clsx('w-2 h-2 rounded-full', style.dot)} />
                  <span className="text-sm font-medium text-white/80">{exec.agent_type}</span>
                </div>
                <span className={clsx('text-xs font-medium capitalize', style.text)}>
                  {exec.status}
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
                <div
                  className={clsx(
                    'h-full rounded-full transition-[width] duration-500 motion-reduce:transition-none',
                    exec.status === 'complete'
                      ? 'bg-green-500'
                      : exec.status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-primary-500',
                  )}
                  style={{ width: `${exec.progress}%` }}
                />
              </div>

              {/* Result preview */}
              {exec.result && (
                <p className="text-xs text-white/40 mt-2 line-clamp-2">
                  {String(exec.result.summary || exec.result.output || JSON.stringify(exec.result).slice(0, 120))}
                </p>
              )}
              {exec.error && (
                <p className="text-xs text-red-400/70 mt-2">{exec.error}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

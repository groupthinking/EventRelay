'use client';

import { clsx } from 'clsx';
import type { AgentExecution, ExtractedEvent } from '@/lib/types';

interface ResultsViewerProps {
  executions: AgentExecution[];
  events: ExtractedEvent[];
  className?: string;
}

export default function ResultsViewer({ executions, events, className }: ResultsViewerProps) {
  const completed = executions.filter((e) => e.status === 'complete' && e.result);

  if (completed.length === 0) return null;

  return (
    <div className={clsx('space-y-3', className)}>
      <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
        Results
      </h3>

      <div className="space-y-3">
        {completed.map((exec) => {
          const event = events.find((e) => e.id === exec.event_id);
          const result = exec.result as any;

          const hasStructuredData = result && result.goal && result.plan && result.reason;

          return (
            <div
              key={exec.agent_id}
              className="p-4 rounded-xl bg-green-500/5 border border-green-500/10"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium text-green-400">
                  ✓ {exec.agent_type}
                </span>
                {event && (
                  <span className="text-xs text-white/30">→ {event.title.slice(0, 50)}</span>
                )}
              </div>

              {hasStructuredData ? (
                <div className="text-xs text-white/80 bg-black/20 rounded-lg p-3 space-y-3">
                  <div>
                    <span className="font-semibold text-white/50 uppercase tracking-wider block mb-1">Goal</span>
                    <p>{result.goal}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-white/50 uppercase tracking-wider block mb-1">Plan</span>
                    {Array.isArray(result.plan) ? (
                      <ul className="list-disc pl-4 space-y-1">
                        {result.plan.map((item: string, i: number) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>{result.plan}</p>
                    )}
                  </div>
                  <div>
                    <span className="font-semibold text-white/50 uppercase tracking-wider block mb-1">Reason</span>
                    <p className="text-white/60">{result.reason}</p>
                  </div>
                </div>
              ) : (
                <pre className="text-xs text-white/60 bg-black/20 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(exec.result, null, 2)}
                </pre>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

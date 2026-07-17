'use client';

import { clsx } from 'clsx';
import { Check } from 'lucide-react';
import type { AgentExecution, ExtractedEvent } from '@/lib/types';

interface ResultsViewerProps {
  executions: AgentExecution[];
  events: ExtractedEvent[];
  className?: string;
}

/**
 * Renders the results for completed executions with a result.
 *
 * @param executions - Agent executions to display.
 * @param events - Events used to resolve execution titles.
 * @param className - Additional CSS classes for the container.
 * @returns The results section for completed executions with results, or `null` when none are available.
 */
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
          return (
            <div
              key={exec.agent_id}
              className="p-4 rounded-xl bg-green-500/5 border border-green-500/10"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex items-center gap-1 text-sm font-medium text-green-400">
                  <Check className="h-4 w-4" aria-hidden="true" /> {exec.agent_type}
                </span>
                {event && (
                  <span className="text-xs text-white/30">→ {event.title.slice(0, 50)}</span>
                )}
              </div>
              <pre className="text-xs text-white/60 bg-black/20 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(exec.result, null, 2)}
              </pre>
            </div>
          );
        })}
      </div>
    </div>
  );
}

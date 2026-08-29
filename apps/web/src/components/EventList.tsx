'use client';

import { clsx } from 'clsx';
import { Zap, Pin, Code2, AlertTriangle, Loader2, type LucideIcon } from 'lucide-react';
import type { ExtractedEvent } from '@/lib/types';

interface EventListProps {
  events: ExtractedEvent[];
  loading?: boolean;
  onExtract?: () => void;
  className?: string;
}

// Event Classification Taxonomy: ACTION (blue), TOPIC (purple), CODE (green), ALERT (red)
// Legacy types (mention, insight) map to the new taxonomy for backward compat
const TYPE_STYLES: Record<string, { bg: string; text: string; icon: LucideIcon }> = {
  action:  { bg: 'bg-blue-500/10 border-blue-500/20', text: 'text-blue-400', icon: Zap },
  topic:   { bg: 'bg-purple-500/10 border-purple-500/20', text: 'text-purple-400', icon: Pin },
  code:    { bg: 'bg-green-500/10 border-green-500/20', text: 'text-green-400', icon: Code2 },
  alert:   { bg: 'bg-red-500/10 border-red-500/20', text: 'text-red-400', icon: AlertTriangle },
  // Legacy type mappings
  mention: { bg: 'bg-purple-500/10 border-purple-500/20', text: 'text-purple-400', icon: Pin },
  insight: { bg: 'bg-red-500/10 border-red-500/20', text: 'text-red-400', icon: AlertTriangle },
};

/**
 * Displays a list of extracted events with loading and empty states.
 *
 * @param events - The events to display.
 * @param loading - Whether the event extraction state is being shown.
 * @param onExtract - Called when the extract events button is clicked.
 * @param className - Additional classes for the container.
 * @returns The rendered event list.
 */
export default function EventList({ events, loading, onExtract, className }: EventListProps) {
  if (loading) {
    return (
      <div className={clsx('space-y-3', className)}>
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Extracted Events
        </h3>
        <div
          role="status"
          aria-live="polite"
          className="flex items-center gap-2 text-sm text-white/40 py-8 justify-center"
        >
          <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" /> Extracting events…
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Extracted Events
        </h3>
        {events.length === 0 && onExtract && (
          <button
            onClick={onExtract}
            className="text-xs px-3 py-1.5 rounded-lg bg-primary-500/10 text-primary-400 border border-primary-500/20 hover:bg-primary-500/20 transition-colors"
          >
            Extract Events
          </button>
        )}
        {events.length > 0 && (
          <span className="text-xs text-white/30">{events.length} events</span>
        )}
      </div>

      {events.length === 0 && !onExtract && (
        <p className="text-sm text-white/30 py-4 text-center">No events extracted yet.</p>
      )}

      <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
        {events.map((event) => {
          const style = TYPE_STYLES[event.type] || TYPE_STYLES.topic;
          const Icon = style.icon;
          return (
            <div
              key={event.id}
              className={clsx(
                'p-3 rounded-xl border transition-colors hover:bg-white/[0.02]',
                style.bg,
              )}
            >
              <div className="flex items-start gap-2">
                <Icon className={clsx('h-4 w-4 mt-0.5 flex-none', style.text)} aria-hidden="true" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={clsx('text-xs font-semibold uppercase', style.text)}>
                      {event.type}
                    </span>
                    {event.timestamp && (
                      <span className="text-xs text-white/25">{event.timestamp}</span>
                    )}
                  </div>
                  <p className="text-sm text-white/80 mt-1 leading-snug">{event.title}</p>
                  {event.description && (
                    <p className="text-xs text-white/40 mt-1 line-clamp-2">
                      {event.description}
                    </p>
                  )}
                </div>
                {typeof event.confidence === 'number' && (
                  <span
                    className="text-xs text-white/45 tabular-nums"
                    title={`Provider confidence: ${Math.round(event.confidence * 100)}%`}
                  >
                    {Math.round(event.confidence * 100)}%
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

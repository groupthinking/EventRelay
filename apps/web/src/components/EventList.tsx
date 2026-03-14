'use client';

import { useState, useCallback, useMemo } from 'react';
import { clsx } from 'clsx';
import type { ExtractedEvent } from '@/lib/types';
import { useToast } from '@/components/ui/Toast';

interface EventListProps {
  events: ExtractedEvent[];
  loading?: boolean;
  onExtract?: () => void;
  className?: string;
}

const TYPE_STYLES: Record<string, { bg: string; text: string; icon: string; label: string }> = {
  action:  { bg: 'bg-blue-500/10 border-blue-500/20', text: 'text-blue-400', icon: '⚡', label: 'Actions' },
  mention: { bg: 'bg-purple-500/10 border-purple-500/20', text: 'text-purple-400', icon: '💬', label: 'Mentions' },
  topic:   { bg: 'bg-green-500/10 border-green-500/20', text: 'text-green-400', icon: '📌', label: 'Topics' },
  insight: { bg: 'bg-amber-500/10 border-amber-500/20', text: 'text-amber-400', icon: '💡', label: 'Insights' },
};

type EventType = keyof typeof TYPE_STYLES | 'all';

export default function EventList({ events, loading, onExtract, className }: EventListProps) {
  const [activeFilter, setActiveFilter] = useState<EventType>('all');
  const [copied, setCopied] = useState(false);
  const { addToast } = useToast();

  // Determine which filter pills to show based on available event types
  const availableTypes = useMemo(
    () => Array.from(new Set(events.map((e) => e.type))).filter((t) => t in TYPE_STYLES) as EventType[],
    [events]
  );

  const filteredEvents = useMemo(
    () => (activeFilter === 'all' ? events : events.filter((e) => e.type === activeFilter)),
    [events, activeFilter]
  );

  const handleCopyAll = useCallback(async () => {
    if (events.length === 0) return;
    const text = events
      .map((e) => `[${e.type.toUpperCase()}] ${e.title}${e.description ? ` — ${e.description}` : ''}`)
      .join('\n');
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      addToast('Events copied to clipboard', 'success');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      addToast('Failed to copy events', 'error');
    }
  }, [events, addToast]);

  // ── Skeleton loading ──
  if (loading) {
    return (
      <div className={clsx('space-y-3', className)}>
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Extracted Events
        </h3>
        <div className="space-y-2">
          {[1, 2, 3].map((n) => (
            <div key={n} className="p-3 rounded-xl border border-white/[0.06]">
              <div className="skeleton h-4 w-1/4 mb-2 rounded" />
              <div className="skeleton h-3 w-3/4 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── Empty state with CTA ──
  if (events.length === 0) {
    return (
      <div className={clsx('space-y-3', className)}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
            Extracted Events
          </h3>
          {onExtract && (
            <button
              onClick={onExtract}
              className="text-xs px-3 py-1.5 rounded-lg bg-primary-500/10 text-primary-400 border border-primary-500/20 hover:bg-primary-500/20 transition-colors"
            >
              Extract Events
            </button>
          )}
        </div>
        <div className="flex flex-col items-center justify-center py-10 gap-3 text-center">
          <div className="text-4xl opacity-30">⚡</div>
          <p className="text-sm text-white/30">
            {onExtract
              ? 'Click "Extract Events" to identify key actions, topics, and insights from the video.'
              : 'No events extracted yet.'}
          </p>
          {onExtract && (
            <button
              onClick={onExtract}
              className="mt-1 btn btn-primary py-2 px-5 text-sm"
            >
              Extract Events
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('space-y-3', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Extracted Events
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/30">{filteredEvents.length} of {events.length}</span>
          {/* Copy button */}
          <button
            onClick={handleCopyAll}
            title="Copy all events"
            className={clsx(
              'flex items-center gap-1 text-xs px-2 py-1 rounded-lg border transition-all',
              copied
                ? 'bg-green-500/15 border-green-500/30 text-green-400'
                : 'bg-white/[0.03] border-white/[0.08] text-white/40 hover:text-white/70'
            )}
          >
            {copied ? '✓' : (
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Type filter pills */}
      {availableTypes.length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setActiveFilter('all')}
            className={clsx(
              'text-xs px-2.5 py-1 rounded-full border transition-all',
              activeFilter === 'all'
                ? 'bg-white/10 border-white/20 text-white'
                : 'bg-white/[0.03] border-white/[0.08] text-white/40 hover:text-white/60'
            )}
          >
            All
          </button>
          {availableTypes.map((type) => {
            const style = TYPE_STYLES[type];
            return (
              <button
                key={type}
                onClick={() => setActiveFilter(type)}
                className={clsx(
                  'text-xs px-2.5 py-1 rounded-full border transition-all flex items-center gap-1',
                  activeFilter === type
                    ? `${style.bg} ${style.text} border-current/30`
                    : 'bg-white/[0.03] border-white/[0.08] text-white/40 hover:text-white/60'
                )}
              >
                <span>{style.icon}</span>
                {style.label}
              </button>
            );
          })}
        </div>
      )}

      <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
        {filteredEvents.map((event) => {
          const style = TYPE_STYLES[event.type] || TYPE_STYLES.topic;
          return (
            <div
              key={event.id}
              className={clsx(
                'p-3 rounded-xl border transition-colors hover:bg-white/[0.02]',
                style.bg,
              )}
            >
              <div className="flex items-start gap-2">
                <span className="text-base mt-0.5">{style.icon}</span>
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
                <span
                  className="text-xs text-white/20 tabular-nums"
                  title={`Confidence: ${Math.round(event.confidence * 100)}%`}
                >
                  {Math.round(event.confidence * 100)}%
                </span>
              </div>
            </div>
          );
        })}
        {filteredEvents.length === 0 && (
          <p className="text-sm text-white/30 text-center py-4">
            {activeFilter !== 'all' ? `No ${activeFilter} events found.` : 'No events found.'}
          </p>
        )}
      </div>
    </div>
  );
}

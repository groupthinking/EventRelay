'use client';

import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import FeedbackWidget from '@/components/FeedbackWidget';
import InteractiveTranscript, { type TranscriptSegment } from '@/components/InteractiveTranscript';
import { hasRichDashboardInsights, isThinDashboardAnalysis } from '@/lib/dashboard-analysis';
import type { SearchResult, Video } from '@/store/dashboard-types';

const TranscriptViewer = dynamic(() => import('@/components/TranscriptViewer'), {
  loading: () => <PanelLoading label="Loading transcript…" />,
});
const AgentDashboard = dynamic(() => import('@/components/AgentDashboard'), {
  loading: () => <PanelLoading label="Loading agent dashboard…" />,
});
const EventList = dynamic(() => import('@/components/EventList'), {
  loading: () => <PanelLoading label="Loading events…" />,
});

function PanelLoading({ label }: { label: string }) {
  return <div className="py-12 text-center text-sm" style={{ color: 'rgba(248,245,253,0.4)' }}>{label}</div>;
}

function EmptyState({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 gap-4">
      <div style={{ color: 'rgba(248,245,253,0.2)' }}>{icon}</div>
      <p className="max-w-xs text-sm" style={{ color: 'rgba(248,245,253,0.4)' }}>{children}</p>
    </div>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="w-1 h-5" style={{ background: '#6af2de' }} />
      <h3 className="font-heading text-base font-bold tracking-tight" style={{ color: '#f8f5fd' }}>{children}</h3>
    </div>
  );
}

/* ─────────────────────────── Transcript ─────────────────────────── */

export function TranscriptPanel({
  video,
  segments,
  hasTimings,
  currentTime,
  isPlaying,
  onSeek,
}: {
  video: Video;
  segments: TranscriptSegment[];
  hasTimings: boolean;
  currentTime: number;
  isPlaying: boolean;
  onSeek: (seconds: number) => void;
}) {
  if (!video.transcript) {
    return (
      <EmptyState
        icon={<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h10" /></svg>}
      >
        {video.status === 'processing' ? 'Transcript is being generated…' : 'No transcript available.'}
      </EmptyState>
    );
  }

  if (hasTimings && segments.length > 0) {
    return (
      <InteractiveTranscript
        segments={segments}
        currentTime={currentTime}
        onSeek={onSeek}
        isPlaying={isPlaying}
      />
    );
  }

  // Fallback: no per-line timings, render read-only transcript.
  return (
    <div className="space-y-4">
      <p className="text-[11px] uppercase tracking-[0.15em]" style={{ color: 'rgba(248,245,253,0.3)' }}>
        Timestamps unavailable — transcript is read-only
      </p>
      <Suspense fallback={<PanelLoading label="Loading transcript…" />}>
        <TranscriptViewer transcript={video.transcript} />
      </Suspense>
    </div>
  );
}

/* ─────────────────────────── Insights / Summary ─────────────────────────── */

export function InsightsPanel({ video }: { video: Video }) {
  const hasInsights = hasRichDashboardInsights(video);
  const thinAnalysis = isThinDashboardAnalysis(video);

  if (!hasInsights) {
    return (
      <EmptyState
        icon={<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 8v4l2 2" /></svg>}
      >
        {video.status === 'processing'
          ? 'AI is analyzing the video. Insights will appear here shortly.'
          : thinAnalysis
            ? 'Agents finished but the backend returned minimal data. Check logs or retry from the library.'
            : 'No analysis available for this video.'}
      </EmptyState>
    );
  }

  const insights = video.insights!;

  return (
    <div className="space-y-8 stitch-fade-in">
      <section>
        <SectionHeading>Intelligence Synthesis</SectionHeading>
        <p className="leading-relaxed text-sm" style={{ color: 'rgba(172, 170, 177, 1)' }}>{insights.summary}</p>
      </section>

      {insights.topics.length > 0 && (
        <section>
          <SectionHeading>Extracted Topics</SectionHeading>
          <div className="flex flex-wrap gap-2">
            {insights.topics.map((topic, i) => (
              <span
                key={topic}
                className="text-[10px] font-bold uppercase tracking-widest px-3 py-1"
                style={{ background: 'rgba(37, 37, 44, 1)', color: i < 2 ? '#6af2de' : i < 4 ? '#69ccff' : 'rgba(172, 170, 177, 1)' }}
              >
                {topic}
              </span>
            ))}
          </div>
        </section>
      )}

      {insights.actions.length > 0 && (
        <section>
          <SectionHeading>Directive Protocols</SectionHeading>
          <div className="grid grid-cols-1 gap-3">
            {insights.actions.map((action, i) => (
              <div
                key={i}
                className="p-4 transition-all stitch-fade-in"
                style={{
                  background: 'rgba(37, 37, 44, 0.4)',
                  backdropFilter: 'blur(20px)',
                  borderLeft: i === 0 ? '2px solid rgba(159, 5, 25, 0.8)' : '2px solid rgba(16, 183, 165, 0.8)',
                  animationDelay: `${i * 80}ms`,
                }}
              >
                <div className="flex justify-between items-start mb-2 gap-3">
                  <span
                    className="px-2 py-0.5 text-[10px] font-bold tracking-widest uppercase rounded-sm"
                    style={{ background: i === 0 ? 'rgba(159,5,25,0.2)' : 'rgba(16,183,165,0.2)', color: i === 0 ? '#ff716c' : '#6af2de' }}
                  >
                    {action.category || (i === 0 ? 'Critical' : 'Strategic')}
                  </span>
                  {action.estimatedMinutes != null && (
                    <span className="text-[10px] font-mono" style={{ color: 'rgba(248,245,253,0.35)' }}>~{action.estimatedMinutes}m</span>
                  )}
                </div>
                <p className="font-heading font-medium text-sm leading-tight mb-1" style={{ color: '#f8f5fd' }}>{action.title}</p>
                {action.description && (
                  <p className="text-xs leading-relaxed" style={{ color: 'rgba(172, 170, 177, 0.8)' }}>{action.description}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <FeedbackWidget videoId={video.id} tab="analysis" />
    </div>
  );
}

/* ─────────────────────────── Actions / Events ─────────────────────────── */

export function ActionsPanel({
  video,
  onExtractEvents,
}: {
  video: Video;
  onExtractEvents?: (videoId: string) => void;
}) {
  return (
    <div className="space-y-4">
      <Suspense fallback={<PanelLoading label="Loading events…" />}>
        <EventList
          events={video.events || []}
          onExtract={onExtractEvents ? () => onExtractEvents(video.id) : undefined}
        />
      </Suspense>
      <FeedbackWidget videoId={video.id} tab="actions" />
    </div>
  );
}

/* ─────────────────────────── Agents ─────────────────────────── */

export function AgentsPanel({
  video,
  agentBackend,
  onDispatch,
  onRefresh,
}: {
  video: Video;
  agentBackend: boolean;
  onDispatch: (videoId: string) => void;
  onRefresh: (videoId: string) => void;
}) {
  const hasEvents = !!(video.events && video.events.length > 0);
  const agents = video.agents || [];
  const anyRunning = agents.some((a) => a.status === 'running' || a.status === 'queued');

  return (
    <div className="space-y-4">
      {(hasEvents || agents.length > 0) && (
        <div className="flex items-center justify-end gap-2 flex-wrap">
          {hasEvents && agentBackend && (
            <button
              onClick={() => onDispatch(video.id)}
              className="px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/50 rounded"
              style={{ background: 'rgba(129,140,248,0.15)', color: '#818cf8', border: '1px solid rgba(129,140,248,0.3)' }}
            >
              Dispatch {video.events!.length} events
            </button>
          )}
          {anyRunning && (
            <button
              onClick={() => onRefresh(video.id)}
              className="px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/30 rounded"
              style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(248,245,253,0.7)', border: '1px solid rgba(255,255,255,0.1)' }}
            >
              Refresh
            </button>
          )}
        </div>
      )}
      {hasEvents && !agentBackend && (
        <p className="text-xs text-right" style={{ color: 'rgba(248,245,253,0.35)' }}>
          Backend agents offline — deploy FastAPI + set BACKEND_URL to dispatch real MCP agents.
        </p>
      )}
      <Suspense fallback={<PanelLoading label="Loading agent dashboard…" />}>
        <AgentDashboard
          executions={agents}
          loading={video.status === 'processing' && agents.length === 0}
        />
      </Suspense>
      {video.status !== 'processing' && agents.length === 0 && (
        <EmptyState
          icon={<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><rect x="4" y="8" width="16" height="12" rx="2" /><path d="M12 8V4M9 14h.01M15 14h.01" /></svg>}
        >
          No agent executions yet.
        </EmptyState>
      )}
    </div>
  );
}

/* ─────────────────────────── Search ─────────────────────────── */

export function SearchPanel({
  video,
  searchQuery,
  setSearchQuery,
  performSearch,
  searchResults,
  searchLoading,
  onSeek,
}: {
  video: Video;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  performSearch: (videoId: string, q: string) => void;
  searchResults: SearchResult[];
  searchLoading: boolean;
  onSeek?: (seconds: number) => void;
}) {
  return (
    <div className="space-y-5">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          performSearch(video.id, searchQuery);
        }}
        className="flex gap-2"
      >
        <label htmlFor="search-video" className="sr-only">
          Search the video
        </label>
        <input
          id="search-video"
          type="text"
          placeholder="Search the video…"
          className="flex-1 px-3 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40 transition-colors rounded-lg"
          style={{ background: 'rgba(25, 25, 31, 0.8)', border: '1px solid rgba(106, 242, 222, 0.15)', color: '#f8f5fd' }}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button
          type="submit"
          className="px-4 py-2.5 font-heading font-bold text-xs tracking-wider uppercase transition-all disabled:opacity-30 active:scale-95 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-[#10b7a5]/60"
          style={{ background: 'rgba(16, 183, 165, 0.9)', color: '#002b26' }}
          disabled={searchLoading || !searchQuery.trim()}
          aria-busy={searchLoading || undefined}
        >
          {searchLoading ? '…' : 'Go'}
        </button>
      </form>

      {searchResults.length > 0 ? (
        <div className="space-y-3">
          <h4 className="text-[11px] font-bold uppercase tracking-wider" style={{ color: 'rgba(248,245,253,0.4)' }}>Top Results</h4>
          {searchResults.map((res, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onSeek?.(res.start)}
              className="w-full text-left p-4 rounded-xl border transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/50"
              style={{ background: 'rgba(37,37,44,0.4)', borderColor: 'rgba(255,255,255,0.05)' }}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(106,242,222,0.1)', color: '#6af2de' }}>
                  {new Date(res.start * 1000).toISOString().substr(11, 8)}
                </span>
                <span className="text-[11px] font-mono" style={{ color: 'rgba(248,245,253,0.3)' }}>{(res.score * 100).toFixed(0)}%</span>
              </div>
              <p className="text-sm leading-relaxed" style={{ color: 'rgba(248,245,253,0.7)' }}>{res.text}</p>
            </button>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>}
        >
          Search for a topic to jump to that moment in the video.
        </EmptyState>
      )}
    </div>
  );
}

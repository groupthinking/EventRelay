'use client';

import { Suspense, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { AlignLeft, Bot, Clock3, Search, ShieldCheck } from 'lucide-react';
import FeedbackWidget from '@/components/FeedbackWidget';
import InteractiveTranscript, { type TranscriptSegment } from '@/components/InteractiveTranscript';
import {
  buildScaffoldPackage,
  downloadScaffoldPackage,
  summarizeProjectScaffold,
  type ActionCardLike,
} from '@/lib/action-surface';
import type { AgentAction } from '@/lib/action-lifecycle';
import { hasRichDashboardInsights, isThinDashboardAnalysis } from '@/lib/dashboard-analysis';
import { useActionAgentStore } from '@/store/action-agent-store';
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
        icon={<AlignLeft className="h-10 w-10" strokeWidth={1.5} aria-hidden="true" />}
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
        icon={<Clock3 className="h-10 w-10" strokeWidth={1.5} aria-hidden="true" />}
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
        <SectionHeading>Key takeaways</SectionHeading>
        <p className="text-[15px] leading-7" style={{ color: 'rgba(214, 219, 216, 0.82)' }}>{insights.summary}</p>
      </section>

      {insights.topics.length > 0 && (
        <section>
          <SectionHeading>Topics</SectionHeading>
          <div className="flex flex-wrap gap-2">
            {insights.topics.map((topic, i) => (
              <span
                key={topic}
                className="rounded-md px-3 py-1.5 text-xs font-medium"
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
          <SectionHeading>Proposed actions</SectionHeading>
          <div className="grid grid-cols-1 gap-3">
            {insights.actions.map((action, i) => {
              const normalized = typeof action === 'string'
                ? { title: action, description: '', category: 'Recommended', estimatedMinutes: null }
                : action;
              return (
              <div
                key={`${normalized.title}-${i}`}
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
                    {normalized.category || (i === 0 ? 'Critical' : 'Strategic')}
                  </span>
                  {normalized.estimatedMinutes != null && (
                    <span className="text-[10px] font-mono" style={{ color: 'rgba(248,245,253,0.35)' }}>~{normalized.estimatedMinutes}m</span>
                  )}
                </div>
                <p className="mb-1 font-heading text-base font-medium leading-snug" style={{ color: '#f8f5fd' }}>{normalized.title}</p>
                {normalized.description && (
                  <p className="text-sm leading-6" style={{ color: 'rgba(200, 205, 202, 0.78)' }}>{normalized.description}</p>
                )}
              </div>
              );
            })}
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
  const transcript = (video.transcript || '').trim();
  const hasTranscript = transcript.length > 40;
  const {
    lifecycle,
    isRunning,
    sourceVideoId,
    runFromTranscript,
    confirmPreparedActions,
    reset,
  } = useActionAgentStore();
  const planMatchesVideo = sourceVideoId === video.id;
  const fulfilled = planMatchesVideo ? lifecycle.actions || [] : [];
  const isPrepared = planMatchesVideo && lifecycle.phase === 'dispatching';
  const [selectedActionIndexes, setSelectedActionIndexes] = useState<number[]>([]);
  useEffect(() => {
    setSelectedActionIndexes(isPrepared ? lifecycle.actions.map((_, index) => index) : []);
  }, [isPrepared, lifecycle.actions, lifecycle.id]);
  const selectedActions = fulfilled.filter((_, index) => selectedActionIndexes.includes(index));
  const plannedActions = video.insights?.actions || [];
  const projectScaffold = video.insights?.project_scaffold;
  const scaffoldPreview = summarizeProjectScaffold(projectScaffold);

  const exportScaffold = () => {
    // Prefer tool-fulfilled titles; fall back to planned analysis actions.
    const fromTools: ActionCardLike[] = fulfilled
      .filter((a) => typeof a.input?.title === 'string' || a.tool)
      .map((a) => ({
        title:
          typeof a.input?.title === 'string'
            ? a.input.title
            : a.tool.replace(/_/g, ' '),
        description:
          a.result ||
          (typeof a.input?.description === 'string' ? a.input.description : ''),
        category: a.tool,
      }));
    const fromPlan: ActionCardLike[] = plannedActions.map((a) =>
      typeof a === 'string'
        ? { title: a, description: '', category: 'recommended' }
        : {
            title: a.title,
            description: a.description,
            category: a.category,
            estimatedMinutes: a.estimatedMinutes,
          },
    );
    const actions = fromTools.length > 0 ? fromTools : fromPlan;
    const pkg = buildScaffoldPackage({
      projectName: video.title || 'eventrelay-project',
      actions,
      projectScaffold,
    });
    downloadScaffoldPackage(pkg);
  };

  const canExport =
    fulfilled.length > 0 || plannedActions.length > 0 || projectScaffold != null;

  const actionOutcomeTitle = (action: AgentAction): string => {
    const title = typeof action.input?.title === 'string' ? action.input.title : '';
    const name = typeof action.input?.name === 'string' ? action.input.name : '';
    const topic = typeof action.input?.topic === 'string' ? action.input.topic : '';
    const task = typeof action.input?.task === 'string' ? action.input.task : '';
    if (action.tool === 'save_resource') return `Save ${name || 'resource'}`;
    if (action.tool === 'schedule_followup') return `Schedule follow-up${topic ? `: ${topic}` : ''}`;
    if (action.tool === 'create_workflow_task') return title || 'Create workflow task';
    if (action.tool === 'dispatch_agent') return task || title || 'Dispatch agent';
    return title || name || topic || action.tool.replace(/_/g, ' ');
  };

  return (
    <div className="space-y-4">
      {/* F12: Prepare, review, then explicitly confirm /api/agents/actions */}
      <section
        className="rounded-xl border p-4 space-y-3"
        style={{ borderColor: 'rgba(129,140,248,0.25)', background: 'rgba(129,140,248,0.06)' }}
      >
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: '#a5b4fc' }}>
              Review action plan
            </h3>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: 'rgba(248,245,253,0.55)' }}>
              Preparation proposes tool calls but executes nothing. Select, inspect, or reject each
              item before confirming any external side effect.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {fulfilled.length > 0 && (
              <button
                type="button"
                onClick={() => reset()}
                className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded"
                style={{ color: 'rgba(248,245,253,0.5)', border: '1px solid rgba(255,255,255,0.1)' }}
              >
                Clear
              </button>
            )}
            <button
              type="button"
              disabled={!hasTranscript || isRunning || (isPrepared && selectedActions.length === 0)}
              onClick={() =>
                isPrepared
                  ? confirmPreparedActions(selectedActions, video.id)
                  : runFromTranscript(transcript, video.title, video.id)
              }
              className="px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/50 rounded disabled:opacity-40"
              style={{
                background: isPrepared ? 'rgba(248,113,113,0.16)' : 'rgba(129,140,248,0.2)',
                color: isPrepared ? '#fecaca' : '#c7d2fe',
                border: isPrepared
                  ? '1px solid rgba(248,113,113,0.4)'
                  : '1px solid rgba(129,140,248,0.4)',
              }}
            >
              {isRunning
                ? isPrepared
                  ? 'Executing confirmed plan…'
                  : 'Preparing plan…'
                : isPrepared
                  ? `Confirm ${selectedActions.length} selected action${selectedActions.length === 1 ? '' : 's'}`
                  : 'Prepare action plan'}
            </button>
          </div>
        </div>

        {!hasTranscript && (
          <p className="text-xs" style={{ color: 'rgba(248,245,253,0.4)' }}>
            Need a transcript on this video before the action agent can run.
          </p>
        )}

        {lifecycle.phase !== 'idle' && (
          <p className="text-[11px] font-mono" style={{ color: 'rgba(165,180,252,0.8)' }}>
            {isPrepared ? 'Status: prepared for review' : `Phase: ${lifecycle.phase}`}
            {lifecycle.provider ? ` · ${lifecycle.provider}` : ''}
            {lifecycle.error ? ` · ${lifecycle.error}` : ''}
          </p>
        )}

        {sourceVideoId && !planMatchesVideo && (
          <div className="rounded-lg border border-amber-300/20 bg-amber-300/[0.07] px-3 py-3 text-sm text-amber-100/80">
            The prepared plan belongs to another video. Preparing here will replace it; it cannot be
            confirmed from this workspace.
          </div>
        )}

        {isPrepared && (
          <div
            className="flex items-start gap-2 rounded-lg border px-3 py-2"
            style={{ borderColor: 'rgba(248,113,113,0.3)', background: 'rgba(248,113,113,0.08)' }}
          >
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" style={{ color: '#fca5a5' }} aria-hidden="true" />
            <p className="text-xs leading-relaxed" style={{ color: '#fecaca' }}>
              Review required. The confirmation button is the authorization boundary; nothing below
              has run yet.
            </p>
          </div>
        )}

        {fulfilled.length > 0 && (
          <ul className="space-y-2">
            {fulfilled.map((action, i) => (
              <li
                key={`${action.tool}-${i}`}
                className="rounded-lg border px-3 py-2"
                style={{
                  borderColor:
                    action.status === 'failed' || action.isError
                      ? 'rgba(248,113,113,0.35)'
                      : 'rgba(52,211,153,0.25)',
                  background: 'rgba(0,0,0,0.2)',
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <label className="flex min-h-11 min-w-0 cursor-pointer items-start gap-3 py-1">
                    <input
                      type="checkbox"
                      checked={selectedActionIndexes.includes(i)}
                      disabled={!isPrepared}
                      onChange={() => {
                        setSelectedActionIndexes((current) =>
                          current.includes(i)
                            ? current.filter((index) => index !== i)
                            : [...current, i],
                        );
                      }}
                      className="mt-0.5 h-5 w-5 accent-[#6de1c6]"
                      aria-label={`Select ${actionOutcomeTitle(action)}`}
                    />
                    <span className="min-w-0 break-words text-sm font-semibold text-[#f8f5fd]">
                      {actionOutcomeTitle(action)}
                    </span>
                  </label>
                  <span
                    className="mt-1 text-xs font-mono uppercase"
                    style={{
                      color:
                        action.status === 'failed' || action.isError ? '#fca5a5' : '#6ee7b7',
                    }}
                  >
                    {action.status}
                  </span>
                </div>
                <p className="mt-1 text-xs" style={{ color: 'rgba(248,245,253,0.5)' }}>
                  {['dispatch_agent', 'dispatch_subagents', 'add_to_knowledge_base'].includes(action.tool)
                    ? 'External write or execution'
                    : action.tool === 'get_agent_session_logs'
                      ? 'External read'
                      : 'Temporary structured result — not durably saved'}
                </p>
                <p className="mt-1 text-[11px] font-mono text-white/40">
                  Tool: {action.tool.replace(/_/g, ' ')}
                </p>
                {action.result && (
                  <p className="mt-1 text-xs leading-relaxed" style={{ color: 'rgba(172,170,177,0.9)' }}>
                    {action.result}
                  </p>
                )}
                <dl className="mt-3 space-y-2 border-t border-white/[0.07] pt-3">
                  {Object.entries(action.input || {}).map(([key, value]) => (
                    <div key={key} className="grid grid-cols-[110px_minmax(0,1fr)] gap-3 text-xs leading-5">
                      <dt className="break-words font-mono text-white/45">{key}</dt>
                      <dd className="min-w-0 break-words text-white/75">
                        {typeof value === 'string' ? value : JSON.stringify(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* F3: Plan surface — TranscriptActionAgent project_scaffold + package export */}
      <section
        className="rounded-xl border p-4 space-y-3"
        style={{ borderColor: 'rgba(52,211,153,0.2)', background: 'rgba(52,211,153,0.05)' }}
      >
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: '#6ee7b7' }}>
              Project scaffold
            </h3>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: 'rgba(248,245,253,0.55)' }}>
              Plan from analysis (<code className="text-[10px]">project_scaffold</code>) plus deterministic
              package files (README, tasks.json) for offline handoff.
            </p>
          </div>
          <button
            type="button"
            disabled={!canExport}
            onClick={exportScaffold}
            className="px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/50 rounded disabled:opacity-40"
            style={{
              background: 'rgba(52,211,153,0.15)',
              color: '#a7f3d0',
              border: '1px solid rgba(52,211,153,0.35)',
            }}
          >
            Export package
          </button>
        </div>

        {scaffoldPreview.length > 0 ? (
          <ul className="space-y-1.5">
            {scaffoldPreview.map((line) => (
              <li
                key={line}
                className="text-xs leading-relaxed rounded-lg px-3 py-2"
                style={{ background: 'rgba(0,0,0,0.2)', color: 'rgba(248,245,253,0.75)' }}
              >
                {line}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs" style={{ color: 'rgba(248,245,253,0.4)' }}>
            {plannedActions.length > 0
              ? `${plannedActions.length} planned action(s) from analysis — export builds tasks.json without a Gemini scaffold blob.`
              : 'Re-analyze with the backend transcript-action path to populate project_scaffold, or Act on findings then export.'}
          </p>
        )}
      </section>

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
  const [dispatchReview, setDispatchReview] = useState(false);
  const hasEvents = !!(video.events && video.events.length > 0);
  const agents = video.agents || [];
  const anyRunning = agents.some((a) => a.status === 'running' || a.status === 'queued');

  return (
    <div className="space-y-4">
      {(hasEvents || agents.length > 0) && (
        <div className="flex items-center justify-end gap-2 flex-wrap">
          {hasEvents && agentBackend && !dispatchReview && (
            <button
              type="button"
              onClick={() => setDispatchReview(true)}
              className="px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/50 rounded"
              style={{ background: 'rgba(129,140,248,0.15)', color: '#818cf8', border: '1px solid rgba(129,140,248,0.3)' }}
            >
              Review dispatch
            </button>
          )}
          {hasEvents && agentBackend && dispatchReview && (
            <>
              <span className="text-xs" style={{ color: '#fca5a5' }}>
                Dispatch {video.events!.length} event{video.events!.length === 1 ? '' : 's'} to backend agents?
              </span>
              <button
                type="button"
                onClick={() => setDispatchReview(false)}
                className="px-3 py-2 text-xs font-bold uppercase tracking-wider rounded"
                style={{ color: 'rgba(248,245,253,0.6)', border: '1px solid rgba(255,255,255,0.12)' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  setDispatchReview(false);
                  onDispatch(video.id);
                }}
                className="px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400/50 rounded"
                style={{ background: 'rgba(248,113,113,0.15)', color: '#fecaca', border: '1px solid rgba(248,113,113,0.35)' }}
              >
                Confirm dispatch
              </button>
            </>
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
          icon={<Bot className="h-10 w-10" strokeWidth={1.5} aria-hidden="true" />}
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
          className="flex-1 px-3 py-2.5 text-sm focus:outline-none transition-colors rounded-lg"
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
          icon={<Search className="h-10 w-10" strokeWidth={1.5} aria-hidden="true" />}
        >
          Search for a topic to jump to that moment in the video.
        </EmptyState>
      )}
    </div>
  );
}

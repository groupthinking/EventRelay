'use client';

import { Suspense, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import FeedbackWidget from '@/components/FeedbackWidget';
import { useDashboardDetail } from '@/hooks/use-dashboard-detail';
import { hasRichDashboardInsights, isThinDashboardAnalysis } from '@/lib/dashboard-analysis';
import type { PipelineMode, Video } from '@/store/dashboard-types';

function pipelineModeLabel(mode?: PipelineMode): string | null {
  switch (mode) {
    case 'live':
      return 'Live backend';
    case 'serverless':
      return 'Gemini analysis';
    case 'fallback':
      return 'Direct analysis';
    case 'handoff':
      return 'Offline handoff';
    default:
      return null;
  }
}

const TranscriptViewer = dynamic(() => import('@/components/TranscriptViewer'), {
  loading: () => (
    <div className="py-12 text-center text-sm text-white/40">Loading transcript viewer…</div>
  ),
});

const AgentDashboard = dynamic(() => import('@/components/AgentDashboard'), {
  loading: () => (
    <div className="py-12 text-center text-sm text-white/40">Loading agent dashboard…</div>
  ),
});

const EventList = dynamic(() => import('@/components/EventList'), {
  loading: () => (
    <div className="py-12 text-center text-sm text-white/40">Loading events…</div>
  ),
});

function getYouTubeEmbedUrl(url: string) {
  if (!url) return null;
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([^&?]+)/);
  return match ? `https://www.youtube.com/embed/${match[1]}` : null;
}

export interface DashboardSplitViewProps {
  video: Video;
  onClose: () => void;
  onExtractEvents?: (videoId: string) => void;
}

export default function DashboardSplitView({
  video,
  onClose,
  onExtractEvents,
}: DashboardSplitViewProps) {
  const [activeTab, setActiveTab] = useState<'analysis' | 'transcript' | 'actions' | 'agents' | 'search'>('analysis');
  const {
    searchQuery,
    setSearchQuery,
    performSearch,
    searchResults,
    searchLoading,
    dispatchToAgents,
    refreshAgentStatus,
  } = useDashboardDetail();

  const [agentBackend, setAgentBackend] = useState(false);
  useEffect(() => {
    let active = true;
    fetch('/api/agents/dispatch')
      .then((r) => r.json())
      .then((d) => { if (active) setAgentBackend(!!d.available); })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const embedUrl = getYouTubeEmbedUrl(video.url);
  const hasInsights = hasRichDashboardInsights(video);
  const thinAnalysis = isThinDashboardAnalysis(video);
  const hasTranscript = !!video.transcript;
  const hasEvents = video.events && video.events.length > 0;

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="w-[40%] flex flex-col min-w-[320px]" style={{ background: '#0e0e13', borderRight: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="p-4 flex items-center justify-between" style={{ background: 'rgba(25, 25, 31, 0.9)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <button
            onClick={onClose}
            className="flex items-center gap-2 text-sm transition-colors hover:text-white"
            style={{ color: 'rgba(248,245,253,0.4)', fontFamily: 'var(--font-heading)', letterSpacing: '0.05em', fontSize: '12px', textTransform: 'uppercase' }}
          >
            <span className="text-lg">←</span> Back to Library
          </button>
        </div>

        <div className="flex-none aspect-video bg-black relative">
          {embedUrl ? (
            <iframe
              src={embedUrl}
              className="w-full h-full border-0 absolute inset-0"
              allowFullScreen
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-white/30 text-sm gap-3">
              <span className="text-4xl">🎬</span>
              <span>Video player not available</span>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em]" style={{ color: 'rgba(248,245,253,0.35)' }}>
            <span>Dashboard</span>
            <span>›</span>
            <span style={{ color: '#6af2de' }}>Analysis</span>
          </div>
          <div>
            <h2 className="font-heading text-2xl font-bold tracking-tight mb-2" style={{ color: '#f8f5fd' }}>{video.title}</h2>
            <p className="text-sm break-all" style={{ color: 'rgba(248,245,253,0.3)' }}>{video.url}</p>
          </div>

          <div className="flex items-center gap-3">
            <span
              className="text-[10px] font-bold uppercase tracking-widest px-3 py-1"
              style={{
                background: thinAnalysis && video.status === 'complete'
                  ? 'rgba(245,158,11,0.1)'
                  : video.status === 'complete'
                    ? 'rgba(34,197,94,0.1)'
                    : video.status === 'failed'
                      ? 'rgba(255,113,108,0.1)'
                      : 'rgba(106,242,222,0.1)',
                color: thinAnalysis && video.status === 'complete'
                  ? '#f59e0b'
                  : video.status === 'complete'
                    ? '#22c55e'
                    : video.status === 'failed'
                      ? '#ff716c'
                      : '#6af2de',
                borderLeft: `2px solid ${
                  thinAnalysis && video.status === 'complete'
                    ? '#f59e0b'
                    : video.status === 'complete'
                      ? '#22c55e'
                      : video.status === 'failed'
                        ? '#ff716c'
                        : '#6af2de'
                }`,
              }}
            >
              {thinAnalysis && video.status === 'complete' ? 'PARTIAL' : video.status.toUpperCase()}
            </span>
            {video.status === 'processing' && <span className="text-sm font-mono" style={{ color: '#6af2de' }}>{video.progress}%</span>}
            {pipelineModeLabel(video.pipelineMode) && (
              <span
                className="text-[10px] font-bold uppercase tracking-widest px-3 py-1"
                style={{
                  background: 'rgba(106,242,222,0.06)',
                  border: '1px solid rgba(106,242,222,0.15)',
                  color: 'rgba(106,242,222,0.85)',
                }}
              >
                {pipelineModeLabel(video.pipelineMode)}
              </span>
            )}
          </div>

          {video.transcript && (
            <button
              onClick={() => {
                const blob = new Blob([video.transcript!], { type: 'text/plain' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = `transcript-${video.id}.txt`;
                a.click();
                URL.revokeObjectURL(a.href);
              }}
              className="w-full py-3 font-heading font-bold text-xs tracking-wider uppercase transition-all"
              style={{
                background: 'rgba(16, 183, 165, 0.9)',
                color: '#002b26',
                boxShadow: '0 0 15px rgba(16,183,165,0.3)',
              }}
            >
              Export Report
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col" style={{ background: '#131318', borderLeft: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(25, 25, 31, 0.9)' }}>
          {(['analysis', 'transcript', 'actions', 'agents', 'search'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="relative px-6 py-5 font-heading text-xs tracking-[0.2em] uppercase transition-colors"
              style={{
                color: activeTab === tab ? '#6af2de' : 'rgba(248,245,253,0.35)',
                borderBottom: activeTab === tab ? '2px solid #6af2de' : '2px solid transparent',
                background: activeTab === tab ? 'rgba(106, 242, 222, 0.05)' : 'transparent',
                fontWeight: activeTab === tab ? 700 : 500,
              }}
            >
              {tab === 'analysis' ? 'Summary' : tab}
              {tab === 'actions' && hasEvents && (
                <span className="absolute -top-1 -right-1 text-[9px] font-bold px-1.5 py-0.5 rounded-sm"
                  style={{ background: 'rgba(106,242,222,0.15)', color: '#6af2de' }}
                >
                  {video.events!.length}
                </span>
              )}
              {tab === 'agents' && video.agents && video.agents.length > 0 && (
                <span className="absolute -top-1 -right-1 text-[9px] font-bold px-1.5 py-0.5 rounded-sm"
                  style={{ background: 'rgba(129,140,248,0.15)', color: '#818cf8' }}
                >
                  {video.agents.length}
                </span>
              )}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-8 relative">
          {activeTab === 'analysis' && hasInsights && (
            <div className="max-w-3xl space-y-10 stitch-fade-in">
              <section>
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-1 h-6" style={{ background: '#6af2de' }} />
                  <h3 className="font-heading text-xl font-bold tracking-tight" style={{ color: '#f8f5fd' }}>Intelligence Synthesis</h3>
                </div>
                <div className="space-y-4 leading-relaxed text-lg" style={{ color: 'rgba(172, 170, 177, 1)' }}>
                  <p>{video.insights!.summary}</p>
                </div>
              </section>

              {video.insights!.topics.length > 0 && (
                <section>
                  <div className="flex items-center gap-3 mb-5">
                    <div className="w-1 h-6" style={{ background: '#6af2de' }} />
                    <h3 className="font-heading text-xl font-bold tracking-tight" style={{ color: '#f8f5fd' }}>Extracted Metadata</h3>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {video.insights!.topics.map((topic, i) => (
                      <span
                        key={topic}
                        className="text-[10px] font-bold uppercase tracking-widest px-3 py-1"
                        style={{
                          background: 'rgba(37, 37, 44, 1)',
                          color: i < 2 ? '#6af2de' : i < 4 ? '#69ccff' : 'rgba(172, 170, 177, 1)',
                        }}
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {video.insights!.actions.length > 0 && (
                <section>
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <div className="w-1 h-6" style={{ background: '#6af2de' }} />
                      <h3 className="font-heading text-xl font-bold tracking-tight" style={{ color: '#f8f5fd' }}>Directive Protocols</h3>
                    </div>
                    <span className="text-[10px] uppercase tracking-widest" style={{ color: 'rgba(248,245,253,0.35)' }}>
                      {video.insights!.actions.length} Pending Actions
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {video.insights!.actions.map((action, i) => (
                      <div
                        key={i}
                        className="p-6 cursor-pointer transition-all stitch-fade-in"
                        style={{
                          background: 'rgba(37, 37, 44, 0.4)',
                          backdropFilter: 'blur(20px)',
                          borderLeft: i === 0 ? '2px solid rgba(159, 5, 25, 0.8)' : '2px solid rgba(16, 183, 165, 0.8)',
                          animationDelay: `${i * 100}ms`,
                        }}
                      >
                        <div className="flex justify-between items-start mb-4">
                          <span
                            className="px-2 py-0.5 text-[10px] font-bold tracking-widest uppercase rounded-sm"
                            style={{
                              background: i === 0 ? 'rgba(159,5,25,0.2)' : 'rgba(16,183,165,0.2)',
                              color: i === 0 ? '#ff716c' : '#6af2de',
                            }}
                          >
                            {action.category || (i === 0 ? 'Critical' : 'Strategic')}
                          </span>
                          <input type="checkbox" className="h-4 w-4 rounded border-white/20 bg-transparent cursor-pointer" />
                        </div>
                        <p className="font-heading font-medium text-sm leading-tight mb-3" style={{ color: '#f8f5fd' }}>
                          {action.title}
                        </p>
                        {action.description && (
                          <p className="text-xs leading-relaxed" style={{ color: 'rgba(172, 170, 177, 0.8)' }}>
                            {action.description}
                          </p>
                        )}
                        {action.estimatedMinutes && (
                          <div className="flex items-center gap-2 mt-3 text-[10px]" style={{ color: 'rgba(248,245,253,0.35)' }}>
                            <span>⏱</span>
                            <span>Est. {action.estimatedMinutes}m</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}
              <FeedbackWidget videoId={video.id} tab="analysis" />
            </div>
          )}

          {activeTab === 'analysis' && !hasInsights && (
             <div className="flex flex-col items-center justify-center h-full text-center py-20">
               <div className="text-6xl mb-6 opacity-20">🧠</div>
               <p className="text-white/40 max-w-md">
                 {video.status === 'processing'
                   ? 'AI is currently analyzing the video. Insights will appear here shortly.'
                   : thinAnalysis
                     ? 'Agents finished but the backend returned minimal transcript/action data. Check Cloud Run logs for transcript-action, or retry from the library.'
                     : 'No analysis available for this video.'}
               </p>
             </div>
          )}

          {activeTab === 'transcript' && (
            hasTranscript ? (
              <div className="max-w-4xl mx-auto animate-fade-in-up">
                 <Suspense fallback={<div className="py-12 text-center text-sm text-white/40">Loading transcript viewer…</div>}>
                   <TranscriptViewer transcript={video.transcript!} />
                 </Suspense>
                 <FeedbackWidget videoId={video.id} tab="transcript" />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center py-20">
                <div className="text-6xl mb-6 opacity-20">📝</div>
                <p className="text-white/40">
                  {video.status === 'processing'
                    ? 'Transcript is being generated...'
                    : 'No transcript available.'}
                </p>
              </div>
            )
          )}

          {activeTab === 'actions' && (
            <div className="max-w-4xl mx-auto animate-fade-in-up">
              <Suspense fallback={<div className="py-12 text-center text-sm text-white/40">Loading events…</div>}>
                <EventList
                  events={video.events || []}
                  onExtract={onExtractEvents ? () => onExtractEvents(video.id) : undefined}
                />
              </Suspense>
              <FeedbackWidget videoId={video.id} tab="actions" />
            </div>
          )}

          {activeTab === 'agents' && (
            <div className="max-w-3xl mx-auto animate-fade-in-up">
              {(hasEvents || (video.agents && video.agents.length > 0)) && (
                <div className="flex items-center justify-end gap-2 mb-4 flex-wrap">
                  {hasEvents && agentBackend && (
                    <button
                      onClick={() => dispatchToAgents(video.id)}
                      className="px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all active:scale-95"
                      style={{ background: 'rgba(129,140,248,0.15)', color: '#818cf8', border: '1px solid rgba(129,140,248,0.3)' }}
                    >
                      ⚡ Dispatch {video.events!.length} events
                    </button>
                  )}
                  {(video.agents || []).some((a) => a.status === 'running' || a.status === 'queued') && (
                    <button
                      onClick={() => refreshAgentStatus(video.id)}
                      className="px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all active:scale-95"
                      style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(248,245,253,0.7)', border: '1px solid rgba(255,255,255,0.1)' }}
                    >
                      ↻ Refresh
                    </button>
                  )}
                </div>
              )}
              {hasEvents && !agentBackend && (
                <p className="text-xs mb-4 text-right" style={{ color: 'rgba(248,245,253,0.35)' }}>
                  Backend agents offline — deploy FastAPI + set BACKEND_URL to dispatch real MCP agents.
                </p>
              )}
              <Suspense fallback={<div className="py-12 text-center text-sm text-white/40">Loading agent dashboard…</div>}>
                <AgentDashboard
                  executions={video.agents || []}
                  loading={video.status === 'processing' && !(video.agents && video.agents.length > 0)}
                />
              </Suspense>
              {video.status !== 'processing' && !(video.agents && video.agents.length > 0) && (
                <div className="flex flex-col items-center justify-center text-center py-16">
                  <div className="text-6xl mb-6 opacity-20">🤖</div>
                  <p className="text-white/40">No agent executions yet.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'search' && (
            <div className="max-w-4xl mx-auto animate-fade-in-up space-y-6">
              <div className="p-6" style={{ background: 'rgba(37, 37, 44, 0.4)', backdropFilter: 'blur(20px)' }}>
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-1 h-6" style={{ background: '#6af2de' }} />
                  <h3 className="font-heading text-lg font-bold tracking-tight" style={{ color: '#f8f5fd' }}>Semantic Search</h3>
                </div>
                <form
                  onSubmit={(e) => {
                     e.preventDefault();
                     performSearch(video.id, searchQuery);
                  }}
                  className="flex gap-3"
                >
                  <input
                    type="text"
                    placeholder="Search the video (e.g. 'architecture diagram' or 'next js deploy')..."
                    className="flex-1 px-4 py-3 text-sm focus:outline-none transition-colors"
                    style={{ background: 'rgba(25, 25, 31, 0.8)', border: '1px solid rgba(106, 242, 222, 0.15)', color: '#f8f5fd' }}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  <button
                    type="submit"
                    className="px-6 py-3 font-heading font-bold text-xs tracking-wider uppercase transition-all disabled:opacity-30 active:scale-95"
                    style={{ background: 'rgba(16, 183, 165, 0.9)', color: '#002b26', boxShadow: '0 0 15px rgba(16,183,165,0.3)' }}
                    disabled={searchLoading || !searchQuery.trim()}
                  >
                    {searchLoading ? 'Searching...' : 'Search'}
                  </button>
                </form>
              </div>

              {searchResults.length > 0 ? (
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-white/40 uppercase tracking-wider">Top Results</h4>
                  {searchResults.map((res, i) => (
                    <div key={i} className="bg-surface-800 p-5 rounded-xl border border-white/[0.05] hover:border-primary-500/30 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono text-primary-400 bg-primary-500/10 px-2 py-1 rounded">
                          {new Date(res.start * 1000).toISOString().substr(11, 8)} - {new Date((res.start + res.duration) * 1000).toISOString().substr(11, 8)}
                        </span>
                        <span className="text-xs text-white/30 font-mono">
                          Score: {(res.score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-sm text-white/70 leading-relaxed">{res.text}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-10 opacity-50">
                  <span className="text-4xl block mb-3">💬</span>
                  <p>Ask a question or search for a specific topic within the video.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
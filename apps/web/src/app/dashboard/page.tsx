'use client';

import { Suspense, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { clsx } from 'clsx';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';
import TranscriptViewer from '@/components/TranscriptViewer';
import EventList from '@/components/EventList';
import type { ExtractedEvent } from '@/lib/types';
import { useDashboardStore } from '@/store/dashboard-store';
import type { PipelineResult, Video } from '@/store/dashboard-store';

// ============================================
// Helper
// ============================================
function getYouTubeEmbedUrl(url: string) {
  if (!url) return null;
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([^&?]+)/);
  return match ? `https://www.youtube.com/embed/${match[1]}` : null;
}

// ============================================
// Processing Stage Indicator
// ============================================
function ProcessingStage({
  stage,
  isActive,
  isComplete
}: {
  stage: string;
  isActive: boolean;
  isComplete: boolean;
}) {
  return (
    <div
      className={clsx(
        'flex items-center gap-2 px-3 py-1.5 text-xs font-bold uppercase tracking-widest transition-all duration-300',
        isComplete && 'text-green-400',
        isActive && 'text-[#6af2de]',
        !isComplete && !isActive && 'text-white/25'
      )}
      style={{
        background: isComplete ? 'rgba(34, 197, 94, 0.08)' : isActive ? 'rgba(106, 242, 222, 0.08)' : 'rgba(37, 37, 44, 0.4)',
        borderLeft: isComplete ? '2px solid #22c55e' : isActive ? '2px solid #6af2de' : '2px solid transparent',
      }}
    >
      {isComplete && <span className="text-green-400">✓</span>}
      {isActive && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ background: '#6af2de' }} />
          <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: '#6af2de' }} />
        </span>
      )}
      {stage}
    </div>
  );
}

// ============================================
// Split View (Active State)
// ============================================
function SplitView({
  video,
  onClose,
  onExtractEvents,
}: {
  video: Video;
  onClose: () => void;
  onExtractEvents?: (videoId: string) => void;
}) {
  const [activeTab, setActiveTab] = useState<'analysis' | 'transcript' | 'actions' | 'search'>('analysis');
  const searchQuery = useDashboardStore((s) => s.searchQuery);
  const setSearchQuery = useDashboardStore((s) => s.setSearchQuery);
  const performSearch = useDashboardStore((s) => s.performSearch);
  const searchResults = useDashboardStore((s) => s.searchResults);
  const searchLoading = useDashboardStore((s) => s.searchLoading);

  const embedUrl = getYouTubeEmbedUrl(video.url);

  const hasInsights = video.insights && (video.insights.summary !== 'Analysis complete' || video.insights.actions.length > 0);
  const hasTranscript = !!video.transcript;
  const hasEvents = video.events && video.events.length > 0;

  const stages = video.pipelineResult !== undefined
    ? ['Ingest', 'Generate', 'Deploy', 'Live']
    : ['Ingest', 'Transcribe', 'Analyze', 'Extract'];
  const currentStage = Math.floor((video.progress / 100) * stages.length);

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Left Panel (40%) - Video & Metadata */}
      <div className="w-[40%] flex flex-col min-w-[320px]" style={{ background: '#0e0e13', borderRight: '1px solid rgba(255,255,255,0.05)' }}>
        {/* Header */}
        <div className="p-4 flex items-center justify-between" style={{ background: 'rgba(25, 25, 31, 0.9)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <button
            onClick={onClose}
            className="flex items-center gap-2 text-sm transition-colors hover:text-white"
            style={{ color: 'rgba(248,245,253,0.4)', fontFamily: 'var(--font-heading)', letterSpacing: '0.05em', fontSize: '12px', textTransform: 'uppercase' }}
          >
            <span className="text-lg">←</span> Back to Library
          </button>
        </div>

        {/* Video Player */}
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

        {/* Scrollable Metadata */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Breadcrumb */}
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
                background: video.status === 'complete' ? 'rgba(34,197,94,0.1)' : video.status === 'failed' ? 'rgba(255,113,108,0.1)' : 'rgba(106,242,222,0.1)',
                color: video.status === 'complete' ? '#22c55e' : video.status === 'failed' ? '#ff716c' : '#6af2de',
                borderLeft: `2px solid ${video.status === 'complete' ? '#22c55e' : video.status === 'failed' ? '#ff716c' : '#6af2de'}`,
              }}
            >
              {video.status.toUpperCase()}
            </span>
            {video.status === 'processing' && <span className="text-sm font-mono" style={{ color: '#6af2de' }}>{video.progress}%</span>}
          </div>

          {/* Processing stages */}
          {video.status === 'processing' && (
            <div className="flex flex-col gap-1 p-5" style={{ background: 'rgba(37, 37, 44, 0.4)', backdropFilter: 'blur(20px)' }}>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-1 h-4" style={{ background: '#6af2de' }} />
                <h3 className="font-heading text-xs font-bold uppercase tracking-widest" style={{ color: '#f8f5fd' }}>Processing Pipeline</h3>
              </div>
              {stages.map((stage, i) => (
                <ProcessingStage
                  key={stage}
                  stage={stage}
                  isActive={i === currentStage}
                  isComplete={i < currentStage}
                />
              ))}
            </div>
          )}

          {/* Export action */}
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

      {/* Right Panel (60%) - Intelligence Feed */}
      <div className="flex-1 flex flex-col" style={{ background: '#131318', borderLeft: '1px solid rgba(255,255,255,0.05)' }}>
        {/* Tabs */}
        <div className="flex" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(25, 25, 31, 0.9)' }}>
          {(['analysis', 'transcript', 'actions', 'search'] as const).map((tab) => (
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
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-8 relative">
          {activeTab === 'analysis' && hasInsights && (
            <div className="max-w-3xl space-y-10 stitch-fade-in">
              {/* Summary */}
              <section>
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-1 h-6" style={{ background: '#6af2de' }} />
                  <h3 className="font-heading text-xl font-bold tracking-tight" style={{ color: '#f8f5fd' }}>Intelligence Synthesis</h3>
                </div>
                <div className="space-y-4 leading-relaxed text-lg" style={{ color: 'rgba(172, 170, 177, 1)' }}>
                  <p>{video.insights!.summary}</p>
                </div>
              </section>

              {/* Topics */}
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

              {/* Sentiments & Action Items */}
              {/* Directive Protocols (Action Items) */}
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
            </div>
          )}

          {activeTab === 'analysis' && !hasInsights && (
             <div className="flex flex-col items-center justify-center h-full text-center py-20">
               <div className="text-6xl mb-6 opacity-20">🧠</div>
               <p className="text-white/40 max-w-md">
                 {video.status === 'processing'
                   ? 'AI is currently analyzing the video. Insights will appear here shortly.'
                   : 'No analysis available for this video.'}
               </p>
             </div>
          )}

          {activeTab === 'transcript' && (
            hasTranscript ? (
              <div className="max-w-4xl mx-auto animate-fade-in-up">
                 <TranscriptViewer transcript={video.transcript!} />
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
              {/* EventList component assumes it receives events and optional onExtract */}
              <EventList
                events={video.events || []}
                onExtract={onExtractEvents ? () => onExtractEvents(video.id) : undefined}
              />
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
                  {searchResults.map((res: any, i: number) => (
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

// ============================================
// Video Card Component (Library View)
// ============================================
function VideoCard({
  video,
  onClick
}: {
  video: Video;
  onClick: () => void;
}) {
  const stages = video.pipelineResult !== undefined
    ? ['Ingest', 'Generate', 'Deploy', 'Live']
    : ['Ingest', 'Transcribe', 'Analyze', 'Extract'];
  const currentStage = Math.floor((video.progress / 100) * stages.length);

  return (
    <div
      onClick={onClick}
      className={clsx(
        'group relative overflow-hidden rounded-2xl cursor-pointer',
        'bg-surface-900/50 backdrop-blur-xl flex flex-col',
        'border border-white/[0.08] hover:border-primary-500/30',
        'transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-primary-500/10'
      )}
    >
      <div className="relative aspect-video bg-surface-800 overflow-hidden flex-none">
        {video.thumbnail ? (
          <img
            src={video.thumbnail}
            alt={video.title}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-5xl bg-gradient-to-br from-surface-800 to-surface-900">
            🎬
          </div>
        )}

        {video.status === 'processing' && (
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center">
            <div className="text-center">
              <div className="relative w-16 h-16 mx-auto mb-3 overflow-hidden">
                <svg className="w-16 h-16 animate-spin" width="64" height="64" viewBox="0 0 24 24">
                  <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" />
                  <circle
                    className="text-primary-500" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none"
                    strokeDasharray="62.83" strokeDashoffset={62.83 * (1 - video.progress / 100)} strokeLinecap="round"
                    transform="rotate(-90 12 12)"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">
                  {video.progress}%
                </span>
              </div>
            </div>
          </div>
        )}

        <div className={clsx(
          'absolute top-3 left-3 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider backdrop-blur-md',
          video.status === 'complete' && 'bg-green-500/90 text-white',
          video.status === 'failed' && 'bg-red-500/90 text-white',
          video.status === 'processing' && 'bg-primary-500/90 text-white'
        )}>
          {video.status}
        </div>
      </div>

      <div className="p-5 flex flex-col flex-1">
        <h3 className="font-bold text-white truncate group-hover:text-primary-400 transition-colors mb-1.5">
          {video.title}
        </h3>
        <p className="text-xs text-white/40 truncate mb-4">{video.url}</p>

        {video.status === 'processing' && (
          <div className="flex flex-wrap gap-1.5 mt-auto">
            {stages.map((stage, i) => (
              <ProcessingStage key={stage} stage={stage} isActive={i === currentStage} isComplete={i < currentStage} />
            ))}
          </div>
        )}

        {video.status === 'complete' && video.insights && (
          <div className="mt-auto flex flex-wrap gap-2 pt-4 border-t border-white/[0.05]">
            {video.insights.topics.slice(0, 2).map((topic) => (
              <span key={topic} className="px-2 py-1 bg-white/[0.05] text-white/70 rounded border border-white/[0.05] text-[10px] font-medium truncate max-w-[100px]">
                {topic}
              </span>
            ))}
            {video.events && video.events.length > 0 && (
              <span className="px-2 py-1 bg-primary-500/10 text-primary-400 rounded border border-primary-500/20 text-[10px] font-bold">
                {video.events.length} Actions
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================
// Dashboard Content wrapper
// ============================================
function DashboardContent() {
  const searchParams = useSearchParams();
  const [videoUrl, setVideoUrl] = useState('');
  const [filter, setFilter] = useState<'all' | 'processing' | 'complete' | 'failed'>('all');

  const videos = useDashboardStore((s) => s.videos);
  const selectedVideoId = useDashboardStore((s) => s.selectedVideoId);
  const selectVideo = useDashboardStore((s) => s.selectVideo);
  const processVideo = useDashboardStore((s) => s.processVideo);
  const extractEvents = useDashboardStore((s) => s.extractEvents);

  const selectedVideo = videos.find((v) => v.id === selectedVideoId) || null;

  useEffect(() => {
    const video = searchParams.get('video');
    if (video) {
      setVideoUrl(video);
      processVideo(video).then((id) => {
        selectVideo(id);
      });
    }
  }, [searchParams, processVideo, selectVideo]);

  const handleAddVideo = useCallback(() => {
    if (!videoUrl.trim()) return;
    const url = videoUrl;
    setVideoUrl('');
    processVideo(url).then((id) => {
      selectVideo(id);
    });
  }, [videoUrl, processVideo, selectVideo]);

  const filteredVideos = filter === 'all' ? videos : videos.filter((v) => v.status === filter);
  const processingCount = videos.filter((v) => v.status === 'processing').length;

  return (
    <div className="h-screen flex flex-col text-white overflow-hidden bg-surface-950">
      {/* Top Nav (Always visible) */}
      <Nav
        subtitle="Dashboard"
        rightSlot={
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard/agents"
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-400 font-bold uppercase tracking-wider hover:bg-indigo-500/20 transition-all"
            >
              ⚡ Agent Pipeline
            </Link>
            {processingCount > 0 ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-500/10 border border-primary-500/20">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-400" />
                </span>
                <span className="text-xs text-primary-400 font-bold uppercase tracking-wider">{processingCount} Processing</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
                <span className="text-xs text-green-400 font-bold uppercase tracking-wider">Ready</span>
              </div>
            )}
        </div>
        }
      />

      {/* Main Content Area */}
      {selectedVideo ? (
        <SplitView
          video={selectedVideo}
          onClose={() => selectVideo(null)}
          onExtractEvents={extractEvents}
        />
      ) : (
        <div className="flex-1 overflow-y-auto p-6 lg:p-10">
          <div className="max-w-6xl mx-auto space-y-10">
            {/* Input Section */}
            <div className="p-10 flex flex-col items-center justify-center text-center" style={{ background: 'rgba(25, 25, 31, 0.8)', border: '1px solid rgba(106, 242, 222, 0.08)' }}>
              <span className="text-[10px] tracking-[0.3em] uppercase mb-4 block" style={{ color: '#6af2de', fontFamily: 'var(--font-heading)' }}>Video Intelligence Engine</span>
              <h1 className="font-heading text-4xl font-bold tracking-tighter mb-3" style={{ color: '#f8f5fd' }}>Analyze New Video</h1>
              <p className="mb-8 max-w-lg" style={{ color: 'rgba(248,245,253,0.4)' }}>
                Paste a YouTube URL to extract intelligence, generate transcripts, and identify actionable events.
              </p>
              <form onSubmit={(e) => { e.preventDefault(); handleAddVideo(); }} className="w-full max-w-2xl">
                <div className="flex gap-2 p-2 rounded-xl transition-all" style={{ background: 'rgba(25, 25, 31, 0.8)', border: '1px solid rgba(106, 242, 222, 0.15)' }}>
                  <input
                    type="text"
                    value={videoUrl}
                    onChange={(e) => setVideoUrl(e.target.value)}
                    placeholder="https://youtube.com/watch?v=..."
                    className="flex-1 px-4 py-3 bg-transparent text-white placeholder:text-white/20 focus:outline-none text-sm"
                  />
                  <button
                    type="submit"
                    disabled={!videoUrl.trim()}
                    className="px-8 py-3 font-bold text-sm transition-all active:scale-95 disabled:opacity-30"
                    style={{ background: 'linear-gradient(135deg, #6af2de, #10b7a5)', color: '#002b26' }}
                  >
                    Analyze Footage
                  </button>
                </div>
              </form>
            </div>

            {/* Library Section */}
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-1 h-6" style={{ background: '#6af2de' }} />
                  <h2 className="font-heading text-xl font-bold tracking-tight" style={{ color: '#f8f5fd' }}>Your Library</h2>
                </div>
                <div className="flex p-1" style={{ background: 'rgba(25, 25, 31, 0.8)', border: '1px solid rgba(72, 71, 77, 0.15)' }}>
                  {(['all', 'processing', 'complete', 'failed'] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className="px-4 py-1.5 text-xs font-heading font-bold uppercase tracking-widest transition-all"
                      style={{
                        color: filter === f ? '#6af2de' : 'rgba(248,245,253,0.35)',
                        background: filter === f ? 'rgba(106, 242, 222, 0.08)' : 'transparent',
                      }}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              {filteredVideos.length === 0 ? (
                <div className="py-20 text-center border border-dashed border-white/[0.1] rounded-3xl bg-white/[0.01]">
                  <p className="text-white/50 font-medium mb-2">No videos yet</p>
                  <p className="text-white/30 text-sm mb-6 max-w-sm mx-auto">Paste a YouTube URL above to analyze your first video and start building your library.</p>
                  <button
                    onClick={() => document.querySelector<HTMLInputElement>('input[type="text"]')?.focus()}
                    className="btn btn-primary px-5 py-2.5 text-sm"
                  >
                    Analyze a video
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {filteredVideos.map((video) => (
                    <VideoCard key={video.id} video={video} onClick={() => selectVideo(video.id)} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={
      <div className="h-screen bg-surface-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    }>
      <DashboardContent />
    </Suspense>
  );
}
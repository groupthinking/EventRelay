'use client';

import { Suspense, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { clsx } from 'clsx';
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
        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300',
        isComplete && 'bg-green-500/15 text-green-400 border border-green-500/20',
        isActive && 'bg-primary-500/15 text-primary-400 border border-primary-500/20',
        !isComplete && !isActive && 'bg-white/[0.03] text-white/30 border border-white/[0.05]'
      )}
    >
      {isComplete && <span className="text-green-400">✓</span>}
      {isActive && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-400" />
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
      <div className="w-[40%] flex flex-col border-r border-white/[0.05] bg-surface-900 min-w-[320px]">
        {/* Header */}
        <div className="p-4 flex items-center justify-between border-b border-white/[0.05] bg-surface-950">
          <button
            onClick={onClose}
            className="flex items-center gap-2 text-sm text-white/50 hover:text-white transition-colors"
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
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">{video.title}</h2>
            <p className="text-sm text-white/40 break-all">{video.url}</p>
          </div>

          <div className="flex items-center gap-3">
            <span
              className={clsx(
                'px-3 py-1.5 rounded-lg text-xs font-semibold',
                video.status === 'complete' && 'bg-green-500/20 text-green-400',
                video.status === 'failed' && 'bg-red-500/20 text-red-400',
                video.status === 'processing' && 'bg-primary-500/20 text-primary-400 animate-pulse'
              )}
            >
              {video.status.toUpperCase()}
            </span>
            {video.status === 'processing' && <span className="text-sm text-white/50">{video.progress}%</span>}
          </div>

          {/* Processing stages */}
          {video.status === 'processing' && (
            <div className="flex flex-col gap-2 p-4 bg-white/[0.02] rounded-xl border border-white/[0.05]">
              <h3 className="text-xs font-medium text-white/40 uppercase tracking-wider mb-2">Processing Pipeline</h3>
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
              className="w-full py-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-sm font-medium transition-all"
            >
              Download Raw Transcript
            </button>
          )}
        </div>
      </div>

      {/* Right Panel (60%) - Intelligence Feed */}
      <div className="flex-1 flex flex-col bg-surface-900/50">
        {/* Tabs */}
        <div className="flex items-center px-6 border-b border-white/[0.05] gap-8 bg-surface-950/30">
          {(['analysis', 'transcript', 'actions', 'search'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(
                'py-4 text-sm font-medium capitalize border-b-2 transition-colors relative',
                activeTab === tab
                  ? 'border-primary-500 text-primary-400'
                  : 'border-transparent text-white/40 hover:text-white/70'
              )}
            >
              {tab}
              {tab === 'actions' && hasEvents && (
                <span className="absolute -top-1 -right-4 text-[10px] bg-primary-500/20 text-primary-400 px-1.5 py-0.5 rounded-full">
                  {video.events!.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-8 relative">
          {activeTab === 'analysis' && hasInsights && (
            <div className="max-w-3xl space-y-8 animate-fade-in-up">
              {/* Summary */}
              <section>
                <h3 className="text-sm font-bold text-white/50 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <span className="text-primary-500">❖</span> Executive Summary
                </h3>
                <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
                  <p className="text-white/80 leading-relaxed text-lg">{video.insights!.summary}</p>
                </div>
              </section>

              {/* Topics */}
              {video.insights!.topics.length > 0 && (
                <section>
                  <h3 className="text-sm font-bold text-white/50 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <span className="text-blue-500">❖</span> Key Topics
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {video.insights!.topics.map((topic) => (
                      <span
                        key={topic}
                        className="px-4 py-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 text-sm font-medium"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {/* Sentiments & Action Items */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {video.insights!.actions.length > 0 && (
                  <section className="col-span-full md:col-span-1">
                    <h3 className="text-sm font-bold text-white/50 uppercase tracking-wider mb-4 flex items-center gap-2">
                      <span className="text-green-500">❖</span> Extracted Tasks
                    </h3>
                    <ul className="space-y-4">
                      {video.insights!.actions.map((action, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.05] transition-colors"
                        >
                          <input
                            type="checkbox"
                            className="mt-1.5 h-4 w-4 rounded border-white/20 bg-white/5 text-primary-500 cursor-pointer"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              {action.category && (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-primary-500/10 text-primary-400 border border-primary-500/20">
                                  {action.category}
                                </span>
                              )}
                              {action.estimatedMinutes && (
                                <span className="text-xs text-white/40">
                                  ⏱ {action.estimatedMinutes}m
                                </span>
                              )}
                            </div>
                            <h4 className="text-white/90 text-sm font-semibold leading-relaxed">
                              {action.title}
                            </h4>
                            {action.description && (
                              <p className="text-white/60 text-xs mt-1 leading-relaxed">
                                {action.description}
                              </p>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}
              </div>
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
              <div className="bg-white/[0.02] border border-white/[0.05] p-6 rounded-2xl">
                <h3 className="text-sm font-bold text-white/50 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <span className="text-primary-500">🔍</span> Multimodal Semantic Search
                </h3>
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
                    className="flex-1 bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-primary-500/50 outline-none transition-colors"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  <button 
                    type="submit"
                    className="px-6 py-3 bg-primary-500 text-white font-bold rounded-xl hover:bg-primary-600 transition-colors disabled:opacity-50"
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
      processVideo(video);
    }
  }, [searchParams, processVideo]);

  const handleAddVideo = useCallback(() => {
    if (!videoUrl.trim()) return;
    const url = videoUrl;
    setVideoUrl('');
    processVideo(url);
  }, [videoUrl, processVideo]);

  const filteredVideos = filter === 'all' ? videos : videos.filter((v) => v.status === filter);
  const processingCount = videos.filter((v) => v.status === 'processing').length;

  return (
    <div className="h-screen flex flex-col text-white overflow-hidden bg-surface-950">
      {/* Top Nav (Always visible) */}
      <nav className="flex-none flex items-center justify-between px-6 py-4 border-b border-white/[0.05] bg-surface-900 z-50">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-sm shadow-lg shadow-primary-500/25">
              U
            </div>
            <span className="font-bold tracking-tight">UVAI</span>
          </Link>
          <div className="h-5 w-px bg-white/[0.08]" />
          <span className="text-white/50 font-medium text-sm">Dashboard</span>
        </div>
        
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
      </nav>

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
            <div className="bg-surface-900/50 p-8 rounded-3xl border border-white/[0.05] flex flex-col items-center justify-center text-center">
              <h1 className="text-3xl font-black mb-3">Analyze New Video</h1>
              <p className="text-white/40 mb-8 max-w-lg">
                Paste a YouTube URL to extract intelligence, generate transcripts, and identify actionable events.
              </p>
              <form onSubmit={(e) => { e.preventDefault(); handleAddVideo(); }} className="w-full max-w-2xl flex gap-3">
                <div className="flex-1 flex items-center bg-white/[0.03] border border-white/[0.08] rounded-2xl px-4 py-2 focus-within:border-primary-500/50 focus-within:ring-2 focus-within:ring-primary-500/10 transition-all">
                  <span className="text-white/30 mr-2">🔗</span>
                  <input
                    type="text"
                    value={videoUrl}
                    onChange={(e) => setVideoUrl(e.target.value)}
                    placeholder="https://youtube.com/watch?v=..."
                    className="flex-1 bg-transparent border-none outline-none text-white placeholder:text-white/30"
                  />
                </div>
                <button
                  type="submit"
                  disabled={!videoUrl.trim()}
                  className="btn btn-primary py-3 px-8 rounded-2xl font-bold tracking-wide disabled:opacity-50"
                >
                  Analyze
                </button>
              </form>
            </div>

            {/* Library Section */}
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold flex items-center gap-3">
                  <span className="p-1.5 rounded-lg bg-white/[0.05] border border-white/[0.05]">📚</span>
                  Your Library
                </h2>
                <div className="flex bg-white/[0.02] p-1 rounded-xl border border-white/[0.05]">
                  {(['all', 'processing', 'complete', 'failed'] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={clsx(
                        'px-4 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all',
                        filter === f ? 'bg-white/10 text-white shadow-sm' : 'text-white/40 hover:text-white/70 hover:bg-white/[0.02]'
                      )}
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
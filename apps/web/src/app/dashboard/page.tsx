'use client';

import { Suspense, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { clsx } from 'clsx';
import AnalysisPanel from '@/components/AnalysisPanel';
import TranscriptViewer from '@/components/TranscriptViewer';
import EventList from '@/components/EventList';
import type { ExtractedEvent } from '@/lib/types';
import { useDashboardStore } from '@/store/dashboard-store';
import type { PipelineResult, Video } from '@/store/dashboard-store';

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
// Video Card Component
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
        'bg-surface-900/50 backdrop-blur-xl',
        'border border-white/[0.08] hover:border-primary-500/30',
        'transition-all duration-300 hover:-translate-y-1',
        'hover:shadow-xl hover:shadow-primary-500/10'
      )}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-surface-800 overflow-hidden">
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

        {/* Processing overlay */}
        {video.status === 'processing' && (
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center">
            <div className="text-center">
              <div className="relative w-16 h-16 mx-auto mb-3 overflow-hidden">
                <svg className="w-16 h-16 animate-spin" width="64" height="64" viewBox="0 0 24 24">
                  <circle
                    className="opacity-20"
                    cx="12" cy="12" r="10"
                    stroke="currentColor"
                    strokeWidth="2"
                    fill="none"
                  />
                  <circle
                    className="text-primary-500"
                    cx="12" cy="12" r="10"
                    stroke="currentColor"
                    strokeWidth="2"
                    fill="none"
                    strokeDasharray="62.83"
                    strokeDashoffset={62.83 * (1 - video.progress / 100)}
                    strokeLinecap="round"
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

        {/* Status badge */}
        <div
          className={clsx(
            'absolute top-3 left-3 px-2.5 py-1 rounded-lg text-xs font-semibold backdrop-blur-sm',
            video.status === 'complete' && 'bg-green-500/90 text-white',
            video.status === 'failed' && 'bg-red-500/90 text-white',
            video.status === 'processing' && 'bg-primary-500/90 text-white'
          )}
        >
          {video.status.charAt(0).toUpperCase() + video.status.slice(1)}
        </div>
      </div>

      {/* Info */}
      <div className="p-5">
        <h3 className="font-semibold text-white truncate group-hover:text-primary-400 transition-colors">
          {video.title}
        </h3>
        <p className="text-sm text-white/40 truncate mt-1.5">{video.url}</p>

        {/* Processing stages */}
        {video.status === 'processing' && (
          <div className="flex flex-wrap gap-2 mt-4">
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

        {/* Quick insights for completed */}
        {video.status === 'complete' && video.insights && (
          <div className="mt-4 pt-4 border-t border-white/[0.05]">
            {/* Pipeline deployment result */}
            {video.pipelineResult && (
              <div className="mb-3 space-y-2">
                {video.pipelineResult.live_url && (
                  <a
                    href={video.pipelineResult.live_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-3 py-2 bg-green-500/10 border border-green-500/20 rounded-lg text-sm text-green-400 hover:bg-green-500/20 transition-colors"
                  >
                    🌐 <span className="font-medium">Live:</span> <span className="truncate">{video.pipelineResult.live_url}</span>
                  </a>
                )}
                {video.pipelineResult.github_repo && (
                  <a
                    href={video.pipelineResult.github_repo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-3 py-2 bg-purple-500/10 border border-purple-500/20 rounded-lg text-sm text-purple-400 hover:bg-purple-500/20 transition-colors"
                  >
                    📦 <span className="font-medium">Repo:</span> <span className="truncate">{video.pipelineResult.github_repo}</span>
                  </a>
                )}
                {video.pipelineResult.code_generation && (
                  <div className="flex items-center gap-2 text-xs text-white/40">
                    <span>Framework: {video.pipelineResult.code_generation.framework}</span>
                    <span>•</span>
                    <span>{video.pipelineResult.code_generation.files_created.length} files</span>
                  </div>
                )}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {video.insights.topics.slice(0, 3).map((topic) => (
                <span
                  key={topic}
                  className="px-2.5 py-1 bg-primary-500/10 text-primary-400 border border-primary-500/20 rounded-lg text-xs font-medium"
                >
                  {topic}
                </span>
              ))}
              {video.events && video.events.length > 0 && (
                <span className="px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-lg text-xs font-medium">
                  {video.events.length} events
                </span>
              )}
            </div>
          </div>
        )}

        {/* Failed state */}
        {video.status === 'failed' && (
          <p className="mt-3 text-xs text-red-400/70">Processing failed. Click to retry.</p>
        )}
      </div>
    </div>
  );
}

// ============================================
// Quick Start Guide (shown when no videos)
// ============================================
const STARTER_VIDEOS = [
  { label: 'Y Combinator lecture', url: 'https://www.youtube.com/watch?v=aircAruvnKk' },
  { label: 'Tech conference talk', url: 'https://www.youtube.com/watch?v=zjkBMFhNj_g' },
];

function QuickStartGuide({ onLoad }: { onLoad: (url: string) => void }) {
  return (
    <div className={clsx(
      'bg-surface-900/50 backdrop-blur-xl rounded-2xl p-6',
      'border border-white/[0.08]'
    )}>
      <h3 className="font-semibold text-white mb-2">Quick Start</h3>
      <p className="text-xs text-white/40 mb-5 leading-relaxed">
        Paste any YouTube URL or try one of these examples to see EventRelay in action.
      </p>
      <div className="space-y-2">
        {STARTER_VIDEOS.map((v) => (
          <button
            key={v.url}
            onClick={() => onLoad(v.url)}
            className="w-full flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-primary-500/30 hover:bg-primary-500/5 transition-all text-left group"
          >
            <span className="text-xl">▶️</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white/80 group-hover:text-white transition truncate">
                {v.label}
              </p>
              <p className="text-xs text-white/30 truncate">{v.url.replace('https://www.youtube.com/watch?v=', 'youtu.be/')}</p>
            </div>
            <span className="text-primary-400 opacity-0 group-hover:opacity-100 transition text-xs font-semibold">
              Try →
            </span>
          </button>
        ))}
      </div>

      <div className="mt-5 pt-5 border-t border-white/[0.06]">
        <div className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-3">What you&apos;ll get</div>
        <ul className="space-y-2">
          {['Full transcript', 'Extracted events & actions', 'AI-powered insights', 'Searchable video chat'].map((item) => (
            <li key={item} className="flex items-center gap-2 text-xs text-white/50">
              <span className="text-green-400">✓</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// ============================================
// Stats Summary Card (shown when has videos)
// ============================================
function StatsSummary({
  videoCount,
  completedCount,
  totalEvents,
}: {
  videoCount: number;
  completedCount: number;
  totalEvents: number;
}) {
  return (
    <div className={clsx(
      'bg-surface-900/50 backdrop-blur-xl rounded-2xl p-6',
      'border border-white/[0.08]'
    )}>
      <h3 className="font-semibold text-white mb-4">Session Stats</h3>
      <div className="grid grid-cols-3 gap-3">
        {[
          { value: videoCount, label: 'Videos', icon: '🎬' },
          { value: completedCount, label: 'Done', icon: '✅' },
          { value: totalEvents, label: 'Events', icon: '⚡' },
        ].map((s) => (
          <div key={s.label} className="text-center p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
            <div className="text-lg mb-1">{s.icon}</div>
            <div className="text-xl font-black text-white">{s.value}</div>
            <div className="text-[10px] text-white/35 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Activity Feed
// ============================================
function ActivityFeed({
  activities,
}: {
  activities: { time: string; event: string; type: 'success' | 'info' | 'error' }[];
}) {
  if (activities.length === 0) {
    return (
      <div className={clsx(
        'bg-surface-900/50 backdrop-blur-xl rounded-2xl p-6',
        'border border-white/[0.08]'
      )}>
        <h3 className="font-semibold text-white mb-4">Activity</h3>
        <p className="text-sm text-white/30 text-center py-6">
          Process a video to see activity here.
        </p>
      </div>
    );
  }

  return (
    <div className={clsx(
      'bg-surface-900/50 backdrop-blur-xl rounded-2xl p-6',
      'border border-white/[0.08]'
    )}>
      <h3 className="font-semibold text-white mb-5">Activity</h3>
      <div className="space-y-4 max-h-72 overflow-y-auto pr-2">
        {activities.map((activity, i) => (
          <div
            key={i}
            className="flex items-start gap-3 text-sm animate-fade-in-up opacity-0"
            style={{ animationDelay: `${i * 50}ms`, animationFillMode: 'forwards' }}
          >
            <div className="relative mt-1.5 flex-shrink-0">
              <div
                className={clsx(
                  'w-2.5 h-2.5 rounded-full',
                  activity.type === 'success' && 'bg-green-400',
                  activity.type === 'error' && 'bg-red-400',
                  activity.type === 'info' && 'bg-blue-400'
                )}
              />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white/80 leading-snug text-xs">{activity.event}</p>
              <p className="text-white/30 text-[10px] mt-0.5">{activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Export Button (for completed videos)
// ============================================
function ExportMenu({ videos }: { videos: Video[] }) {
  const [open, setOpen] = useState(false);
  const completed = videos.filter((v) => v.status === 'complete');
  if (completed.length === 0) return null;

  const exportJSON = () => {
    const data = completed.map((v) => ({
      title: v.title,
      transcript: v.transcript,
      events: v.events,
      insights: v.insights,
    }));
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `eventrelay-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    setOpen(false);
  };

  const exportCSV = () => {
    const rows = ['Video Title,Event Type,Event Title,Timestamp,Confidence'];
    completed.forEach((v) => {
      (v.events || []).forEach((e) => {
        rows.push(`"${v.title}","${e.type}","${e.title}","${e.timestamp || ''}","${Math.round(e.confidence * 100)}%"`);
      });
    });
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `eventrelay-events-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="btn btn-secondary py-2 px-4 text-sm flex items-center gap-2"
      >
        <span>↓</span> Export
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-2 w-48 bg-surface-900 border border-white/[0.12] rounded-xl shadow-2xl z-30 overflow-hidden">
          <button
            onClick={exportJSON}
            className="w-full text-left px-4 py-3 text-sm text-white/80 hover:bg-white/[0.06] transition flex items-center gap-2"
          >
            <span>&#123;&#125;</span> Export JSON
          </button>
          <button
            onClick={exportCSV}
            className="w-full text-left px-4 py-3 text-sm text-white/80 hover:bg-white/[0.06] transition flex items-center gap-2 border-t border-white/[0.06]"
          >
            <span>📊</span> Export CSV
          </button>
        </div>
      )}
    </div>
  );
}

// ============================================
// Video Detail Modal
// ============================================
function VideoDetailModal({
  video,
  onClose,
  onExtractEvents,
}: {
  video: Video;
  onClose: () => void;
  onExtractEvents?: (videoId: string) => void;
}) {
  const [showAssistant, setShowAssistant] = useState(false);
  const [activeTab, setActiveTab] = useState<'insights' | 'transcript' | 'events'>('insights');

  const hasInsights = video.insights && (video.insights.summary !== 'Analysis complete' || video.insights.actions.length > 0);
  const hasTranscript = !!video.transcript;
  const hasEvents = video.events && video.events.length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
      onClick={onClose}
    >
      <div
        className={clsx(
          'bg-surface-900 rounded-3xl border border-white/[0.08] flex overflow-hidden transition-all duration-500',
          showAssistant ? 'max-w-5xl w-full h-[85vh]' : 'max-w-2xl w-full max-h-[85vh]',
          'shadow-2xl shadow-black/50 animate-scale-in'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Main Content */}
        <div className={clsx(
          "flex flex-col flex-1 min-w-0 transition-opacity duration-300",
          showAssistant ? "border-r border-white/[0.08]" : ""
        )}>
          {/* Header */}
          <div className="p-6 border-b border-white/[0.08]">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0 pr-4">
                <h2 className="text-xl font-bold text-white truncate">{video.title}</h2>
                <div className="flex items-center gap-3 mt-1.5">
                  <p className="text-white/40 text-sm truncate">{video.url}</p>
                  {video.status === 'complete' && (
                    <span className="flex-shrink-0 px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 text-xs font-medium">
                      ✓ Complete
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="w-10 h-10 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] flex items-center justify-center text-white/60 hover:text-white transition-all"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="px-6 border-b border-white/[0.08] flex gap-1">
            {(['insights', 'transcript', 'events'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={clsx(
                  'px-4 py-3 text-sm font-medium capitalize transition-colors border-b-2 -mb-px',
                  activeTab === tab
                    ? 'border-primary-500 text-primary-400'
                    : 'border-transparent text-white/40 hover:text-white/60'
                )}
              >
                {tab}
                {tab === 'events' && hasEvents && (
                  <span className="ml-1.5 text-xs bg-primary-500/20 text-primary-400 px-1.5 py-0.5 rounded-full">
                    {video.events!.length}
                  </span>
                )}
                {tab === 'insights' && video.insights?.actions && video.insights.actions.length > 0 && (
                  <span className="ml-1.5 text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded-full">
                    {video.insights.actions.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {activeTab === 'insights' && hasInsights && (
              <>
                {/* Summary */}
                <div>
                  <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                    Summary
                  </h3>
                  <p className="text-white/80 leading-relaxed">{video.insights!.summary}</p>
                </div>

                {/* Action Items */}
                {video.insights!.actions.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                      Action Items
                    </h3>
                    <ul className="space-y-2">
                      {video.insights!.actions.map((action, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-3 p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:bg-white/[0.05] transition-colors"
                        >
                          <input
                            type="checkbox"
                            className="mt-0.5 h-4 w-4 rounded border-white/20 bg-white/5 text-primary-500 focus:ring-primary-500/50"
                          />
                          <span className="text-white/80">{action}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Sentiment */}
                {video.insights!.sentiment && video.insights!.sentiment !== 'Neutral' && (
                  <div>
                    <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                      Sentiment
                    </h3>
                    <span className="px-3 py-1.5 rounded-lg bg-white/[0.05] text-white/70 text-sm">
                      {video.insights!.sentiment}
                    </span>
                  </div>
                )}

                {/* Topics */}
                {video.insights!.topics.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                      Topics
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {video.insights!.topics.map((topic) => (
                        <span
                          key={topic}
                          className="px-4 py-2 rounded-full bg-primary-500/15 text-primary-400 border border-primary-500/25 text-sm font-medium"
                        >
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {activeTab === 'insights' && !hasInsights && (
              <div className="text-center py-12">
                <div className="text-4xl mb-3 opacity-40">🧠</div>
                <p className="text-sm text-white/30">
                  {video.status === 'processing'
                    ? 'Insights will appear once processing completes.'
                    : 'No insights available for this video.'}
                </p>
              </div>
            )}

            {activeTab === 'transcript' && (
              hasTranscript ? (
                <TranscriptViewer transcript={video.transcript!} />
              ) : (
                <div className="text-center py-12">
                  <div className="text-4xl mb-3 opacity-40">📝</div>
                  <p className="text-sm text-white/30">
                    {video.status === 'processing'
                      ? 'Transcript is being generated...'
                      : 'No transcript available.'}
                  </p>
                </div>
              )
            )}

            {activeTab === 'events' && (
              <EventList
                events={video.events || []}
                onExtract={onExtractEvents ? () => onExtractEvents(video.id) : undefined}
              />
            )}
          </div>

          {/* Footer Actions */}
          <div className="p-6 border-t border-white/[0.08] bg-surface-900/50">
            <div className="flex gap-3">
              <button
                onClick={() => setShowAssistant(!showAssistant)}
                className={clsx(
                  "flex-1 btn py-3 transition-all flex items-center justify-center gap-2",
                  showAssistant ? "btn-secondary" : "btn-primary"
                )}
              >
                <span className="text-xl">🤖</span>
                {showAssistant ? "Hide Assistant" : "Ask About This Video"}
              </button>
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
                  className="btn btn-secondary py-3 px-6"
                >
                  Export Transcript
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Assistant Side Panel */}
        {showAssistant && (
          <div className="w-[400px] h-full">
            <AnalysisPanel
              videoId={video.id}
              videoUrl={video.url}
              onClose={() => setShowAssistant(false)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================
// Dashboard Content
// ============================================
function DashboardContent() {
  const searchParams = useSearchParams();
  const [videoUrl, setVideoUrl] = useState('');
  const [filter, setFilter] = useState<'all' | 'processing' | 'complete' | 'failed'>('all');

  // Zustand store
  const videos = useDashboardStore((s) => s.videos);
  const activities = useDashboardStore((s) => s.activities);
  const selectedVideoId = useDashboardStore((s) => s.selectedVideoId);
  const selectVideo = useDashboardStore((s) => s.selectVideo);
  const processVideo = useDashboardStore((s) => s.processVideo);
  const deployPipeline = useDashboardStore((s) => s.deployPipeline);
  const extractEvents = useDashboardStore((s) => s.extractEvents);

  const selectedVideo = videos.find((v) => v.id === selectedVideoId) || null;

  const filteredVideos = filter === 'all'
    ? videos
    : videos.filter((v) => v.status === filter);

  const completedCount = videos.filter((v) => v.status === 'complete').length;
  const processingCount = videos.filter((v) => v.status === 'processing').length;
  const totalEvents = videos.reduce((sum, v) => sum + (v.events?.length || 0), 0);

  useEffect(() => {
    const video = searchParams.get('video');
    if (video) {
      setVideoUrl(video);
      processVideo(video);
    }
  }, [searchParams, processVideo]);

  const handleAddVideo = useCallback(
    (url?: string) => {
      const targetUrl = url || videoUrl;
      if (!targetUrl.trim()) return;
      setVideoUrl('');
      processVideo(targetUrl);
    },
    [videoUrl, processVideo],
  );

  const handleDeployPipeline = useCallback(
    () => {
      const targetUrl = videoUrl;
      if (!targetUrl.trim()) return;
      setVideoUrl('');
      deployPipeline(targetUrl);
    },
    [videoUrl, deployPipeline],
  );

  return (
    <div className="min-h-screen text-white">
      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-6 lg:px-12 py-4 border-b border-white/[0.05]">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-lg shadow-lg shadow-primary-500/25">
              E
            </div>
            <span className="font-bold text-xl tracking-tight">EventRelay</span>
          </Link>
          <div className="h-6 w-px bg-white/[0.08]" />
          <span className="text-white/50 font-medium">Dashboard</span>
        </div>
        <div className="flex items-center gap-4">
          {processingCount > 0 && (
            <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-primary-500/10 border border-primary-500/20">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-400" />
              </span>
              <span className="text-sm text-primary-400 font-medium">{processingCount} Processing</span>
            </div>
          )}
          {processingCount === 0 && (
            <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-green-500/10 border border-green-500/20">
              <span className="relative flex h-2 w-2">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
              </span>
              <span className="text-sm text-green-400 font-medium">Ready</span>
            </div>
          )}
          <Link href="/playground" className="btn btn-secondary py-2 text-sm">
            API Docs
          </Link>
        </div>
      </nav>

      <div className="relative z-10 max-w-7xl mx-auto p-6 lg:p-8">
        {/* Header + Input */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-3 tracking-tight">
            Video Intelligence
          </h1>
          <p className="text-white/50 text-lg mb-6">
            Process, analyze, and extract insights from any video
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAddVideo();
            }}
            className="flex gap-3 max-w-2xl"
          >
            <div className="flex-1 flex gap-3 p-2 rounded-2xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl focus-within:border-primary-500/30 transition-all">
              <input
                type="text"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="Paste YouTube URL..."
                className="flex-1 px-5 py-3 bg-transparent text-white placeholder:text-white/30 focus:outline-none"
              />
              <button
                type="submit"
                disabled={!videoUrl.trim()}
                className="btn btn-primary py-3 px-8 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Analyze
              </button>
              <button
                type="button"
                disabled={!videoUrl.trim()}
                onClick={handleDeployPipeline}
                className="btn py-3 px-6 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400 hover:to-emerald-500 text-white font-semibold rounded-xl shadow-lg shadow-green-500/25 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                🚀 Deploy
              </button>
            </div>
          </form>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Video Library */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">Video Library</h2>
              <div className="flex gap-2 flex-wrap">
                {videos.length > 0 && (
                  <ExportMenu videos={videos} />
                )}
                {(['all', 'processing', 'complete', 'failed'] as const).map((f) => {
                  const count = f === 'all' ? videos.length : videos.filter(v => v.status === f).length;
                  if (f !== 'all' && count === 0) return null;
                  return (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={clsx(
                        'px-4 py-2 rounded-xl text-sm font-medium transition-all capitalize',
                        filter === f
                          ? 'bg-primary-500/15 text-primary-400 border border-primary-500/20'
                          : 'bg-white/[0.03] text-white/50 border border-white/[0.05] hover:bg-white/[0.06]'
                      )}
                    >
                      {f} {count > 0 && `(${count})`}
                    </button>
                  );
                })}
              </div>
            </div>

            {filteredVideos.length === 0 && videos.length === 0 ? (
              <div className="col-span-full flex flex-col items-center justify-center py-20 rounded-2xl border border-dashed border-white/[0.1] bg-white/[0.02]">
                <div className="text-6xl mb-4">🎬</div>
                <h3 className="text-xl font-bold text-white mb-2">Start with any video</h3>
                <p className="text-white/40 text-sm text-center max-w-sm mb-6">
                  Paste a YouTube URL in the field above, or pick an example from the Quick Start guide on the right.
                </p>
                <div className="flex flex-wrap gap-3 justify-center">
                  {STARTER_VIDEOS.map((v) => (
                    <button
                      key={v.url}
                      onClick={() => handleAddVideo(v.url)}
                      className="px-4 py-2 rounded-xl bg-primary-500/10 text-primary-400 border border-primary-500/20 hover:bg-primary-500/20 transition text-sm font-medium"
                    >
                      Try: {v.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : filteredVideos.length === 0 ? (
              <div className="text-center py-12 text-white/30 text-sm">
                No {filter} videos.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {filteredVideos.map((video) => (
                  <VideoCard
                    key={video.id}
                    video={video}
                    onClick={() => selectVideo(video.id)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-5">
            {videos.length > 0 && (
              <StatsSummary
                videoCount={videos.length}
                completedCount={completedCount}
                totalEvents={totalEvents}
              />
            )}
            {videos.length === 0 ? (
              <QuickStartGuide onLoad={handleAddVideo} />
            ) : (
              <ActivityFeed activities={activities} />
            )}
            {videos.length > 0 && activities.length > 0 && (
              <div className={clsx(
                'bg-surface-900/50 backdrop-blur-xl rounded-2xl p-5',
                'border border-white/[0.08]'
              )}>
                <div className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-3">Tips</div>
                <ul className="space-y-2 text-xs text-white/45 leading-relaxed">
                  <li>• Click any video card to see full insights</li>
                  <li>• Use "Ask About This Video" to chat with AI</li>
                  <li>• Export events to CSV or JSON</li>
                  <li>• Deploy button generates and deploys code</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal */}
      {selectedVideo && (
        <VideoDetailModal
          video={selectedVideo}
          onClose={() => selectVideo(null)}
          onExtractEvents={extractEvents}
        />
      )}
    </div>
  );
}

// ============================================
// Loading Fallback
// ============================================
function DashboardLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="relative w-20 h-20 mx-auto mb-6">
          <div className="absolute inset-0 rounded-full border-4 border-primary-500/20" />
          <div className="absolute inset-0 rounded-full border-4 border-primary-500 border-t-transparent animate-spin" />
        </div>
        <p className="text-white/50 font-medium">Loading dashboard...</p>
      </div>
    </div>
  );
}

// ============================================
// Export with Suspense
// ============================================
export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardLoading />}>
      <DashboardContent />
    </Suspense>
  );
}
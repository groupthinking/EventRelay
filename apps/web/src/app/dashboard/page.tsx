'use client';

import { Suspense, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { clsx } from 'clsx';

// ============================================
// Types
// ============================================
interface Video {
  id: string;
  title: string;
  url: string;
  status: 'processing' | 'complete' | 'failed';
  progress: number;
  thumbnail?: string;
  duration?: string;
  processedAt?: string;
  insights?: {
    summary: string;
    actions: string[];
    sentiment: string;
    topics: string[];
  };
}

interface DashboardMetrics {
  status: string;
  timestamp: string;
  metrics: {
    activeWorkflows: number;
    totalProcessed: number;
    errorRate: number;
  };
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
// Video Card Component
// ============================================
function VideoCard({
  video,
  onClick
}: {
  video: Video;
  onClick: () => void;
}) {
  const stages = ['Ingest', 'Transcribe', 'Analyze', 'Generate'];
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
              <div className="relative w-16 h-16 mx-auto mb-3">
                <svg className="w-16 h-16 animate-spin" viewBox="0 0 24 24">
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

        {/* Duration badge */}
        {video.duration && (
          <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/80 backdrop-blur-sm rounded-lg text-xs text-white/80 font-medium">
            {video.duration}
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

        {/* Quick insights */}
        {video.status === 'complete' && video.insights && (
          <div className="mt-4 pt-4 border-t border-white/[0.05]">
            <div className="flex flex-wrap gap-2">
              {video.insights.topics.slice(0, 3).map((topic) => (
                <span
                  key={topic}
                  className="px-2.5 py-1 bg-primary-500/10 text-primary-400 border border-primary-500/20 rounded-lg text-xs font-medium"
                >
                  {topic}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================
// Metric Card Component
// ============================================
function MetricCard({
  value,
  label,
  icon,
  trend,
  trendUp = true,
}: {
  value: string | number;
  label: string;
  icon: string;
  trend?: string;
  trendUp?: boolean;
}) {
  return (
    <div className={clsx(
      'bg-surface-900/50 backdrop-blur-xl rounded-2xl p-6',
      'border border-white/[0.08]',
      'transition-all duration-300 hover:border-primary-500/20',
      'hover:shadow-lg hover:shadow-primary-500/5'
    )}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-white/40 text-sm font-medium">{label}</p>
          <p className="text-4xl font-bold text-white mt-2 tracking-tight">{value}</p>
          {trend && (
            <p className={clsx(
              'text-sm mt-3 font-medium flex items-center gap-1',
              trendUp ? 'text-green-400' : 'text-red-400'
            )}>
              <span>{trendUp ? '↑' : '↓'}</span>
              {trend} vs last week
            </p>
          )}
        </div>
        <div className="text-4xl opacity-80">{icon}</div>
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
  return (
    <div className={clsx(
      'bg-surface-900/50 backdrop-blur-xl rounded-2xl p-6',
      'border border-white/[0.08]'
    )}>
      <h3 className="font-semibold text-white mb-5">Activity Feed</h3>
      <div className="space-y-4 max-h-72 overflow-y-auto pr-2">
        {activities.map((activity, i) => (
          <div
            key={i}
            className="flex items-start gap-3 text-sm animate-fade-in-up opacity-0"
            style={{ animationDelay: `${i * 50}ms`, animationFillMode: 'forwards' }}
          >
            <div className="relative mt-1.5">
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
              <p className="text-white/80 leading-snug">{activity.event}</p>
              <p className="text-white/30 text-xs mt-1">{activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Quick Actions
// ============================================
function QuickActions() {
  const actions = [
    { icon: '📊', label: 'Generate Weekly Report', primary: true },
    { icon: '🔗', label: 'Connect Integration', primary: false },
    { icon: '📤', label: 'Export All Insights', primary: false },
  ];

  return (
    <div className={clsx(
      'bg-surface-900/50 backdrop-blur-xl rounded-2xl p-6',
      'border border-white/[0.08]'
    )}>
      <h3 className="font-semibold text-white mb-5">Quick Actions</h3>
      <div className="space-y-3">
        {actions.map((action, i) => (
          <button
            key={i}
            className={clsx(
              'w-full px-4 py-3.5 rounded-xl text-sm font-medium text-left transition-all duration-200',
              'flex items-center gap-3',
              action.primary
                ? 'bg-primary-500/10 border border-primary-500/20 text-primary-400 hover:bg-primary-500/20'
                : 'bg-white/[0.03] border border-white/[0.08] text-white/80 hover:bg-white/[0.06]'
            )}
          >
            <span className="text-lg">{action.icon}</span>
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Video Detail Modal
// ============================================
function VideoDetailModal({
  video,
  onClose,
}: {
  video: Video;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in-up"
      onClick={onClose}
    >
      <div
        className={clsx(
          'bg-surface-900 rounded-3xl border border-white/[0.08]',
          'max-w-2xl w-full max-h-[85vh] overflow-y-auto',
          'shadow-2xl shadow-black/50',
          'animate-scale-in'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-white/[0.08]">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0 pr-4">
              <h2 className="text-xl font-bold text-white truncate">{video.title}</h2>
              <p className="text-white/40 text-sm mt-1.5 truncate">{video.url}</p>
            </div>
            <button
              onClick={onClose}
              className="w-10 h-10 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] flex items-center justify-center text-white/60 hover:text-white transition-all"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        {video.insights && (
          <div className="p-6 space-y-6">
            {/* Summary */}
            <div>
              <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                Summary
              </h3>
              <p className="text-white/80 leading-relaxed">{video.insights.summary}</p>
            </div>

            {/* Action Items */}
            <div>
              <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                Action Items
              </h3>
              <ul className="space-y-2">
                {video.insights.actions.map((action, i) => (
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

            {/* Topics */}
            <div>
              <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">
                Topics
              </h3>
              <div className="flex flex-wrap gap-2">
                {video.insights.topics.map((topic) => (
                  <span
                    key={topic}
                    className="px-4 py-2 rounded-full bg-primary-500/15 text-primary-400 border border-primary-500/25 text-sm font-medium"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-6 border-t border-white/[0.08]">
              <button className="flex-1 btn btn-primary py-3">Deploy as App</button>
              <button className="btn btn-secondary py-3 px-6">Export</button>
              <button className="btn btn-secondary py-3 px-6">Share</button>
            </div>
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
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [videoUrl, setVideoUrl] = useState('');
  const [videos, setVideos] = useState<Video[]>([
    {
      id: '1',
      title: 'React Hooks Deep Dive Tutorial',
      url: 'https://youtube.com/watch?v=abc123',
      status: 'complete',
      progress: 100,
      duration: '45:32',
      processedAt: '2 hours ago',
      insights: {
        summary:
          'Comprehensive guide to React hooks including useState, useEffect, useCallback, and custom hooks.',
        actions: [
          'Implement useState for form handling',
          'Add useEffect for API calls',
          'Create custom useAuth hook',
        ],
        sentiment: 'Educational',
        topics: ['React', 'Hooks', 'JavaScript', 'Frontend'],
      },
    },
    {
      id: '2',
      title: 'Q4 Strategy Meeting Recording',
      url: 'https://drive.google.com/file/xyz',
      status: 'processing',
      progress: 65,
      duration: '1:23:45',
    },
    {
      id: '3',
      title: 'Product Demo for Enterprise Client',
      url: 'https://youtube.com/watch?v=def456',
      status: 'complete',
      progress: 100,
      duration: '12:08',
      processedAt: '1 day ago',
      insights: {
        summary:
          'Product demonstration showcasing key features for enterprise deployment.',
        actions: [
          'Follow up with client on pricing',
          'Schedule technical deep-dive',
          'Send case studies',
        ],
        sentiment: 'Positive',
        topics: ['Sales', 'Demo', 'Enterprise', 'Features'],
      },
    },
  ]);

  const [activities] = useState([
    { time: 'Just now', event: 'Video analysis complete: React Hooks Tutorial', type: 'success' as const },
    { time: '2 min ago', event: 'Processing started: Q4 Strategy Meeting', type: 'info' as const },
    { time: '5 min ago', event: 'New video added to queue', type: 'info' as const },
    { time: '15 min ago', event: 'Generated 3 action items from Demo video', type: 'success' as const },
    { time: '1 hour ago', event: 'API rate limit reached - auto-retry scheduled', type: 'error' as const },
  ]);

  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);

  useEffect(() => {
    const video = searchParams.get('video');
    if (video) {
      setVideoUrl(video);
      handleAddVideo(video);
    }
  }, [searchParams]);

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const res = await fetch('/api/dashboard');
        const data = await res.json();
        setMetrics(data);
      } catch (error) {
        console.error('Failed to fetch metrics:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAddVideo = useCallback(
    async (url?: string) => {
      const targetUrl = url || videoUrl;
      if (!targetUrl.trim()) return;

      const newVideo: Video = {
        id: Date.now().toString(),
        title: `Analyzing: ${targetUrl.length > 50 ? targetUrl.substring(0, 47) + '...' : targetUrl}`,
        url: targetUrl,
        status: 'processing',
        progress: 10,
      };
      setVideos((prev) => [newVideo, ...prev]);
      setVideoUrl('');

      const progressInterval = setInterval(() => {
        setVideos((prev) =>
          prev.map((v) =>
            v.id === newVideo.id && v.status === 'processing'
              ? { ...v, progress: Math.min(v.progress + 5, 95) }
              : v
          )
        );
      }, 1000);

      try {
        const response = await fetch('/api/video', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: targetUrl }),
        });

        clearInterval(progressInterval);

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const result = await response.json();

        setVideos((prev) =>
          prev.map((v) =>
            v.id === newVideo.id
              ? {
                  ...v,
                  status: result.status === 'complete' ? 'complete' : 'failed',
                  progress: 100,
                  title: result.result?.insights?.summary?.substring(0, 50) + '...' || 'Analyzed Video',
                  processedAt: 'Just now',
                  duration: `${result.result?.transcript_segments || 0} segments`,
                  insights: {
                    summary: result.result?.insights?.summary || 'Analysis complete',
                    actions: result.result?.insights?.actions || [],
                    sentiment: result.result?.insights?.sentiment || 'Neutral',
                    topics: result.result?.insights?.topics || ['Analyzed'],
                  },
                }
              : v
          )
        );
      } catch (error) {
        clearInterval(progressInterval);
        console.error('Video analysis failed:', error);

        setVideos((prev) =>
          prev.map((v) =>
            v.id === newVideo.id ? { ...v, status: 'failed', progress: 0 } : v
          )
        );
      }
    },
    [videoUrl]
  );

  return (
    <div className="min-h-screen text-white">
      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-6 lg:px-12 py-4 border-b border-white/[0.05]">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-lg shadow-lg shadow-primary-500/25">
              U
            </div>
            <span className="font-bold text-xl tracking-tight">UVAI.io</span>
          </Link>
          <div className="h-6 w-px bg-white/[0.08]" />
          <span className="text-white/50 font-medium">Dashboard</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-green-500/10 border border-green-500/20">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
            </span>
            <span className="text-sm text-green-400 font-medium">System Online</span>
          </div>
          <Link
            href="/playground"
            className="btn btn-secondary py-2"
          >
            API Docs
          </Link>
        </div>
      </nav>

      <div className="relative z-10 max-w-7xl mx-auto p-6 lg:p-8">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-3xl md:text-4xl font-bold mb-3 tracking-tight">
            Video Intelligence Dashboard
          </h1>
          <p className="text-white/50 text-lg mb-8">
            Process, analyze, and extract insights from any video
          </p>

          {/* Video Input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAddVideo();
            }}
            className="flex gap-3 max-w-2xl"
          >
            <div className="flex-1 flex gap-3 p-2 rounded-2xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl">
              <input
                type="text"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="Paste YouTube URL, Google Drive link, or upload..."
                className="flex-1 px-5 py-3 bg-transparent text-white placeholder:text-white/30 focus:outline-none"
              />
              <button
                type="submit"
                className="btn btn-primary py-3 px-8"
              >
                Analyze
              </button>
            </div>
          </form>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
          <MetricCard
            value={metrics?.metrics.activeWorkflows ?? 0}
            label="Active Workflows"
            icon="⚡"
            trend="+12%"
            trendUp={true}
          />
          <MetricCard
            value={metrics?.metrics.totalProcessed ?? 0}
            label="Videos Processed"
            icon="🎬"
            trend="+28%"
            trendUp={true}
          />
          <MetricCard
            value="2.3s"
            label="Avg Processing Time"
            icon="⏱️"
            trend="-15%"
            trendUp={true}
          />
          <MetricCard
            value={`${metrics?.metrics.errorRate ?? 0}%`}
            label="Error Rate"
            icon="✓"
          />
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Video Library */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">Video Library</h2>
              <div className="flex gap-2">
                {['All', 'Processing', 'Complete'].map((filter, i) => (
                  <button
                    key={filter}
                    className={clsx(
                      'px-4 py-2 rounded-xl text-sm font-medium transition-all',
                      i === 0
                        ? 'bg-primary-500/15 text-primary-400 border border-primary-500/20'
                        : 'bg-white/[0.03] text-white/50 border border-white/[0.05] hover:bg-white/[0.06]'
                    )}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {videos.map((video) => (
                <VideoCard
                  key={video.id}
                  video={video}
                  onClick={() => setSelectedVideo(video)}
                />
              ))}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <ActivityFeed activities={activities} />
            <QuickActions />
          </div>
        </div>
      </div>

      {/* Modal */}
      {selectedVideo && (
        <VideoDetailModal
          video={selectedVideo}
          onClose={() => setSelectedVideo(null)}
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
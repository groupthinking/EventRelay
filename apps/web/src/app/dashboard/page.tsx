'use client';

import { Suspense, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

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

// Processing stage indicator
function ProcessingStage({ stage, isActive, isComplete }: { stage: string; isActive: boolean; isComplete: boolean }) {
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
      isComplete ? 'bg-green-500/20 text-green-400' :
      isActive ? 'bg-violet-500/20 text-violet-400 animate-pulse' :
      'bg-white/5 text-white/40'
    }`}>
      {isComplete && <span>✓</span>}
      {isActive && <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-ping" />}
      {stage}
    </div>
  );
}

// Video card component
function VideoCard({ video, onClick }: { video: Video; onClick: () => void }) {
  const stages = ['Ingest', 'Transcribe', 'Analyze', 'Generate'];
  const currentStage = Math.floor((video.progress / 100) * stages.length);

  return (
    <div
      onClick={onClick}
      className="group bg-slate-900/50 backdrop-blur-xl rounded-xl border border-white/10 hover:border-violet-500/50 transition-all cursor-pointer overflow-hidden"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-slate-800">
        {video.thumbnail ? (
          <img src={video.thumbnail} alt={video.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">🎬</div>
        )}
        {/* Progress overlay */}
        {video.status === 'processing' && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full border-4 border-violet-500 border-t-transparent animate-spin mb-2" />
              <span className="text-sm text-white/80">{video.progress}%</span>
            </div>
          </div>
        )}
        {/* Duration badge */}
        {video.duration && (
          <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/80 rounded text-xs text-white/80">
            {video.duration}
          </div>
        )}
        {/* Status badge */}
        <div className={`absolute top-2 left-2 px-2 py-1 rounded text-xs font-medium ${
          video.status === 'complete' ? 'bg-green-500/80 text-white' :
          video.status === 'failed' ? 'bg-red-500/80 text-white' :
          'bg-violet-500/80 text-white'
        }`}>
          {video.status}
        </div>
      </div>

      {/* Info */}
      <div className="p-4">
        <h3 className="font-medium text-white truncate group-hover:text-violet-400 transition">{video.title}</h3>
        <p className="text-sm text-white/40 truncate mt-1">{video.url}</p>

        {/* Processing stages */}
        {video.status === 'processing' && (
          <div className="flex flex-wrap gap-2 mt-3">
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
          <div className="mt-3 pt-3 border-t border-white/5">
            <div className="flex flex-wrap gap-2">
              {video.insights.topics.slice(0, 3).map(topic => (
                <span key={topic} className="px-2 py-1 bg-violet-500/10 text-violet-400 rounded text-xs">
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

// Metric card component
function MetricCard({ value, label, icon, trend }: { value: string | number; label: string; icon: string; trend?: string }) {
  return (
    <div className="bg-slate-900/50 backdrop-blur-xl rounded-xl border border-white/10 p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-white/40 text-sm">{label}</p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
          {trend && (
            <p className={`text-sm mt-2 ${trend.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>
              {trend} vs last week
            </p>
          )}
        </div>
        <div className="text-3xl">{icon}</div>
      </div>
    </div>
  );
}

// Real-time activity feed
function ActivityFeed({ activities }: { activities: { time: string; event: string; type: 'success' | 'info' | 'error' }[] }) {
  return (
    <div className="bg-slate-900/50 backdrop-blur-xl rounded-xl border border-white/10 p-6">
      <h3 className="font-medium text-white mb-4">Activity Feed</h3>
      <div className="space-y-3 max-h-64 overflow-y-auto">
        {activities.map((activity, i) => (
          <div key={i} className="flex items-start gap-3 text-sm">
            <div className={`w-2 h-2 rounded-full mt-1.5 ${
              activity.type === 'success' ? 'bg-green-400' :
              activity.type === 'error' ? 'bg-red-400' :
              'bg-blue-400'
            }`} />
            <div>
              <p className="text-white/80">{activity.event}</p>
              <p className="text-white/30 text-xs">{activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

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
        summary: 'Comprehensive guide to React hooks including useState, useEffect, useCallback, and custom hooks.',
        actions: ['Implement useState for form handling', 'Add useEffect for API calls', 'Create custom useAuth hook'],
        sentiment: 'Educational',
        topics: ['React', 'Hooks', 'JavaScript', 'Frontend']
      }
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
        summary: 'Product demonstration showcasing key features for enterprise deployment.',
        actions: ['Follow up with client on pricing', 'Schedule technical deep-dive', 'Send case studies'],
        sentiment: 'Positive',
        topics: ['Sales', 'Demo', 'Enterprise', 'Features']
      }
    }
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
    // Check for video URL from query params
    const video = searchParams.get('video');
    if (video) {
      setVideoUrl(video);
      // Auto-submit if URL provided
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

    // Poll for updates
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAddVideo = useCallback(async (url?: string) => {
    const targetUrl = url || videoUrl;
    if (!targetUrl.trim()) return;

    // Add new video to list with processing state
    const newVideo: Video = {
      id: Date.now().toString(),
      title: `Analyzing: ${targetUrl.length > 50 ? targetUrl.substring(0, 47) + '...' : targetUrl}`,
      url: targetUrl,
      status: 'processing',
      progress: 10,
    };
    setVideos(prev => [newVideo, ...prev]);
    setVideoUrl('');

    // Update progress while waiting
    const progressInterval = setInterval(() => {
      setVideos(prev => prev.map(v =>
        v.id === newVideo.id && v.status === 'processing'
          ? { ...v, progress: Math.min(v.progress + 5, 95) }
          : v
      ));
    }, 1000);

    try {
      // Call the real backend API
      const response = await fetch('/api/video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: targetUrl })
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const result = await response.json();

      // Update video with real results
      setVideos(prev => prev.map(v =>
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
                topics: result.result?.insights?.topics || ['Analyzed']
              }
            }
          : v
      ));
    } catch (error) {
      clearInterval(progressInterval);
      console.error('Video analysis failed:', error);

      setVideos(prev => prev.map(v =>
        v.id === newVideo.id
          ? { ...v, status: 'failed', progress: 0 }
          : v
      ));
    }
  }, [videoUrl]);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Gradient background */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-violet-900/10 via-slate-950 to-slate-950" />

      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center font-black text-lg">
              U
            </div>
            <span className="font-bold text-xl">UVAI.io</span>
          </Link>
          <div className="h-6 w-px bg-white/10" />
          <span className="text-white/60">Dashboard</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-sm text-green-400">System Online</span>
          </div>
          <Link
            href="https://api.uvai.io/docs"
            target="_blank"
            className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm hover:bg-white/10 transition"
          >
            API Docs
          </Link>
        </div>
      </nav>

      <div className="relative z-10 max-w-7xl mx-auto p-6">
        {/* Header with video input */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Video Intelligence Dashboard</h1>
          <p className="text-white/60 mb-6">Process, analyze, and extract insights from any video</p>

          <form onSubmit={(e) => { e.preventDefault(); handleAddVideo(); }} className="flex gap-3 max-w-2xl">
            <div className="flex-1 flex gap-3 p-2 rounded-xl bg-white/5 border border-white/10">
              <input
                type="text"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="Paste YouTube URL, Google Drive link, or upload..."
                className="flex-1 px-4 py-2 bg-transparent text-white placeholder:text-white/40 focus:outline-none"
              />
              <button
                type="submit"
                className="px-6 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 font-medium hover:opacity-90 transition"
              >
                Analyze
              </button>
            </div>
          </form>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <MetricCard
            value={metrics?.metrics.activeWorkflows ?? 0}
            label="Active Workflows"
            icon="⚡"
            trend="+12%"
          />
          <MetricCard
            value={metrics?.metrics.totalProcessed ?? 0}
            label="Videos Processed"
            icon="🎬"
            trend="+28%"
          />
          <MetricCard
            value="2.3s"
            label="Avg Processing Time"
            icon="⏱️"
            trend="-15%"
          />
          <MetricCard
            value={`${metrics?.metrics.errorRate ?? 0}%`}
            label="Error Rate"
            icon="✓"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Library */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Video Library</h2>
              <div className="flex gap-2">
                <button className="px-3 py-1.5 rounded-lg bg-violet-500/20 text-violet-400 text-sm">All</button>
                <button className="px-3 py-1.5 rounded-lg bg-white/5 text-white/60 text-sm hover:bg-white/10 transition">Processing</button>
                <button className="px-3 py-1.5 rounded-lg bg-white/5 text-white/60 text-sm hover:bg-white/10 transition">Complete</button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {videos.map(video => (
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
            {/* Activity Feed */}
            <ActivityFeed activities={activities} />

            {/* Quick Actions */}
            <div className="bg-slate-900/50 backdrop-blur-xl rounded-xl border border-white/10 p-6">
              <h3 className="font-medium text-white mb-4">Quick Actions</h3>
              <div className="space-y-3">
                <button className="w-full px-4 py-3 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-400 text-sm font-medium hover:bg-violet-500/20 transition text-left">
                  📊 Generate Weekly Report
                </button>
                <button className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white/80 text-sm font-medium hover:bg-white/10 transition text-left">
                  🔗 Connect Integration
                </button>
                <button className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white/80 text-sm font-medium hover:bg-white/10 transition text-left">
                  📤 Export All Insights
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Video Detail Modal */}
      {selectedVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" onClick={() => setSelectedVideo(null)}>
          <div className="bg-slate-900 rounded-2xl border border-white/10 max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-white/10">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">{selectedVideo.title}</h2>
                  <p className="text-white/40 text-sm mt-1">{selectedVideo.url}</p>
                </div>
                <button onClick={() => setSelectedVideo(null)} className="text-white/40 hover:text-white">✕</button>
              </div>
            </div>

            {selectedVideo.insights && (
              <div className="p-6 space-y-6">
                {/* Summary */}
                <div>
                  <h3 className="text-sm font-medium text-white/60 mb-2">Summary</h3>
                  <p className="text-white/80">{selectedVideo.insights.summary}</p>
                </div>

                {/* Action Items */}
                <div>
                  <h3 className="text-sm font-medium text-white/60 mb-2">Action Items</h3>
                  <ul className="space-y-2">
                    {selectedVideo.insights.actions.map((action, i) => (
                      <li key={i} className="flex items-start gap-3 p-3 rounded-lg bg-white/5">
                        <input type="checkbox" className="mt-1" />
                        <span className="text-white/80">{action}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Topics */}
                <div>
                  <h3 className="text-sm font-medium text-white/60 mb-2">Topics</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedVideo.insights.topics.map(topic => (
                      <span key={topic} className="px-3 py-1 rounded-full bg-violet-500/20 text-violet-400 text-sm">
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-4 border-t border-white/10">
                  <button className="flex-1 px-4 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 font-medium">
                    Deploy as App
                  </button>
                  <button className="px-4 py-2 rounded-lg bg-white/5 border border-white/10">
                    Export
                  </button>
                  <button className="px-4 py-2 rounded-lg bg-white/5 border border-white/10">
                    Share
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Loading fallback for Suspense
function DashboardLoading() {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 rounded-full border-4 border-violet-500 border-t-transparent animate-spin mx-auto mb-4" />
        <p className="text-white/60">Loading dashboard...</p>
      </div>
    </div>
  );
}

// Export with Suspense boundary (required for useSearchParams in Next.js 14+)
export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardLoading />}>
      <DashboardContent />
    </Suspense>
  );
}
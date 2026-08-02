'use client';

import { Suspense, useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import Image from 'next/image';
import { useSearchParams } from 'next/navigation';
import { clsx } from 'clsx';
import Nav from '@/components/Nav';
import PreferencesPanel from '@/components/PreferencesPanel';
import BillingStatusBanner from '@/components/billing/BillingStatusBanner';
import { useDashboardStore } from '@/store/dashboard-store';
import type { Video } from '@/store/dashboard-types';

const DashboardSplitView = dynamic(
  () => import('@/components/dashboard/DashboardSplitView'),
  {
    loading: () => (
      <div className="flex flex-1 items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    ),
  },
);

// ============================================
// Video Card Component (Library View)
// ============================================
function VideoCard({
  video,
  priority = false,
  onClick
}: {
  video: Video;
  priority?: boolean;
  onClick: () => void;
}) {
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
          <Image
            src={video.thumbnail}
            alt={video.title}
            fill
            priority={priority}
            className="object-cover transition-transform duration-500 group-hover:scale-105"
            sizes="(max-width: 768px) 100vw, 33vw"
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
    useDashboardStore.persist.rehydrate();
  }, []);

  useEffect(() => {
    const video = searchParams.get('video');
    if (video) {
      setVideoUrl(video);
      const existingVideo = videos.find((v) => v.url === video);
      if (existingVideo) {
        if (selectedVideoId !== existingVideo.id) {
          selectVideo(existingVideo.id);
        }
      } else {
        let cancelled = false;
        processVideo(video).then((id) => {
          if (!cancelled) {
            selectVideo(id);
          }
        });
        return () => {
          cancelled = true;
        };
      }
    }
  }, [searchParams, processVideo, selectVideo, videos, selectedVideoId]);

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
      <p id="billing-dashboard-markers" className="sr-only" aria-hidden>
        billing:BillingStatusBanner
      </p>
      <Nav
        subtitle="Dashboard"
        rightSlot={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Link
              href="/dashboard/agents"
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-400 font-bold uppercase tracking-wider hover:bg-indigo-500/20 transition-all"
            >
              ⚡ <span className="hidden sm:inline">Agent Pipeline</span><span className="sm:hidden">Agents</span>
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

      {selectedVideo ? (
        <DashboardSplitView
          video={selectedVideo}
          onClose={() => selectVideo(null)}
          onExtractEvents={extractEvents}
        />
      ) : (
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-10">
          <div className="max-w-6xl mx-auto space-y-10">
            <BillingStatusBanner />
            <div className="p-6 sm:p-10 flex flex-col items-center justify-center text-center" style={{ background: 'rgba(25, 25, 31, 0.8)', border: '1px solid rgba(106, 242, 222, 0.08)' }}>
              <span className="text-[10px] tracking-[0.3em] uppercase mb-4 block" style={{ color: '#6af2de', fontFamily: 'var(--font-heading)' }}>Video Intelligence Engine</span>
              <h1 className="font-heading text-4xl font-bold tracking-tighter mb-3" style={{ color: '#f8f5fd' }}>Analyze New Video</h1>
              <p className="mb-6 max-w-lg" style={{ color: 'rgba(248,245,253,0.4)' }}>
                Paste a YouTube URL — like adding a video to your library. We transcribe it, extract events, and dispatch agents to act on what matters.
              </p>
              <ol className="mb-8 flex flex-wrap items-center justify-center gap-2 text-[10px] font-heading font-bold uppercase tracking-widest" aria-label="Workflow steps">
                {[
                  { n: 1, label: 'Paste URL' },
                  { n: 2, label: 'Analyze' },
                  { n: 3, label: 'Review insights' },
                  { n: 4, label: 'Dispatch agents' },
                ].map((step, i) => (
                  <li key={step.n} className="flex items-center gap-2">
                    <span
                      className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[10px]"
                      style={{ background: 'rgba(106,242,222,0.12)', color: '#6af2de', border: '1px solid rgba(106,242,222,0.25)' }}
                    >
                      {step.n}
                    </span>
                    <span style={{ color: 'rgba(248,245,253,0.55)' }}>{step.label}</span>
                    {i < 3 && <span style={{ color: 'rgba(248,245,253,0.2)' }}>→</span>}
                  </li>
                ))}
              </ol>
              <div className="w-full max-w-2xl mb-4">
                <PreferencesPanel />
              </div>
              <form onSubmit={(e) => { e.preventDefault(); handleAddVideo(); }} className="w-full max-w-2xl">
                <div className="flex flex-col gap-2 p-2 rounded-xl transition-all sm:flex-row" style={{ background: 'rgba(25, 25, 31, 0.8)', border: '1px solid rgba(106, 242, 222, 0.15)' }}>
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
                    className="px-6 py-3 font-bold text-sm transition-all active:scale-95 disabled:opacity-30 sm:px-8"
                    style={{ background: 'linear-gradient(135deg, #6af2de, #10b7a5)', color: '#002b26' }}
                  >
                    Analyze Footage
                  </button>
                </div>
              </form>
            </div>

            <div>
              <div className="flex flex-col gap-4 mb-6 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-1 h-6" style={{ background: '#6af2de' }} />
                  <h2 className="font-heading text-xl font-bold tracking-tight" style={{ color: '#f8f5fd' }}>Your Library</h2>
                </div>
                <div className="flex flex-wrap gap-1 p-1 rounded-xl" style={{ background: 'rgba(25, 25, 31, 0.8)', border: '1px solid rgba(72, 71, 77, 0.15)' }}>
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
                  {filteredVideos.map((video, index) => (
                    <VideoCard key={video.id} video={video} priority={index === 0} onClick={() => selectVideo(video.id)} />
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
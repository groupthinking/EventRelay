'use client';

import { Suspense, useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import { useSearchParams } from 'next/navigation';
import { clsx } from 'clsx';
import { AlertCircle, LoaderCircle, RotateCcw, Video as VideoIcon } from 'lucide-react';
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

const EXAMPLE_VIDEO_URL = 'https://www.youtube.com/watch?v=auJzb1D-fag';

function processingStage(progress: number): string {
  if (progress < 20) return 'Checking video';
  if (progress < 50) return 'Fetching captions';
  if (progress < 70) return 'Verifying timestamps';
  if (progress < 92) return 'Creating findings';
  return 'Preparing actions';
}

// ============================================
// Video Card Component (Library View)
// ============================================
function VideoCard({
  video,
  priority = false,
  onClick,
  onRetry,
}: {
  video: Video;
  priority?: boolean;
  onClick: () => void;
  onRetry: () => void;
}) {
  const displayTitle = video.status === 'failed' ? "Couldn't analyze this video" : video.title;
  const failureSummary = video.failure?.stage === 'start'
    ? 'Use a valid YouTube watch, share, embed, Shorts, or live URL.'
    : video.failure?.stage === 'acquisition'
      ? 'Captions could not be acquired from this source.'
      : 'Analysis stopped before a verified result was saved.';

  return (
    <article
      className={clsx(
        'relative flex w-full flex-col overflow-hidden rounded-2xl text-left',
        'bg-[#10151a] border border-white/[0.08] hover:border-[#6de1c6]/35',
        'transition-[border-color,background-color] duration-200 hover:bg-[#131a20]',
      )}
    >
      <button
        type="button"
        onClick={onClick}
        aria-label={`Open ${video.title}`}
        className={clsx(
          'group relative flex-none overflow-hidden bg-surface-800 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-400/70',
          video.status === 'failed' ? 'aspect-[16/6]' : 'aspect-video',
        )}
      >
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
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-surface-800 to-surface-900">
            <VideoIcon className="h-12 w-12 text-white/20" aria-hidden="true" />
          </div>
        )}

        {video.status === 'processing' && (
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center">
            <div className="text-center">
              <div className="mb-2 flex items-center justify-center gap-2 text-[#6de1c6]">
                <LoaderCircle className="h-6 w-6 animate-spin" aria-hidden="true" />
                <span className="text-sm font-bold">{video.progress}%</span>
              </div>
              <p className="text-xs text-white/65">{processingStage(video.progress)}</p>
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
      </button>

      <div className="p-5 flex flex-col flex-1">
        <button type="button" onClick={onClick} aria-label={`Open ${displayTitle}`} className="rounded text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400/70">
          <h3 className="mb-1.5 truncate font-heading font-semibold text-white transition-colors hover:text-[#8aead4]">
            {displayTitle}
          </h3>
        </button>
        <p className="text-xs text-white/40 truncate mb-4">{video.url}</p>

        {video.status === 'complete' && video.insights && (
          <div className="mt-auto flex flex-wrap gap-2 pt-4 border-t border-white/[0.05]">
            {video.insights.topics.slice(0, 2).map((topic) => (
              <span key={topic} className="px-2 py-1 bg-white/[0.05] text-white/70 rounded border border-white/[0.05] text-[10px] font-medium truncate max-w-[100px]">
                {topic}
              </span>
            ))}
            {video.events && video.events.length > 0 && (
              <span className="rounded border border-[#6de1c6]/20 bg-[#6de1c6]/10 px-2 py-1 text-xs font-medium text-[#8aead4]">
                {video.events.length} actions
              </span>
            )}
          </div>
        )}

        {video.status === 'failed' && video.failure && (
          <div className="mt-auto border-t border-white/[0.07] pt-4">
            <div className="mb-3 flex items-start gap-2 text-xs leading-5 text-red-200/80">
              <AlertCircle className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
              <p>{failureSummary}</p>
            </div>
            {video.failure.retryable && (
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-[#6de1c6]/25 bg-[#6de1c6]/10 px-4 text-sm font-semibold text-[#8aead4] transition-colors hover:bg-[#6de1c6]/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400/70"
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Retry analysis
              </button>
            )}
            <details className="mt-2 text-xs text-white/45">
              <summary className="min-h-11 cursor-pointer py-3">Technical details</summary>
              <p className="break-words pb-1 leading-5">{video.failure.message}</p>
            </details>
          </div>
        )}
      </div>
    </article>
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
  const resumeProcessingRuns = useDashboardStore((s) => s.resumeProcessingRuns);
  const extractEvents = useDashboardStore((s) => s.extractEvents);

  const selectedVideo = videos.find((v) => v.id === selectedVideoId) || null;

  useEffect(() => {
    void Promise.resolve(useDashboardStore.persist.rehydrate()).then(() => resumeProcessingRuns());
  }, [resumeProcessingRuns]);

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
        rightSlot={
          <div className="flex flex-wrap items-center justify-end gap-2">
            {processingCount > 0 ? (
              <div className="flex items-center gap-2 rounded-full border border-[#6de1c6]/20 bg-[#6de1c6]/10 px-3 py-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-400" />
                </span>
                <span className="text-xs font-medium text-[#8aead4]">{processingCount} processing</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 rounded-full border border-emerald-400/15 bg-emerald-400/[0.07] px-3 py-1.5">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
                <span className="text-xs font-medium text-emerald-300">Ready</span>
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
        <div className="flex-1 overflow-y-auto bg-[#090c10] p-4 sm:p-6 lg:p-10">
          <div className="mx-auto max-w-6xl space-y-8">
            <section className="overflow-hidden rounded-3xl border border-white/[0.08] bg-[#0f1419] px-5 py-8 sm:px-8 sm:py-10 lg:px-12">
              <div className="max-w-3xl">
                <span className="mb-4 block text-xs font-semibold text-[#6de1c6]">Start with a source</span>
                <h1 className="mb-4 max-w-2xl font-heading text-3xl font-bold tracking-tight text-[#f2f5f2] sm:text-4xl lg:text-5xl">
                  Turn a YouTube video into evidence you can use.
                </h1>
                <p className="mb-7 max-w-2xl text-base leading-7 text-[#97a19d]">
                  UVAI checks the caption source, creates concise findings, and prepares actions for review. Generated conclusions remain separate from verified captions.
                </p>
              </div>
              <form onSubmit={(e) => { e.preventDefault(); handleAddVideo(); }} className="max-w-4xl">
                <label htmlFor="video-url" className="mb-2 block text-sm font-medium text-white/80">
                  YouTube URL
                </label>
                <div className="flex flex-col gap-2 rounded-2xl border border-white/[0.1] bg-[#090c10] p-2 transition-colors focus-within:border-[#6de1c6]/55 sm:flex-row">
                  <input
                    id="video-url"
                    type="text"
                    value={videoUrl}
                    onInput={(e) => setVideoUrl(e.currentTarget.value)}
                    placeholder="https://youtube.com/watch?v=..."
                    className="min-h-12 flex-1 bg-transparent px-4 py-3 text-base text-white outline-none placeholder:text-white/30"
                  />
                  <button
                    type="submit"
                    disabled={!videoUrl.trim()}
                    className="evidence-primary-button min-h-12 rounded-xl px-6 py-3 text-sm font-semibold disabled:opacity-30 sm:px-8"
                  >
                    Analyze video
                  </button>
                </div>
              </form>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <button
                  type="button"
                  onClick={() => setVideoUrl(EXAMPLE_VIDEO_URL)}
                  className="min-h-11 self-start rounded-lg px-3 text-sm font-medium text-[#8aead4] transition-colors hover:bg-white/[0.05]"
                >
                  Try a real example
                </button>
                <details className="w-full max-w-xl rounded-xl border border-white/[0.07] bg-white/[0.02] px-4">
                  <summary className="min-h-11 cursor-pointer py-3 text-sm font-medium text-white/65">
                    Analysis preferences
                  </summary>
                  <div className="pb-4">
                    <PreferencesPanel />
                  </div>
                </details>
              </div>
            </section>

            <BillingStatusBanner />

            <section>
              <div className="flex flex-col gap-4 mb-6 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <h2 className="font-heading text-2xl font-semibold tracking-tight text-[#f2f5f2]">Recent analyses</h2>
                </div>
                <div className="flex flex-wrap gap-1 rounded-xl border border-white/[0.07] bg-[#0f1419] p-1">
                  {(['all', 'processing', 'complete', 'failed'] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className="px-4 py-1.5 text-xs font-heading font-bold uppercase tracking-widest transition-all"
                      style={{
                        color: filter === f ? '#8aead4' : 'rgba(242,245,242,0.5)',
                        background: filter === f ? 'rgba(109, 225, 198, 0.1)' : 'transparent',
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
                    <VideoCard
                      key={video.id}
                      video={video}
                      priority={index === 0}
                      onClick={() => selectVideo(video.id)}
                      onRetry={() => {
                        void processVideo(video.url).then((id) => selectVideo(id));
                      }}
                    />
                  ))}
                </div>
              )}
            </section>
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

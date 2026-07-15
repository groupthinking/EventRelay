'use client';

import { useMemo, useRef, type KeyboardEvent } from 'react';
import { buildEmbedUrl, formatSeconds } from '@/lib/timestamp';

/** A point-in-time marker rendered on the scrubber. */
export interface TimelineMarker {
  id: string;
  seconds: number;
  label: string;
  type: 'action' | 'topic' | 'code' | 'alert' | 'mention' | 'insight';
}

const MARKER_COLORS: Record<TimelineMarker['type'], string> = {
  action: '#69ccff',
  topic: '#a78bfa',
  code: '#22c55e',
  alert: '#ff716c',
  mention: '#a78bfa',
  insight: '#ff716c',
};

interface VideoCanvasStageProps {
  /** Callback ref attached to the element the IFrame API replaces with the player. */
  containerRef: (node: HTMLDivElement | null) => void;
  videoId: string | null;
  title: string;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  ready: boolean;
  /** When true, the IFrame API failed to load — render a plain embed instead. */
  failed: boolean;
  markers: TimelineMarker[];
  onSeek: (seconds: number) => void;
}

/**
 * The visual center of the workspace: a large video player with a scrubbable
 * timeline underneath. The timeline shows progress and clickable event markers
 * that seek the player to that moment.
 */
export default function VideoCanvasStage({
  containerRef,
  videoId,
  title,
  currentTime,
  duration,
  isPlaying,
  ready,
  failed,
  markers,
  onSeek,
}: VideoCanvasStageProps) {
  const hasVideoId = !!videoId;
  const trackRef = useRef<HTMLDivElement>(null);
  const progress = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;
  // Seeking only works once the IFrame API is ready and a duration is known.
  // Until then the slider is a non-functional control, so keep it out of the
  // tab order and mark it disabled for assistive tech.
  const seekable = duration > 0;

  const positionedMarkers = useMemo(() => {
    if (duration <= 0) return [];
    return markers
      .filter((m) => m.seconds >= 0 && m.seconds <= duration)
      .map((m) => ({ ...m, left: (m.seconds / duration) * 100 }));
  }, [markers, duration]);

  const seekFromClientX = (clientX: number) => {
    const el = trackRef.current;
    if (!el || duration <= 0) return;
    const rect = el.getBoundingClientRect();
    const fraction = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    onSeek(fraction * duration);
  };

  const onTrackKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (duration <= 0) return;
    const step = Math.max(5, duration * 0.05);
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      onSeek(Math.min(duration, currentTime + step));
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      onSeek(Math.max(0, currentTime - step));
    } else if (e.key === 'Home') {
      e.preventDefault();
      onSeek(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      onSeek(duration);
    }
  };

  return (
    <section
      className="flex flex-col gap-4"
      aria-label="Video player and timeline"
    >
      {/* Player stage */}
      <div
        className="relative w-full aspect-video overflow-hidden rounded-2xl"
        style={{
          background: '#000',
          border: '1px solid rgba(106, 242, 222, 0.12)',
          boxShadow: '0 24px 60px -24px rgba(0,0,0,0.8), 0 0 0 1px rgba(106,242,222,0.04)',
        }}
      >
        {hasVideoId && failed ? (
          // Fallback: IFrame API unavailable — plain embed keeps the video watchable
          // (time-sync features degrade gracefully).
          <iframe
            src={buildEmbedUrl(videoId!)}
            title={title}
            className="absolute inset-0 h-full w-full border-0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : hasVideoId ? (
          <>
            {/* The IFrame API replaces this element with the player. */}
            <div ref={containerRef} className="absolute inset-0 h-full w-full" />
            {!ready && (
              <div className="absolute inset-0 flex items-center justify-center" style={{ background: '#000' }}>
                <div className="flex flex-col items-center gap-3">
                  <div
                    className="h-8 w-8 rounded-full border-2 border-t-transparent animate-spin motion-reduce:animate-none"
                    style={{ borderColor: '#6af2de', borderTopColor: 'transparent' }}
                    aria-hidden="true"
                  />
                  <span className="text-xs uppercase tracking-[0.2em]" style={{ color: 'rgba(248,245,253,0.4)' }}>
                    Loading player
                  </span>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3" style={{ color: 'rgba(248,245,253,0.3)' }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="m10 9 5 3-5 3z" />
            </svg>
            <span className="text-sm">Video player not available</span>
          </div>
        )}
      </div>

      {/* Timeline scrubber */}
      <div className="flex items-center gap-3 px-1">
        <span className="text-[11px] font-mono tabular-nums w-12 text-right" style={{ color: isPlaying ? '#6af2de' : 'rgba(248,245,253,0.45)' }}>
          {formatSeconds(currentTime)}
        </span>

        <div
          ref={trackRef}
          role="slider"
          tabIndex={seekable ? 0 : -1}
          aria-label="Seek video"
          aria-disabled={!seekable}
          aria-valuemin={0}
          aria-valuemax={Math.floor(duration) || 0}
          aria-valuenow={Math.floor(currentTime) || 0}
          aria-valuetext={`${formatSeconds(currentTime)} of ${formatSeconds(duration)}`}
          aria-keyshortcuts="ArrowLeft ArrowRight Home End"
          onClick={(e) => seekFromClientX(e.clientX)}
          onKeyDown={onTrackKeyDown}
          className={`group relative flex-1 h-9 flex items-center rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0e0e13] ${seekable ? 'cursor-pointer' : 'cursor-default'}`}
        >
          {/* Track */}
          <div
            className="relative w-full h-1.5 rounded-full overflow-visible transition-[height] group-hover:h-2"
            style={{ background: 'rgba(255,255,255,0.08)' }}
          >
            {/* Progress fill */}
            <div
              className="absolute inset-y-0 left-0 rounded-full"
              style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #10b7a5, #6af2de)' }}
            />
            {/* Playhead */}
            <div
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-3 w-3 rounded-full transition-transform group-hover:scale-125"
              style={{ left: `${progress}%`, background: '#6af2de', boxShadow: '0 0 8px rgba(106,242,222,0.6)' }}
              aria-hidden="true"
            />
            {/* Event markers */}
            {positionedMarkers.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSeek(m.seconds);
                }}
                title={`${formatSeconds(m.seconds)} · ${m.label}`}
                aria-label={`Jump to ${formatSeconds(m.seconds)}: ${m.label}`}
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-3 w-3 rounded-full transition-transform hover:scale-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
                style={{
                  left: `${m.left}%`,
                  background: MARKER_COLORS[m.type],
                  border: '2px solid rgba(14,14,19,0.9)',
                }}
              />
            ))}
          </div>
        </div>

        <span className="text-[11px] font-mono tabular-nums w-12" style={{ color: 'rgba(248,245,253,0.35)' }}>
          {formatSeconds(duration)}
        </span>
      </div>

      {/* Title + marker legend */}
      <div className="flex items-start justify-between gap-4 px-1">
        <h2 className="font-heading text-lg font-bold tracking-tight text-balance" style={{ color: '#f8f5fd' }}>
          {title}
        </h2>
        {positionedMarkers.length > 0 && (
          <span className="flex-none text-[10px] uppercase tracking-[0.15em]" style={{ color: 'rgba(248,245,253,0.35)' }}>
            {positionedMarkers.length} markers
          </span>
        )}
      </div>
    </section>
  );
}

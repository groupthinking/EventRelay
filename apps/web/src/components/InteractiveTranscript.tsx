'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { clsx } from 'clsx';

/* ═══════════════════════════════════════════
   Interactive Transcript Player
   VibeVoice-style synchronized playback with
   speaker labels, clickable timestamps, and
   highlight-as-you-play
   ═══════════════════════════════════════════ */

export interface TranscriptSegment {
  id: string;
  speaker: string;
  speakerColor: string;
  startTime: number; // seconds
  endTime: number;
  text: string;
}

interface InteractiveTranscriptProps {
  segments: TranscriptSegment[];
  currentTime: number; // seconds from video player
  onSeek: (time: number) => void;
  isPlaying: boolean;
  className?: string;
}

const SPEAKER_COLORS: Record<string, string> = {
  'Speaker 1': '#6af2de',
  'Speaker 2': '#a78bfa',
  'Speaker 3': '#f59e0b',
  'Speaker 4': '#f472b6',
  'Speaker 5': '#60a5fa',
};

function getSpeakerColor(speaker: string): string {
  return SPEAKER_COLORS[speaker] || '#6af2de';
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * Renders a transcript segment row that can be focused and used to jump to its start time.
 *
 * @param segment - The transcript segment to display.
 * @param isActive - Whether this segment matches the current playback position.
 * @param isPast - Whether this segment ends before the current playback position.
 * @param onSeek - Called with the segment start time when the row is activated.
 */
function SegmentRow({
  segment,
  isActive,
  isPast,
  onSeek,
}: {
  segment: TranscriptSegment;
  isActive: boolean;
  isPast: boolean;
  onSeek: (time: number) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const color = segment.speakerColor || getSpeakerColor(segment.speaker);

  useEffect(() => {
    if (isActive && ref.current) {
      ref.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [isActive]);

  return (
    <div
      ref={ref}
      role="button"
      tabIndex={0}
      aria-label={`Jump to ${formatTimestamp(segment.startTime)}, ${segment.speaker}`}
      aria-current={isActive || undefined}
      className={clsx(
        'group flex gap-3 py-3 px-4 rounded-lg cursor-pointer transition-[transform,background-color,border-color,opacity] duration-300 motion-reduce:transition-none',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40',
        isActive && 'scale-[1.01] motion-reduce:scale-100',
      )}
      style={{
        background: isActive
          ? `rgba(${color === '#6af2de' ? '106, 242, 222' : color === '#a78bfa' ? '167, 139, 250' : '245, 158, 11'}, 0.06)`
          : 'transparent',
        borderLeft: isActive ? `2px solid ${color}` : '2px solid transparent',
        opacity: isPast && !isActive ? 0.5 : 1,
      }}
      onClick={() => onSeek(segment.startTime)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSeek(segment.startTime);
        }
      }}
    >
      {/* Timestamp */}
      <span
        className="flex-shrink-0 text-[10px] font-mono tabular-nums pt-0.5 transition-colors"
        style={{
          color: isActive ? color : 'rgba(248, 245, 253, 0.25)',
        }}
      >
        {formatTimestamp(segment.startTime)}
      </span>

      {/* Speaker label */}
      <div className="flex-shrink-0 pt-0.5">
        <span
          className="text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider"
          style={{
            background: `${color}15`,
            color: color,
            border: `1px solid ${color}30`,
          }}
        >
          {segment.speaker}
        </span>
      </div>

      {/* Text */}
      <p
        className="flex-1 text-sm leading-relaxed transition-colors duration-300"
        style={{
          color: isActive ? '#f8f5fd' : 'rgba(248, 245, 253, 0.6)',
        }}
      >
        {segment.text}
      </p>
    </div>
  );
}

/**
 * Renders an interactive transcript with speaker filtering, search, and playback progress.
 *
 * @param segments - Transcript segments to display
 * @param currentTime - Current playback time in seconds
 * @param onSeek - Called with the start time of a segment when a row is activated
 * @param isPlaying - Controls the playing-state indicator in the header
 * @param className - Additional classes applied to the outer container
 */
export default function InteractiveTranscript({
  segments,
  currentTime,
  onSeek,
  isPlaying,
  className = '',
}: InteractiveTranscriptProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterSpeaker, setFilterSpeaker] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const speakers = useMemo(
    () => [...new Set(segments.map((s) => s.speaker))],
    [segments],
  );

  const filteredSegments = useMemo(() => {
    return segments.filter((seg) => {
      const matchesSpeaker = !filterSpeaker || seg.speaker === filterSpeaker;
      const matchesSearch =
        !searchQuery ||
        seg.text.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSpeaker && matchesSearch;
    });
  }, [segments, filterSpeaker, searchQuery]);

  const activeSegmentId = useMemo(() => {
    const active = segments.find(
      (s) => currentTime >= s.startTime && currentTime < s.endTime,
    );
    return active?.id || null;
  }, [segments, currentTime]);

  return (
    <div
      className={`flex flex-col rounded-2xl overflow-hidden ${className}`}
      style={{
        background: 'rgba(19, 19, 24, 0.7)',
        border: '1px solid rgba(106, 242, 222, 0.08)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-3"
        style={{
          background: 'rgba(25, 25, 31, 0.9)',
          borderBottom: '1px solid rgba(72, 71, 77, 0.1)',
        }}
      >
        <div className="flex items-center gap-3">
          {isPlaying && (
            <div className="flex gap-0.5 items-end h-3" aria-hidden="true">
              {[0.6, 1, 0.4, 0.8, 0.5].map((h, i) => (
                <div
                  key={i}
                  className="w-0.5 rounded-full animate-pulse motion-reduce:animate-none"
                  style={{
                    height: `${h * 12}px`,
                    background: '#6af2de',
                    animationDelay: `${i * 100}ms`,
                  }}
                />
              ))}
            </div>
          )}
          <span
            className="font-heading text-xs tracking-widest uppercase font-bold"
            style={{ color: '#f8f5fd' }}
          >
            Transcript
          </span>
          <span
            className="text-[10px]"
            style={{ color: 'rgba(248, 245, 253, 0.3)' }}
          >
            {segments.length} segments
          </span>
        </div>

        {/* Speaker filter pills */}
        <div className="flex gap-1.5">
          <button
            type="button"
            onClick={() => setFilterSpeaker(null)}
            aria-pressed={!filterSpeaker}
            className="text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40"
            style={{
              background: !filterSpeaker
                ? 'rgba(106, 242, 222, 0.12)'
                : 'rgba(25, 25, 31, 0.6)',
              color: !filterSpeaker ? '#6af2de' : 'rgba(248, 245, 253, 0.3)',
              border: !filterSpeaker
                ? '1px solid rgba(106, 242, 222, 0.2)'
                : '1px solid rgba(72, 71, 77, 0.15)',
            }}
          >
            All
          </button>
          {speakers.map((speaker) => {
            const color = getSpeakerColor(speaker);
            const isActive = filterSpeaker === speaker;
            return (
              <button
                key={speaker}
                type="button"
                onClick={() =>
                  setFilterSpeaker(isActive ? null : speaker)
                }
                aria-pressed={isActive}
                className="text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40"
                style={{
                  background: isActive ? `${color}18` : 'rgba(25, 25, 31, 0.6)',
                  color: isActive ? color : 'rgba(248, 245, 253, 0.3)',
                  border: isActive
                    ? `1px solid ${color}40`
                    : '1px solid rgba(72, 71, 77, 0.15)',
                }}
              >
                {speaker}
              </button>
            );
          })}
        </div>
      </div>

      {/* Search bar */}
      <div
        className="px-4 py-2"
        style={{ borderBottom: '1px solid rgba(72, 71, 77, 0.08)' }}
      >
        <div className="flex items-center gap-2">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="rgba(248,245,253,0.25)"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search transcript…"
            aria-label="Search transcript"
            className="flex-1 bg-transparent text-xs text-white placeholder:text-white/20 focus:outline-none"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="text-[10px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40 rounded"
              style={{ color: 'rgba(248, 245, 253, 0.3)' }}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Transcript body */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-2 space-y-0.5"
        style={{ maxHeight: '500px' }}
      >
        {filteredSegments.map((segment) => (
          <SegmentRow
            key={segment.id}
            segment={segment}
            isActive={segment.id === activeSegmentId}
            isPast={segment.endTime < currentTime}
            onSeek={onSeek}
          />
        ))}
        {filteredSegments.length === 0 && (
          <div className="py-12 text-center">
            <p style={{ color: 'rgba(248, 245, 253, 0.3)' }}>
              No segments match your filter.
            </p>
          </div>
        )}
      </div>

      {/* Waveform-style progress at bottom */}
      {segments.length > 0 && (
        <div
          className="px-4 py-3 flex items-center gap-3"
          style={{
            background: 'rgba(25, 25, 31, 0.9)',
            borderTop: '1px solid rgba(72, 71, 77, 0.1)',
          }}
        >
          <span
            className="text-[10px] font-mono tabular-nums"
            style={{ color: 'rgba(248, 245, 253, 0.3)' }}
          >
            {formatTimestamp(currentTime)}
          </span>
          <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(25, 25, 31, 0.8)' }}>
            <div
              className="h-full rounded-full transition-[width] duration-300 motion-reduce:transition-none"
              style={{
                width: `${
                  segments.length > 0
                    ? (currentTime / segments[segments.length - 1].endTime) * 100
                    : 0
                }%`,
                background: 'linear-gradient(90deg, #6af2de, #38fbf7)',
              }}
            />
          </div>
          <span
            className="text-[10px] font-mono tabular-nums"
            style={{ color: 'rgba(248, 245, 253, 0.3)' }}
          >
            {segments.length > 0
              ? formatTimestamp(segments[segments.length - 1].endTime)
              : '0:00'}
          </span>
        </div>
      )}
    </div>
  );
}

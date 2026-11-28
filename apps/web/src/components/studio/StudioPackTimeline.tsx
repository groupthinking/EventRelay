'use client';

import { useEffect, useState } from 'react';
import type { EmittedVideoPack } from '@/lib/emit-video-pack';
import {
  studioPackTimelineDuration,
  studioPackTimelineMarkers,
  type StudioTimelineMarker,
} from '@/lib/studio-pack-timeline';
import { formatSeconds } from '@/lib/timestamp';

export type StudioPackTimelineProps = {
  pack: EmittedVideoPack;
  canSeek: boolean;
  onSeek?: (seconds: number) => void;
  currentTime?: number;
  playerDuration?: number | null;
};

/**
 * Cut 2 — horizontal pack time surface under the stage player.
 * Chapters are range segments; keyframes / visual moments / events are ticks.
 * Selection seeks the player when canSeek; otherwise markers stay visible but inert.
 */
export default function StudioPackTimeline({
  pack,
  canSeek,
  onSeek,
  currentTime = 0,
  playerDuration = null,
}: StudioPackTimelineProps) {
  const markers = studioPackTimelineMarkers(pack);
  const duration = studioPackTimelineDuration(markers, playerDuration);
  const chapters = markers.filter((m) => m.kind === 'chapter');
  const ticks = markers.filter((m) => m.kind !== 'chapter');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedId(null);
  }, [pack.id, pack.video_id]);

  useEffect(() => {
    if (!selectedId) return;
    const timer = window.setTimeout(() => setSelectedId(null), 1200);
    return () => window.clearTimeout(timer);
  }, [selectedId]);

  if (markers.length === 0) return null;

  const seekMarker = (marker: StudioTimelineMarker) => {
    setSelectedId(marker.id);
    onSeek?.(marker.start);
  };

  const playheadPct =
    duration > 0 && Number.isFinite(currentTime)
      ? Math.min(100, Math.max(0, (currentTime / duration) * 100))
      : 0;

  return (
    <section
      className="studio-pack-timeline"
      data-testid="studio-pack-timeline"
      data-can-seek={canSeek ? 'true' : 'false'}
      aria-label="Pack timeline"
    >
      <div className="studio-pack-timeline__head">
        <p className="uvai-section-label">Timeline</p>
        <span className="studio-pack-timeline__span font-mono" data-testid="studio-pack-timeline-span">
          {formatSeconds(duration)}
        </span>
      </div>

      <div className="studio-pack-timeline__track" data-testid="studio-pack-timeline-track">
        <div className="studio-pack-timeline__rail" aria-hidden />
        {chapters.map((chapter, index) => {
          const end = chapter.end ?? chapter.start;
          const left = (chapter.start / duration) * 100;
          const width = Math.max(((end - chapter.start) / duration) * 100, 0.8);
          const selected = selectedId === chapter.id;
          return (
            <button
              key={chapter.id}
              type="button"
              data-testid={`studio-timeline-chapter-${index}`}
              data-selected={selected ? 'true' : 'false'}
              disabled={!canSeek}
              title={
                canSeek
                  ? `Seek to ${formatSeconds(chapter.start)} — ${chapter.label}`
                  : 'Switch URL back to this pack to seek.'
              }
              aria-label={`Chapter ${index + 1}: ${chapter.label}`}
              onClick={() => seekMarker(chapter)}
              className="studio-pack-timeline__chapter"
              style={{ left: `${left}%`, width: `${width}%` }}
            >
              <span className="studio-pack-timeline__chapter-label">{chapter.label}</span>
            </button>
          );
        })}

        {ticks.map((tick, index) => {
          const left = (tick.start / duration) * 100;
          const selected = selectedId === tick.id;
          return (
            <button
              key={tick.id}
              type="button"
              data-testid={`studio-timeline-${tick.kind}-${index}`}
              data-kind={tick.kind}
              data-selected={selected ? 'true' : 'false'}
              disabled={!canSeek}
              title={
                canSeek
                  ? `Seek to ${formatSeconds(tick.start)} — ${tick.label}`
                  : 'Switch URL back to this pack to seek.'
              }
              aria-label={`${tick.kind} at ${formatSeconds(tick.start)}: ${tick.label}`}
              onClick={() => seekMarker(tick)}
              className="studio-pack-timeline__tick"
              style={{ left: `${left}%` }}
            />
          );
        })}

        {currentTime > 0 || playerDuration ? (
          <div
            className="studio-pack-timeline__playhead"
            data-testid="studio-pack-timeline-playhead"
            style={{ left: `${playheadPct}%` }}
            aria-hidden
          />
        ) : null}
      </div>

      {chapters.length > 0 ? (
        <ol className="studio-pack-timeline__chapters" data-testid="studio-pack-timeline-chapters">
          {chapters.map((chapter, index) => {
            const selected = selectedId === chapter.id;
            return (
              <li key={chapter.id}>
                <button
                  type="button"
                  data-testid={`studio-timeline-chapter-row-${index}`}
                  data-selected={selected ? 'true' : 'false'}
                  disabled={!canSeek}
                  title={
                    canSeek
                      ? `Seek to ${formatSeconds(chapter.start)}`
                      : 'Switch URL back to this pack to seek.'
                  }
                  onClick={() => seekMarker(chapter)}
                  className="studio-pack-timeline__chapter-row"
                >
                  <span className="studio-pack-timeline__chapter-time font-mono">
                    {formatSeconds(chapter.start)}
                  </span>
                  <span className="studio-pack-timeline__chapter-topic">{chapter.label}</span>
                </button>
              </li>
            );
          })}
        </ol>
      ) : null}
    </section>
  );
}

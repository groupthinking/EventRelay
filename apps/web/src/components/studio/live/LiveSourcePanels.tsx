'use client';

import type { ReactNode } from 'react';
import { clsx } from 'clsx';
import type { VideoPackKeyframe, VideoPackTranscriptSegment, VideoPackVisualElement } from '@/lib/video-pack';
import type { VideoPackChapter } from '@/lib/video-pack-types';
import { formatTimestamp } from '@/lib/live-studio-tasks';
import { useProgressiveCount } from '@/lib/use-progressive-count';

export function SkeletonRows({ count, label, testId }: { count: number; label: string; testId?: string }) {
  if (count <= 0) return null;
  return (
    <div data-testid={testId} role="status" aria-label={label}>
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="live-skeleton-row" aria-hidden="true">
          <span className="live-skeleton-bar live-skeleton-bar--short" />
          <span className="live-skeleton-bar" style={{ width: `${62 + ((index * 17) % 30)}%` }} />
        </div>
      ))}
    </div>
  );
}

export function LiveSection({
  id,
  title,
  meta,
  children,
  className,
}: {
  id: string;
  title: string;
  meta?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section aria-labelledby={`${id}-title`} data-testid={id} className={clsx('live-section', className)}>
      <header className="live-section__head">
        <h2 id={`${id}-title`} className="live-section__title">{title}</h2>
        {meta ? <span className="live-section__meta">{meta}</span> : null}
      </header>
      {children}
    </section>
  );
}

/** How many skeleton rows to keep visible below already-revealed items. */
function pendingRows(live: boolean, total: number, visible: number, placeholder: number): number {
  if (total > visible) return Math.min(3, total - visible);
  return live && total === 0 ? placeholder : 0;
}

export function LiveChapterRail({
  chapters,
  live,
  canSeek,
  onSeek,
}: {
  chapters: readonly VideoPackChapter[];
  live: boolean;
  canSeek: boolean;
  onSeek: (seconds: number) => void;
}) {
  const visible = useProgressiveCount(chapters.length, { stepMs: 70 });
  return (
    <LiveSection id="live-chapters" title="Chapters" meta={chapters.length ? `${chapters.length}` : undefined}>
      <ol className="live-chapter-list">
        {chapters.slice(0, visible).map((chapter, index) => (
          <li key={`${chapter.start}-${chapter.topic}`} className="live-row-enter">
            <button
              type="button"
              data-testid={`live-chapter-${index}`}
              disabled={!canSeek}
              onClick={() => onSeek(chapter.start)}
              className="live-chapter"
              title={canSeek ? `Seek to ${formatTimestamp(chapter.start)}` : 'Load this video to seek.'}
            >
              <span className="live-chapter__index">{String(index + 1).padStart(2, '0')}</span>
              <span className="live-chapter__topic">{chapter.topic}</span>
              <span className="live-chapter__time">{formatTimestamp(chapter.start)}</span>
            </button>
          </li>
        ))}
      </ol>
      <SkeletonRows
        count={pendingRows(live, chapters.length, visible, 4)}
        label="Waiting for chapters"
        testId="live-chapters-skeleton"
      />
      {!live && chapters.length === 0 ? <p className="live-empty">Chapters appear once a pack is extracted.</p> : null}
    </LiveSection>
  );
}

export function LiveTranscript({
  segments,
  live,
  canSeek,
  onSeek,
}: {
  segments: readonly VideoPackTranscriptSegment[];
  live: boolean;
  canSeek: boolean;
  onSeek: (seconds: number) => void;
}) {
  const visible = useProgressiveCount(segments.length, { stepMs: 35, batch: 2 });
  return (
    <LiveSection
      id="live-transcript"
      title="Transcript"
      meta={segments.length ? `${segments.length} segments${live ? ' · streaming' : ''}` : undefined}
    >
      <ol className="live-transcript" aria-live="polite" aria-relevant="additions">
        {segments.slice(0, visible).map((segment) => (
          <li key={segment.idx} className="live-row-enter">
            <button
              type="button"
              data-testid={`live-transcript-line-${segment.idx}`}
              disabled={!canSeek}
              onClick={() => onSeek(segment.start_s)}
              className="live-transcript__line"
            >
              <span className="live-transcript__time">{formatTimestamp(segment.start_s)}</span>
              <span className="live-transcript__text">{segment.text}</span>
            </button>
          </li>
        ))}
      </ol>
      <SkeletonRows
        count={pendingRows(live, segments.length, visible, 5) || (live && segments.length > 0 ? 2 : 0)}
        label="Transcript still arriving"
        testId="live-transcript-skeleton"
      />
      {!live && segments.length === 0 ? (
        <p className="live-empty">Paste a YouTube link or try the sample to stream a transcript here.</p>
      ) : null}
    </LiveSection>
  );
}

export function LiveKeyframes({
  keyframes,
  live,
  canSeek,
  onSeek,
}: {
  keyframes: readonly VideoPackKeyframe[];
  live: boolean;
  canSeek: boolean;
  onSeek: (seconds: number) => void;
}) {
  const visible = useProgressiveCount(keyframes.length, { stepMs: 90 });
  if (!live && keyframes.length === 0) return null;
  return (
    <LiveSection id="live-keyframes" title="Keyframes" meta={keyframes.length ? `${keyframes.length}` : undefined}>
      <ol className="live-keyframes">
        {keyframes.slice(0, visible).map((frame) => (
          <li key={frame.t_s} className="live-row-enter">
            <button
              type="button"
              data-testid={`live-keyframe-${frame.t_s}`}
              disabled={!canSeek}
              onClick={() => onSeek(frame.t_s)}
              className="live-keyframe"
              title={frame.desc ?? undefined}
            >
              {frame.image_path ? (
                // Pack frames are same-origin stills of varying size; next/image adds nothing here.
                // eslint-disable-next-line @next/next/no-img-element
                <img src={frame.image_path} alt={frame.desc ?? `Keyframe at ${formatTimestamp(frame.t_s)}`} loading="lazy" width={160} height={90} />
              ) : (
                <span className="live-keyframe__blank" aria-hidden="true" />
              )}
              <span className="live-keyframe__time">{formatTimestamp(frame.t_s)}</span>
            </button>
          </li>
        ))}
        {live && keyframes.length === 0
          ? Array.from({ length: 4 }, (_, index) => (
              <li key={`pending-${index}`} aria-hidden="true">
                <span className="live-keyframe live-keyframe--pending" />
              </li>
            ))
          : null}
      </ol>
    </LiveSection>
  );
}

export function LiveEvents({
  events,
  live,
  canSeek,
  onSeek,
}: {
  events: readonly VideoPackVisualElement[];
  live: boolean;
  canSeek: boolean;
  onSeek: (seconds: number) => void;
}) {
  const visible = useProgressiveCount(events.length, { stepMs: 80 });
  if (!live && events.length === 0) return null;
  return (
    <LiveSection id="live-events" title="Events" meta={events.length ? `${events.length} on screen` : undefined}>
      <ol className="live-events">
        {events.slice(0, visible).map((event, index) => (
          <li key={`${event.timestamp}-${index}`} className="live-row-enter">
            <button
              type="button"
              disabled={!canSeek}
              onClick={() => onSeek(event.timestamp)}
              className="live-event"
              data-testid={`live-event-${index}`}
            >
              <span className="live-transcript__time">{formatTimestamp(event.timestamp)}</span>
              <span className="live-event__type">{event.element_type.replace(/[_-]+/g, ' ')}</span>
              <span className="live-event__text">{event.content}</span>
            </button>
          </li>
        ))}
      </ol>
      <SkeletonRows count={pendingRows(live, events.length, visible, 3)} label="Waiting for events" />
    </LiveSection>
  );
}

export type LiveStageState = 'idle' | 'active' | 'done' | 'failed';

export function LiveStageList({ stages }: { stages: ReadonlyArray<{ id: string; label: string; state: LiveStageState; detail?: string }> }) {
  return (
    <ol className="live-stages" aria-label="Build progress" data-testid="live-stages">
      {stages.map((stage) => (
        <li key={stage.id} data-state={stage.state} data-stage={stage.id}>
          <span className="live-stages__dot" aria-hidden="true" />
          <span className="live-stages__label">{stage.label}</span>
          {stage.detail ? <span className="live-stages__detail">{stage.detail}</span> : null}
          <span className="sr-only">{` — ${stage.state}`}</span>
        </li>
      ))}
    </ol>
  );
}

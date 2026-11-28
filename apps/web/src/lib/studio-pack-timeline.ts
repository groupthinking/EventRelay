/**
 * Cut 2 — derive a selection-scoped pack time surface from real pack fields.
 * No invented chapters/keyframes; empty pack → empty markers.
 */

import type { EmittedVideoPack } from '@/lib/emit-video-pack';
import { studioPackExtractedEvents } from '@/lib/studio-pipeline-status';
import { parseTimestampToSeconds } from '@/lib/timestamp';

export type StudioTimelineMarkerKind = 'chapter' | 'keyframe' | 'moment' | 'event';

export interface StudioTimelineMarker {
  id: string;
  kind: StudioTimelineMarkerKind;
  start: number;
  end?: number;
  label: string;
}

function finiteSeconds(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
    return value;
  }
  if (typeof value === 'string') {
    return parseTimestampToSeconds(value);
  }
  return null;
}

/** True when the loaded URL matches the selected pack (selection-scoped seek). */
export function studioPackTimelineCanSeek(input: {
  videoId: string | null | undefined;
  packVideoId: string | null | undefined;
}): boolean {
  const videoId = input.videoId?.trim() ?? '';
  const packVideoId = input.packVideoId?.trim() ?? '';
  if (!videoId) return false;
  if (!packVideoId) return true;
  return videoId === packVideoId;
}

/**
 * Span for laying out the track. Prefer a longer valid player duration;
 * otherwise the furthest marker start or end. Floor is 1s.
 */
export function studioPackTimelineDuration(
  markers: readonly StudioTimelineMarker[],
  playerDuration?: number | null,
): number {
  let span = 0;
  for (const marker of markers) {
    span = Math.max(span, marker.start, marker.end ?? 0);
  }
  const player =
    typeof playerDuration === 'number' && Number.isFinite(playerDuration) && playerDuration > 0
      ? playerDuration
      : 0;
  return Math.max(span, player, 1);
}

/** Chapters (ranges) + keyframes + visual moments + optional pack events[]. */
export function studioPackTimelineMarkers(
  pack: EmittedVideoPack | null | undefined,
): StudioTimelineMarker[] {
  if (!pack) return [];
  const markers: StudioTimelineMarker[] = [];

  (pack.chapters ?? []).forEach((chapter, index) => {
    const start = finiteSeconds(chapter.start);
    if (start == null) return;
    const end = finiteSeconds(chapter.end) ?? undefined;
    const label = chapter.topic?.trim();
    if (!label) return;
    markers.push({
      id: `chapter-${index}`,
      kind: 'chapter',
      start,
      ...(end != null && end >= start ? { end } : {}),
      label,
    });
  });

  (pack.keyframes ?? []).forEach((frame, index) => {
    const start = finiteSeconds(frame.t_s);
    if (start == null) return;
    const label = frame.desc?.trim() || `Keyframe ${index + 1}`;
    markers.push({
      id: `keyframe-${index}`,
      kind: 'keyframe',
      start,
      label,
    });
  });

  (pack.visual_context?.visual_elements ?? []).forEach((element, index) => {
    const start = finiteSeconds(element.timestamp);
    if (start == null) return;
    const label = element.content?.trim() || element.element_type?.trim() || `Moment ${index + 1}`;
    markers.push({
      id: `moment-${index}`,
      kind: 'moment',
      start,
      label,
    });
  });

  studioPackExtractedEvents(pack).forEach((event, index) => {
    const start = finiteSeconds(event.timestamp);
    if (start == null) return;
    markers.push({
      id: event.id || `event-${index}`,
      kind: 'event',
      start,
      label: event.title,
    });
  });

  return markers;
}

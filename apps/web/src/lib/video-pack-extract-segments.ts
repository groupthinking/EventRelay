import 'server-only';

import type { YouTubeMetadata } from '@/lib/youtube-metadata';

/** Target wall-clock span per sectional Gemini call (seconds). */
export const VIDEO_PACK_CHUNK_DURATION_SECONDS = 180;

/** Videos shorter than this use the legacy single-call extract unless chapters split them. */
export const VIDEO_PACK_CHUNKED_EXTRACT_MIN_DURATION_SECONDS = 300;

/** Bounded fan-out for sectional gateway calls (matches events/extract window). */
export const VIDEO_PACK_CHUNK_MAX_PARALLEL = 4;

export interface VideoPackExtractSection {
  index: number;
  start_s: number;
  end_s: number;
  topic: string;
}

function chapterTimeToSeconds(time: string): number | null {
  const parts = time.split(':').map((part) => Number(part.trim()));
  if (parts.some((n) => !Number.isFinite(n) || n < 0)) return null;
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return null;
}

function sectionsFromChapters(
  metadata: YouTubeMetadata,
  durationSeconds: number,
): VideoPackExtractSection[] {
  const starts = metadata.chapters
    .map((chapter) => ({
      start: chapterTimeToSeconds(chapter.time),
      topic: chapter.title.trim(),
    }))
    .filter((row): row is { start: number; topic: string } => row.start !== null && row.topic.length > 0);
  if (starts.length < 2) return [];

  const fallbackEnd = durationSeconds > 0 ? durationSeconds : starts[starts.length - 1].start + 120;
  const sections: VideoPackExtractSection[] = [];
  for (let i = 0; i < starts.length; i++) {
    const current = starts[i];
    const nextStart = starts[i + 1]?.start;
    const end =
      nextStart !== undefined && nextStart > current.start ? nextStart : fallbackEnd;
    sections.push({
      index: i,
      start_s: current.start,
      end_s: Math.max(end, current.start + 1),
      topic: current.topic,
    });
  }
  return sections;
}

function sectionsFromFixedWindows(durationSeconds: number): VideoPackExtractSection[] {
  const duration = Math.max(durationSeconds, VIDEO_PACK_CHUNK_DURATION_SECONDS + 1);
  const sections: VideoPackExtractSection[] = [];
  let start = 0;
  let index = 0;
  while (start < duration) {
    const end = Math.min(start + VIDEO_PACK_CHUNK_DURATION_SECONDS, duration);
    sections.push({
      index,
      start_s: start,
      end_s: end,
      topic: `Part ${index + 1}`,
    });
    start = end;
    index += 1;
  }
  return sections.length > 0 ? sections : [{ index: 0, start_s: 0, end_s: duration, topic: 'full' }];
}

export function planVideoPackExtractSections(
  metadata: YouTubeMetadata | null,
  durationSeconds: number | null,
): VideoPackExtractSection[] {
  const duration = durationSeconds && durationSeconds > 0 ? durationSeconds : 0;

  if (metadata && metadata.chapters.length >= 2) {
    const fromChapters = sectionsFromChapters(metadata, duration);
    if (fromChapters.length >= 2) {
      return fromChapters;
    }
  }

  if (duration >= VIDEO_PACK_CHUNKED_EXTRACT_MIN_DURATION_SECONDS) {
    const windows = sectionsFromFixedWindows(duration);
    if (windows.length >= 2) {
      return windows;
    }
  }

  const topic = metadata?.title?.trim() || 'full';
  const end = duration > 0 ? duration : 600;
  return [{ index: 0, start_s: 0, end_s: end, topic }];
}

export function shouldUseChunkedVideoPackExtract(
  metadata: YouTubeMetadata | null,
  durationSeconds: number | null,
): boolean {
  const sections = planVideoPackExtractSections(metadata, durationSeconds);
  return sections.length >= 2;
}

export async function mapWithBoundedConcurrency<T, R>(
  items: T[],
  limit: number,
  worker: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  if (items.length === 0) return [];
  const results: R[] = new Array(items.length);
  let nextIndex = 0;

  async function runWorker(): Promise<void> {
    while (true) {
      const current = nextIndex;
      nextIndex += 1;
      if (current >= items.length) {
        return;
      }
      results[current] = await worker(items[current], current);
    }
  }

  const poolSize = Math.min(Math.max(1, limit), items.length);
  await Promise.all(Array.from({ length: poolSize }, () => runWorker()));
  return results;
}

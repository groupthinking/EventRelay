/**
 * Timestamp + YouTube helpers for the video-canvas dashboard.
 *
 * These utilities convert between human timestamps ("1:23", "[01:02:03]"),
 * seconds, extract the YouTube video id from a URL, and parse a plain-text
 * transcript into time-synchronized segments for InteractiveTranscript.
 */

import type { TranscriptSegment } from '@/components/InteractiveTranscript';

/** Matches a leading timestamp token, optionally wrapped in [] or (). */
const LEADING_TIMESTAMP =
  /^[\s>-]*[[(]?\s*((?:\d{1,2}:)?\d{1,2}:\d{2})\s*[\])]?\s*/;

/** Matches an optional "Speaker N:" / "Name:" label after the timestamp. */
const SPEAKER_LABEL = /^([A-Za-z][\w .'-]{0,24}):\s+/;

/**
 * Parse a timestamp string like "83", "1:23", "01:23", or "1:02:03" into
 * whole seconds. Returns null when the value cannot be parsed.
 */
export function parseTimestampToSeconds(raw: string | null | undefined): number | null {
  if (raw == null) return null;
  const cleaned = String(raw).trim().replace(/^[[(]|[\])]$/g, '').trim();
  if (!cleaned) return null;

  // Bare seconds ("83" or "83.5").
  if (/^\d+(\.\d+)?$/.test(cleaned)) {
    const n = Number(cleaned);
    return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : null;
  }

  const parts = cleaned.split(':');
  if (parts.length < 2 || parts.length > 3) return null;
  if (!parts.every((p) => /^\d+$/.test(p))) return null;

  const nums = parts.map((p) => parseInt(p, 10));
  let seconds = 0;
  for (const n of nums) seconds = seconds * 60 + n;
  return Number.isFinite(seconds) ? seconds : null;
}

/** Format whole/fractional seconds as "M:SS" or "H:MM:SS". */
export function formatSeconds(totalSeconds: number): string {
  const safe = Number.isFinite(totalSeconds) && totalSeconds > 0 ? Math.floor(totalSeconds) : 0;
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = safe % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

/**
 * Extract the 11-character YouTube video id from any common URL shape
 * (watch?v=, youtu.be/, /embed/, /v/, /shorts/, /live/). Returns null when
 * no id can be found.
 */
export function extractYouTubeId(url: string | null | undefined): string | null {
  if (!url) return null;
  const patterns = [
    /(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|v\/|shorts\/|live\/))([A-Za-z0-9_-]{11})/,
    /youtu\.be\/([A-Za-z0-9_-]{11})/,
  ];
  for (const re of patterns) {
    const m = url.match(re);
    if (m) return m[1];
  }
  // Last resort: a raw 11-char id passed directly.
  if (/^[A-Za-z0-9_-]{11}$/.test(url.trim())) return url.trim();
  return null;
}

/**
 * Build a privacy-friendly embed URL with the JS API enabled. Uses the
 * `youtube-nocookie.com` domain so no tracking cookies are set until the
 * viewer actually plays the video.
 */
export function buildEmbedUrl(videoId: string, origin?: string): string {
  const params = new URLSearchParams({
    enablejsapi: '1',
    rel: '0',
    modestbranding: '1',
    playsinline: '1',
  });
  if (origin) params.set('origin', origin);
  return `https://www.youtube-nocookie.com/embed/${videoId}?${params.toString()}`;
}

export interface ParsedTranscript {
  segments: TranscriptSegment[];
  /** True when real per-line timestamps were detected (enables seeking). */
  hasTimings: boolean;
}

/**
 * Parse a plain-text transcript into segments. When at least a quarter of the
 * non-empty lines carry a leading timestamp, segments are built with real
 * start/end times (seeking enabled). Otherwise `hasTimings` is false and the
 * caller should render a read-only transcript view.
 */
export function parseTranscriptSegments(transcript: string | null | undefined): ParsedTranscript {
  if (!transcript || !transcript.trim()) {
    return { segments: [], hasTimings: false };
  }

  const lines = transcript
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  type Raw = { start: number | null; speaker: string; text: string };
  const raw: Raw[] = [];
  let timestamped = 0;

  for (const line of lines) {
    let rest = line;
    let start: number | null = null;

    const tsMatch = rest.match(LEADING_TIMESTAMP);
    if (tsMatch) {
      start = parseTimestampToSeconds(tsMatch[1]);
      if (start != null) {
        timestamped += 1;
        rest = rest.slice(tsMatch[0].length);
      }
    }

    let speaker = '';
    const spMatch = rest.match(SPEAKER_LABEL);
    if (spMatch) {
      speaker = spMatch[1].trim();
      rest = rest.slice(spMatch[0].length);
    }

    const text = rest.trim();
    if (!text) continue;
    raw.push({ start, speaker, text });
  }

  const hasTimings = raw.length > 0 && timestamped >= Math.max(2, Math.ceil(raw.length * 0.25));

  // Assign a stable speaker rotation so the transcript still shows speaker pills
  // even when the source has no explicit labels.
  const speakerPool = ['Speaker 1', 'Speaker 2', 'Speaker 3'];
  let lastStart = 0;

  const segments: TranscriptSegment[] = raw.map((r, i) => {
    const start = hasTimings ? (r.start ?? lastStart) : i * 6;
    lastStart = start;
    const speaker = r.speaker || speakerPool[i % speakerPool.length];
    return {
      id: `seg-${i}`,
      speaker,
      speakerColor: '',
      startTime: start,
      endTime: start, // patched below
      text: r.text,
    };
  });

  // End time = next segment start (or +5s for the final line).
  for (let i = 0; i < segments.length; i += 1) {
    const next = segments[i + 1];
    segments[i].endTime = next ? Math.max(next.startTime, segments[i].startTime + 1) : segments[i].startTime + 5;
  }

  return { segments, hasTimings };
}

export type TranscriptExportSegment = {
  text: string;
  start?: number;
  duration?: number;
};

export type CaptionSourceLabel = 'Timed captions' | 'ASR fallback' | 'No captions available';

const DEFAULT_SEGMENT_DURATION_SECONDS = 4;

function pad2(value: number): string {
  return String(value).padStart(2, '0');
}

function pad3(value: number): string {
  return String(value).padStart(3, '0');
}

function formatCueTimestamp(seconds: number, decimalSeparator: ',' | '.'): string {
  const safeSeconds = Number.isFinite(seconds) && seconds >= 0 ? seconds : 0;
  const totalMs = Math.round(safeSeconds * 1000);
  const ms = totalMs % 1000;
  const totalWholeSeconds = Math.floor(totalMs / 1000);
  const secs = totalWholeSeconds % 60;
  const mins = Math.floor(totalWholeSeconds / 60) % 60;
  const hours = Math.floor(totalWholeSeconds / 3600);
  return `${pad2(hours)}:${pad2(mins)}:${pad2(secs)}${decimalSeparator}${pad3(ms)}`;
}

function normalizeCues(
  segments: readonly TranscriptExportSegment[],
): Array<{ start: number; end: number; text: string }> {
  const cues: Array<{ start: number; end: number; text: string }> = [];
  for (const segment of segments) {
    const text = typeof segment.text === 'string' ? segment.text.trim() : '';
    if (!text) continue;
    const start =
      typeof segment.start === 'number' && Number.isFinite(segment.start) && segment.start >= 0
        ? segment.start
        : 0;
    const duration =
      typeof segment.duration === 'number' &&
      Number.isFinite(segment.duration) &&
      segment.duration > 0
        ? segment.duration
        : DEFAULT_SEGMENT_DURATION_SECONDS;
    cues.push({ start, end: start + duration, text });
  }
  return cues;
}

/**
 * Format transcript segments into SubRip (.srt) subtitle text.
 */
export function formatSrt(segments: Array<TranscriptExportSegment>): string {
  const cues = normalizeCues(segments);
  if (cues.length === 0) return '';
  return cues
    .map(
      (cue, index) =>
        `${index + 1}\n${formatCueTimestamp(cue.start, ',')} --> ${formatCueTimestamp(cue.end, ',')}\n${cue.text}`,
    )
    .join('\n\n')
    .concat('\n');
}

/**
 * Format transcript segments into WebVTT (.vtt) subtitle text.
 */
export function formatVtt(segments: Array<TranscriptExportSegment>): string {
  const cues = normalizeCues(segments);
  if (cues.length === 0) return 'WEBVTT\n\n';
  const body = cues
    .map(
      (cue) =>
        `${formatCueTimestamp(cue.start, '.')} --> ${formatCueTimestamp(cue.end, '.')}\n${cue.text}`,
    )
    .join('\n\n');
  return `WEBVTT\n\n${body}\n`;
}

/**
 * Resolve a concise caption-source status label from transcript/provenance metadata.
 */
export function resolveCaptionSourceLabel(input: {
  transcriptSource?: string | null;
  acquisitionMethod?: string | null;
  timedSegmentCount?: number;
  hasTranscriptText?: boolean;
}): CaptionSourceLabel {
  const sourceHint = `${input.transcriptSource ?? ''} ${input.acquisitionMethod ?? ''}`.toLowerCase();
  if (/(whisper|stt|asr|speech|audio)/i.test(sourceHint)) {
    return 'ASR fallback';
  }
  if ((input.timedSegmentCount ?? 0) > 0) {
    return 'Timed captions';
  }
  if (input.hasTranscriptText) {
    return 'ASR fallback';
  }
  return 'No captions available';
}

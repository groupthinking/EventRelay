export type EvidenceState =
  | 'verified'
  | 'degraded'
  | 'processing'
  | 'failed'
  | 'unavailable';

export interface TranscriptSegment {
  start: number;
  duration: number;
  text: string;
}

export interface AnalysisProvenance {
  sourceUrl: string;
  sourceHost: string;
  acquisitionMethod: string;
  transcriptSource: string;
  transcriptVerified: boolean;
  acquiredAt: string;
  segmentCount: number;
  timedSegmentCount: number;
  durationCoverageSeconds: number | null;
  contentSha256?: string;
  warnings: string[];
}

export interface EvidenceAssessment {
  state: EvidenceState;
  passed: boolean;
  issues: string[];
  transcriptCharacters: number;
  segmentCount: number;
  timedSegmentCount: number;
  checkedAt: string;
}

const TRUSTED_TRANSCRIPT_SOURCES = new Set([
  'youtube',
  'youtube-api',
  'youtube_api',
  'youtube-captions',
  'youtube-transcript-api',
  'youtube_transcript_api',
  'innertube',
  'innertube-android',
  'innertube_android',
  'openai-stt',
  'whisper',
]);

const TRANSCRIPT_ADVICE_PATTERNS = [
  /i (?:do not|don't) have direct access to (?:the )?transcript/i,
  /you can obtain (?:it|the transcript) using/i,
  /paste (?:the )?youtube (?:link|url)/i,
  /click (?:on )?(?:show transcript|the three dots)/i,
  /transcript\.you/i,
  /quicktranscript\.ai/i,
  /transcriptgrab/i,
  /audexum/i,
  /yttranscript\.ai/i,
  /unable to access the transcript/i,
  /i attempted to retrieve the transcript/i,
  /online tools designed for this purpose/i,
  /to obtain the transcript, you can use/i,
];

export function normalizeTranscriptSegments(raw: unknown): TranscriptSegment[] {
  if (!Array.isArray(raw)) return [];

  return raw.flatMap((value) => {
    if (!value || typeof value !== 'object') return [];
    const segment = value as Record<string, unknown>;
    const text = typeof segment.text === 'string' ? segment.text.trim() : '';
    if (!text) return [];

    const start = Number(segment.start);
    const duration = Number(segment.duration);
    return [{
      start: Number.isFinite(start) && start >= 0 ? start : 0,
      duration: Number.isFinite(duration) && duration > 0 ? duration : 0,
      text,
    }];
  });
}

export function transcriptTextFromSegments(segments: TranscriptSegment[]): string {
  return segments.map((segment) => segment.text).join(' ').trim();
}

/**
 * Return the union of timed caption intervals.
 *
 * Caption providers commonly return overlapping durations. Summing every
 * duration double-counts those overlaps and can report more coverage than the
 * video actually contains.
 */
export function calculateDurationCoverageSeconds(segments: TranscriptSegment[]): number | null {
  const intervals = segments
    .filter((segment) => segment.duration > 0 && segment.start >= 0)
    .map((segment) => [segment.start, segment.start + segment.duration] as const)
    .sort((left, right) => left[0] - right[0]);
  if (intervals.length === 0) return null;

  let covered = 0;
  let start = intervals[0][0];
  let end = intervals[0][1];
  for (const [nextStart, nextEnd] of intervals.slice(1)) {
    if (nextStart <= end) {
      end = Math.max(end, nextEnd);
      continue;
    }
    covered += end - start;
    start = nextStart;
    end = nextEnd;
  }
  covered += end - start;
  return covered;
}

export function hasTranscriptAdvice(text: string): boolean {
  return TRANSCRIPT_ADVICE_PATTERNS.some((pattern) => pattern.test(text));
}

export function isTrustedTranscriptSource(source: string): boolean {
  return TRUSTED_TRANSCRIPT_SOURCES.has(source.trim().toLowerCase());
}

export function assessAnalysisEvidence(input: {
  transcript: string;
  segments: TranscriptSegment[];
  provenance: AnalysisProvenance;
  now?: string;
}): EvidenceAssessment {
  const transcript = input.transcript.trim();
  const issues: string[] = [];
  const segmentCount = input.segments.length;
  const timedSegmentCount = input.segments.filter(
    (segment) => segment.duration > 0 && segment.start >= 0,
  ).length;

  if (!input.provenance.transcriptVerified) {
    issues.push('Transcript acquisition was not verified by a source provider.');
  }
  if (!isTrustedTranscriptSource(input.provenance.transcriptSource)) {
    issues.push(`Transcript source is not trusted: ${input.provenance.transcriptSource || 'unknown'}.`);
  }

  const fatal: string[] = [];
  if (transcript.length < 40) {
    fatal.push('Transcript is empty or too short to support analysis.');
  }
  if (hasTranscriptAdvice(transcript)) {
    fatal.push('Transcript contains transcript-retrieval advice instead of source speech.');
  }
  if (input.provenance.sourceUrl.trim().length === 0) {
    fatal.push('Source URL is unavailable.');
  }

  const passed = fatal.length === 0;
  const trusted =
    input.provenance.transcriptVerified &&
    isTrustedTranscriptSource(input.provenance.transcriptSource);
  const state: EvidenceState = !passed
    ? transcript.length === 0
      ? 'unavailable'
      : 'failed'
    : trusted && timedSegmentCount === segmentCount && segmentCount > 0
      ? 'verified'
      : 'degraded';
  issues.push(...fatal);

  return {
    state,
    passed,
    issues,
    transcriptCharacters: transcript.length,
    segmentCount,
    timedSegmentCount,
    checkedAt: input.now ?? new Date().toISOString(),
  };
}

/** Fatal only when the evidence gate itself failed — degraded derived speech still completes. */
export function fatalQualityFailure(quality?: EvidenceAssessment): string | null {
  if (quality?.passed) return null;
  return `Analysis quality gate failed: ${quality?.issues.join(' ') || 'missing provenance'}`;
}

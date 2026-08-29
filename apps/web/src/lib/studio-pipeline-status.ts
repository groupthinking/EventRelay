export type StudioRunQuality = 'idle' | 'live' | 'draft';

export interface StudioPipelineCheck {
  ok: boolean;
  status: number;
  pipeline?: string;
  jobId?: string;
  message?: string;
}

const LIVE_PIPELINES = new Set(['backend-async', 'backend', 'gemini-only']);

/** Live means we have analysis payload, not that a kickoff returned a job id. */
export function studioRunQuality(
  check: StudioPipelineCheck | null,
  unsafe: boolean,
  hasVideo: boolean,
  payload?: { transcript?: string | null; eventCount?: number },
): StudioRunQuality {
  if (!hasVideo || unsafe) return 'draft';
  const transcript = payload?.transcript?.trim() ?? '';
  const events = payload?.eventCount ?? 0;
  if (transcript.length >= 40 || events > 0) return 'live';
  if (!check) return 'draft';
  if (check.jobId) return 'draft';
  if (check.ok && check.pipeline && LIVE_PIPELINES.has(check.pipeline)) return 'draft';
  return 'draft';
}

export function studioStatusLabel(
  quality: StudioRunQuality,
  runState: 'idle' | 'working' | 'ready',
): string {
  if (runState === 'working') return 'Working';
  if (runState === 'idle') return 'Idle';
  if (runState === 'ready' && quality === 'live') return 'Analysis ready';
  if (runState === 'ready') return 'No transcript yet';
  return 'Idle';
}

export function studioStatusMessage(
  quality: StudioRunQuality,
  runState: 'idle' | 'working' | 'ready',
  outcomeLabel: string,
  unsafe: boolean,
): string {
  if (unsafe) {
    return 'Safe alternative prepared. Harmful instructions stay out of the output.';
  }
  if (runState === 'working') {
    return `Analyzing the video — transcript and events will appear here.`;
  }
  if (runState === 'ready' && quality === 'live') {
    return `${outcomeLabel} ready. Act, export, or save from this same run.`;
  }
  if (runState === 'ready') {
    return `No usable transcript or events came back. Try another public video or sign in if the enrich path is gated.`;
  }
  return 'Paste a YouTube URL. UVAI transcribes it, extracts events, then you can act.';
}
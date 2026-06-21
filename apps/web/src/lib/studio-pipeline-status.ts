export type StudioRunQuality = 'idle' | 'live' | 'draft';

export interface StudioPipelineCheck {
  ok: boolean;
  status: number;
  pipeline?: string;
  jobId?: string;
  message?: string;
}

const LIVE_PIPELINES = new Set(['backend-async', 'backend', 'gemini-only']);

export function studioRunQuality(
  check: StudioPipelineCheck | null,
  unsafe: boolean,
  hasVideo: boolean,
): StudioRunQuality {
  if (!hasVideo || unsafe) return 'draft';
  if (!check) return 'draft';
  if (check.jobId) return 'live';
  if (check.ok && check.pipeline && LIVE_PIPELINES.has(check.pipeline)) return 'live';
  return 'draft';
}

export function studioStatusLabel(
  quality: StudioRunQuality,
  runState: 'idle' | 'working' | 'ready',
): string {
  if (runState === 'working') return 'Working';
  if (runState === 'idle') return 'Idle';
  if (runState === 'ready' && quality === 'live') return 'Backend connected';
  if (runState === 'ready') return 'Draft only';
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
    return `Checking backend and preparing a ${outcomeLabel.toLowerCase()} draft.`;
  }
  if (runState === 'ready' && quality === 'live') {
    return `${outcomeLabel} draft ready. Open Dashboard for live transcript and agent analysis.`;
  }
  if (runState === 'ready') {
    return `${outcomeLabel} planning draft only — not a live pipeline result. Use Dashboard for real analysis.`;
  }
  return 'Studio builds local planning drafts. Dashboard runs the live agent pipeline.';
}
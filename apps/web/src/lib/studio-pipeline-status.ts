import type { VideoPackCitation } from '@/lib/emit-video-pack';
import { stackChecksFromPackTools, type ChecklistItem } from '@/lib/linked-sop';
import type {
  VideoPackArchitecture,
  VideoPackArtifact,
  VideoPackStackTool,
} from '@/lib/video-pack-types';

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

export function studioPackCitation(pack: VideoPackCitation): string {
  return `cite:youtube:${pack.videoId} · ${pack.version} · ${pack.sourceHash} · ${pack.sourceUrl}`;
}

export function studioPackFormation(pack: VideoPackCitation | null | undefined): {
  tools: VideoPackStackTool[];
  checks: ChecklistItem[];
  architecture: VideoPackArchitecture | null;
  artifacts: VideoPackArtifact[];
} {
  const tools = pack?.pack.stack?.tools ?? [];
  return {
    tools,
    checks: stackChecksFromPackTools(tools),
    architecture: pack?.pack.architecture ?? null,
    artifacts: pack?.pack.artifacts ?? [],
  };
}

export function studioEventsEmptyMessage(input: {
  busy: boolean;
  hasCompletedRun: boolean;
  eventCount: number;
  hasArchitecture: boolean;
  artifactCount: number;
  toolCount: number;
}): string {
  if (input.eventCount > 0) return '';
  if (input.busy) return 'Extracting events…';
  if (!input.hasCompletedRun) return 'Events show up after Run.';
  const packReady =
    input.hasArchitecture || input.artifactCount > 0 || input.toolCount > 0;
  if (packReady) {
    return 'This pack has no extracted events. Architecture, artifacts, and stack from the video are below — export them from this page.';
  }
  return 'This run has no extracted events. Transcript and pack identity stay on this page.';
}

export function studioPromotePackWorkbench(input: {
  eventCount: number;
  hasArchitecture: boolean;
  artifactCount: number;
  toolCount: number;
}): boolean {
  if (input.eventCount > 0) return false;
  return input.hasArchitecture || input.artifactCount > 0 || input.toolCount > 0;
}

export function studioCanExport(input: {
  transcript?: string | null;
  eventCount?: number;
  hasArchitecture?: boolean;
  artifactCount?: number;
  toolCount?: number;
  hasLinkedSopSteps?: boolean;
  hasProjectScaffold?: boolean;
}): boolean {
  const transcript = input.transcript?.trim() ?? '';
  return (
    transcript.length >= 40 ||
    (input.eventCount ?? 0) > 0 ||
    Boolean(input.hasArchitecture) ||
    (input.artifactCount ?? 0) > 0 ||
    (input.toolCount ?? 0) > 0 ||
    Boolean(input.hasLinkedSopSteps) ||
    Boolean(input.hasProjectScaffold)
  );
}

export function studioInvalidHandoffMessage(raw: string): string {
  const preview = raw.trim() || 'that input';
  return `Need a valid YouTube URL. "${preview}" is not a watchable video.`;
}

export function studioPasteOutcomeMessage(input: {
  hasUsableTranscript: boolean;
  packCitation?: string | null;
}): string {
  if (input.hasUsableTranscript) {
    return 'Ready — run tools, export, or save from this page.';
  }
  if (input.packCitation) {
    return `Identity pack ${input.packCitation}. No usable transcript.`;
  }
  return 'Pack emit failed: verification failed (source_url + source_hash required).';
}

export const STUDIO_TRANSCRIPT_TYPICAL_SECONDS = 45;

export type StudioTranscriptStageId =
  | 'idle'
  | 'pack'
  | 'captions'
  | 'transcript'
  | 'events'
  | 'ready'
  | 'failed';

export function studioTranscriptStage(input: {
  busy: boolean;
  elapsedSeconds: number;
  progress?: number;
  hasPack?: boolean;
  hasTranscript?: boolean;
  hasFailed?: boolean;
}): { id: StudioTranscriptStageId; label: string } {
  if (input.hasFailed) {
    return { id: 'failed', label: 'Transcript failed' };
  }
  if (input.hasTranscript && !input.busy) {
    return { id: 'ready', label: 'Transcript ready' };
  }
  if (!input.busy) {
    return { id: 'idle', label: 'Waiting for a video' };
  }
  if (input.hasTranscript) {
    return { id: 'events', label: 'Extracting events' };
  }
  const progress = input.progress ?? 0;
  if (progress >= 10 || input.elapsedSeconds >= 18) {
    return { id: 'transcript', label: 'Building transcript' };
  }
  if (input.hasPack || progress >= 5 || input.elapsedSeconds >= 6) {
    return { id: 'captions', label: 'Fetching captions' };
  }
  return { id: 'pack', label: 'Pack identity' };
}

export function studioTranscriptEtaLabel(
  elapsedSeconds: number,
  typicalSeconds = STUDIO_TRANSCRIPT_TYPICAL_SECONDS,
): string {
  const remaining = Math.max(0, typicalSeconds - Math.max(0, elapsedSeconds));
  if (remaining === 0) {
    return 'Still working — typical run is about 45s';
  }
  return `About ${remaining}s left (typical ~45s)`;
}

export function studioCanRetryTranscript(input: {
  busy: boolean;
  hasFailed?: boolean;
  retryable?: boolean;
  elapsedSeconds?: number;
}): boolean {
  if (input.busy) {
    return (input.elapsedSeconds ?? 0) >= 90;
  }
  return Boolean(input.hasFailed && input.retryable !== false);
}

/** A real deploy receipt is an https live URL. Workflow "completed" is not. */
export function studioHasDeployReceipt(liveUrl?: string | null): boolean {
  return Boolean(liveUrl && /^https:\/\//i.test(liveUrl));
}

export function studioDeployOutcomeMessage(input: {
  liveUrl?: string | null;
  runStatus?: string | null;
  error?: string | null;
  kind?: string | null;
  message?: string | null;
}): string {
  const error = input.error?.trim();
  if (error) return error;
  if (studioHasDeployReceipt(input.liveUrl)) {
    return `Deploy receipt: ${input.liveUrl}`;
  }
  const status = (input.runStatus || '').toLowerCase();
  if (status === 'failed' || status === 'cancelled' || status === 'error') {
    return `Deploy ${status}. No verified live URL.`;
  }
  const handoff = input.message?.trim();
  if (input.kind === 'handoff' && handoff) return handoff;
  return 'Deploy attempt finished. No verified deploy receipt — UNKNOWN checks are not a live URL.';
}

export function studioDeployButtonLabel(_hasReceipt: boolean): string {
  return 'Attempt deploy';
}

export function studioDeployEnabledHint(hasReceipt: boolean): string {
  if (hasReceipt) return 'A live URL was returned. That is the receipt — not the enabled button.';
  return 'Starts an attempt. UNKNOWN checks are not a deploy receipt.';
}

export type StudioPlayerPhase = 'empty' | 'loading' | 'ready' | 'error';

export function studioPlayerPhase(input: {
  videoId?: string | null;
  loaded?: boolean;
  failed?: boolean;
  timedOut?: boolean;
}): StudioPlayerPhase {
  if (!input.videoId) return 'empty';
  if (input.failed) return 'error';
  if (input.loaded) return 'ready';
  if (input.timedOut) return 'error';
  return 'loading';
}

export function studioPlayerOverlay(phase: StudioPlayerPhase): string | null {
  if (phase === 'loading') return 'Loading video…';
  if (phase === 'error') return 'Video did not load. Retry or open on YouTube.';
  return null;
}
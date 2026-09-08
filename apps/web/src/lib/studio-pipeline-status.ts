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

export type StudioRunStatus = 'processing' | 'complete' | 'failed';

export function studioEventsEmptyMessage(input: {
  busy: boolean;
  runStatus?: StudioRunStatus | null;
  eventCount: number;
  hasArchitecture: boolean;
  artifactCount: number;
  toolCount: number;
}): string {
  if (input.eventCount > 0) return '';
  if (input.busy || input.runStatus === 'processing') return 'Extracting events…';
  if (input.runStatus === 'failed') {
    return 'Analysis failed. No events were extracted. Transcript or pack identity may still be on this page.';
  }
  if (input.runStatus !== 'complete') return 'Events show up after Run.';
  const packReady =
    input.hasArchitecture || input.artifactCount > 0 || input.toolCount > 0;
  if (packReady) {
    return 'This pack has no extracted events. Architecture, artifacts, and stack from the video are on this page — export them here.';
  }
  return 'This run has no extracted events. Transcript and pack identity stay on this page.';
}

export function studioPromotePackWorkbench(input: {
  eventCount: number;
  hasArchitecture: boolean;
  artifactCount: number;
  toolCount: number;
}): boolean {
  const hasFormation =
    input.hasArchitecture || input.artifactCount > 0 || input.toolCount > 0;
  if (!hasFormation) return false;
  if (input.eventCount === 0) return true;
  // Named tools empty + architecture/artifacts: still promote the workbench.
  return input.toolCount === 0 && (input.hasArchitecture || input.artifactCount > 0);
}

export function studioWorkingMessage(input: {
  elapsedSec: number;
  hasPack: boolean;
  packCitation?: string | null;
  hasTranscript: boolean;
}): string {
  if (input.hasTranscript) return 'Transcript landed — finishing analysis…';
  if (input.hasPack) {
    const cite = input.packCitation?.trim();
    return cite
      ? `Pack ready · ${cite}. Waiting on transcript (${input.elapsedSec}s)…`
      : `Pack ready. Waiting on transcript (${input.elapsedSec}s)…`;
  }
  return `Fetching pack and transcript (${input.elapsedSec}s)…`;
}

export function studioActActionLabel(action: {
  tool?: string;
  status?: string;
  result?: string;
}): { title: string; detail?: string } {
  if ((action.tool || '') === 'review_action') {
    return {
      title: action.result?.trim() || 'Review this finding',
      detail:
        action.status === 'proposed'
          ? 'Proposed from this run — not an executed tool.'
          : action.status || undefined,
    };
  }
  const title = action.tool?.trim() || 'Action';
  const detail = [action.status, action.result].filter(Boolean).join(' — ') || undefined;
  return { title, detail };
}

export function studioExportOutcomeMessage(input: {
  officialClone?: string | null;
  hasLinkedSop?: boolean;
  hasArchitecture?: boolean;
  artifactCount?: number;
  toolCount?: number;
}): string {
  if (input.officialClone) {
    return `Exported ${input.officialClone} plus SOP and DEPLOY.md.`;
  }
  if (input.hasLinkedSop) {
    return 'Exported SOP, named tools, and DEPLOY.md from this run.';
  }
  const parts: string[] = [];
  if (input.hasArchitecture) parts.push('architecture');
  if ((input.artifactCount ?? 0) > 0) parts.push('artifacts');
  if ((input.toolCount ?? 0) > 0) parts.push('named tools');
  if (parts.length > 0) {
    return `Exported ${parts.join(', ')} from this pack.`;
  }
  return 'Exported scaffold files (README, tasks.json).';
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
    return 'Ready — act on this run, export, or save from this page.';
  }
  if (input.packCitation) {
    return `Identity pack ${input.packCitation}. No usable transcript.`;
  }
  return 'Pack emit failed: verification failed (source_url + source_hash required).';
}
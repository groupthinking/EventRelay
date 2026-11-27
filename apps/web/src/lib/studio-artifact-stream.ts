/**
 * Cut 3 — derive the Agents-stream pack-forming artifact from real extract
 * stages and real pack formation. No invented stages or mock pack preview.
 */

import type { StudioTranscriptStageId } from '@/lib/studio-pipeline-status';
import { studioTranscriptStage } from '@/lib/studio-pipeline-status';
import type {
  VideoPackArchitecture,
  VideoPackArtifact,
  VideoPackStackTool,
} from '@/lib/video-pack-types';

export type StudioArtifactStreamPhase =
  | 'hidden'
  | 'skeletal'
  | 'filling'
  | 'settled'
  | 'failed';

export type StudioArtifactStreamRowState =
  | 'skeletal'
  | 'pending'
  | 'active'
  | 'done'
  | 'failed';

export type StudioArtifactStreamStepId =
  | 'pack'
  | 'captions'
  | 'transcript'
  | 'events'
  | 'ready';

export interface StudioArtifactStreamRow {
  id: StudioArtifactStreamStepId;
  label: string;
  state: StudioArtifactStreamRowState;
}

export interface StudioArtifactStreamPreview {
  architectureSummary: string | null;
  architectureStages: Array<{ id: string; name: string }>;
  artifacts: Array<{ path_hint: string; purpose: string }>;
  tools: Array<{ name: string }>;
}

export const STUDIO_ARTIFACT_STREAM_STEPS: ReadonlyArray<{
  id: StudioArtifactStreamStepId;
  label: string;
}> = [
  { id: 'pack', label: 'Pack identity' },
  { id: 'captions', label: 'Captions & audio' },
  { id: 'transcript', label: 'Building transcript' },
  { id: 'events', label: 'Extracting events & tasks' },
  { id: 'ready', label: 'Pack ready' },
] as const;

const STEP_INDEX: Record<StudioArtifactStreamStepId, number> = {
  pack: 0,
  captions: 1,
  transcript: 2,
  events: 3,
  ready: 4,
};

/** Map transcript-stage ids onto the five extract rows (real stages only). */
export function studioArtifactStreamStepIndex(
  stageId: StudioTranscriptStageId,
): number {
  switch (stageId) {
    case 'ready':
      return STEP_INDEX.ready;
    case 'events':
      return STEP_INDEX.events;
    case 'transcript':
      return STEP_INDEX.transcript;
    case 'captions':
      return STEP_INDEX.captions;
    case 'pack':
      return STEP_INDEX.pack;
    case 'failed':
      return STEP_INDEX.pack;
    case 'idle':
      return STEP_INDEX.pack;
    default: {
      const _exhaustive: never = stageId;
      return _exhaustive;
    }
  }
}

export function studioArtifactStreamPhase(input: {
  busy: boolean;
  hasFailed?: boolean;
  hasPack?: boolean;
  hasTranscript?: boolean;
  stageId: StudioTranscriptStageId;
}): StudioArtifactStreamPhase {
  if (input.hasFailed) return 'failed';
  if (input.busy) {
    // Early pack-identity stage keeps the skeletal panel; later stages fill rows.
    if (input.stageId === 'pack' || input.stageId === 'idle') return 'skeletal';
    return 'filling';
  }
  if (input.hasPack || (input.hasTranscript && input.stageId === 'ready')) {
    return 'settled';
  }
  return 'hidden';
}

export function studioArtifactStreamRows(input: {
  phase: StudioArtifactStreamPhase;
  stageId: StudioTranscriptStageId;
}): StudioArtifactStreamRow[] {
  if (input.phase === 'hidden') return [];

  if (input.phase === 'skeletal') {
    return STUDIO_ARTIFACT_STREAM_STEPS.map((step) => ({
      id: step.id,
      label: step.label,
      state: 'skeletal' as const,
    }));
  }

  const activeIdx = studioArtifactStreamStepIndex(input.stageId);

  return STUDIO_ARTIFACT_STREAM_STEPS.map((step, index) => {
    let state: StudioArtifactStreamRowState;
    if (input.phase === 'settled') {
      state = 'done';
    } else if (input.phase === 'failed') {
      if (index < activeIdx) state = 'done';
      else if (index === activeIdx) state = 'failed';
      else state = 'pending';
    } else if (index < activeIdx) {
      state = 'done';
    } else if (index === activeIdx) {
      state = 'active';
    } else {
      state = 'pending';
    }
    return { id: step.id, label: step.label, state };
  });
}

/**
 * Settled preview from real pack formation only. Returns null when there is
 * nothing real to show — never invents architecture, artifacts, or tools.
 */
export function studioArtifactStreamPreview(formation: {
  architecture: VideoPackArchitecture | null | undefined;
  artifacts: VideoPackArtifact[] | null | undefined;
  tools: VideoPackStackTool[] | null | undefined;
} | null | undefined): StudioArtifactStreamPreview | null {
  if (!formation) return null;

  const architecture = formation.architecture ?? null;
  const summary = architecture?.summary?.trim() || null;
  const architectureStages = (architecture?.stages ?? [])
    .map((stage, index) => {
      const name = stage.name?.trim() ?? '';
      if (!name) return null;
      const id = stage.id?.trim() || `stage-${index}`;
      return { id, name };
    })
    .filter((row): row is { id: string; name: string } => row !== null);

  const artifacts = (formation.artifacts ?? [])
    .map((artifact) => {
      const path_hint = artifact.path_hint?.trim() ?? '';
      if (!path_hint) return null;
      return {
        path_hint,
        purpose: artifact.purpose?.trim() ?? '',
      };
    })
    .filter((row): row is { path_hint: string; purpose: string } => row !== null);

  const tools = (formation.tools ?? [])
    .map((tool) => {
      const name = tool.name?.trim() ?? '';
      if (!name) return null;
      return { name };
    })
    .filter((row): row is { name: string } => row !== null);

  if (!summary && architectureStages.length === 0 && artifacts.length === 0 && tools.length === 0) {
    return null;
  }

  return {
    architectureSummary: summary,
    architectureStages,
    artifacts,
    tools,
  };
}

export function studioArtifactStreamModel(input: {
  busy: boolean;
  elapsedSeconds?: number;
  progress?: number;
  hasPack?: boolean;
  hasPackIdentity?: boolean;
  hasTranscript?: boolean;
  hasFailed?: boolean;
  formation?: {
    architecture: VideoPackArchitecture | null | undefined;
    artifacts: VideoPackArtifact[] | null | undefined;
    tools: VideoPackStackTool[] | null | undefined;
  } | null;
}): {
  stageId: StudioTranscriptStageId;
  phase: StudioArtifactStreamPhase;
  rows: StudioArtifactStreamRow[];
  preview: StudioArtifactStreamPreview | null;
} {
  const stage = studioTranscriptStage({
    busy: input.busy,
    elapsedSeconds: input.elapsedSeconds ?? 0,
    progress: input.progress,
    hasPack: input.hasPack,
    hasPackIdentity: input.hasPackIdentity,
    hasTranscript: input.hasTranscript,
    hasFailed: input.hasFailed,
  });
  const phase = studioArtifactStreamPhase({
    busy: input.busy,
    hasFailed: input.hasFailed,
    hasPack: input.hasPack,
    hasTranscript: input.hasTranscript,
    stageId: stage.id,
  });
  const rows = studioArtifactStreamRows({ phase, stageId: stage.id });
  const preview =
    phase === 'settled' || phase === 'filling'
      ? studioArtifactStreamPreview(input.formation)
      : phase === 'failed'
        ? studioArtifactStreamPreview(input.formation)
        : null;

  return { stageId: stage.id, phase, rows, preview };
}

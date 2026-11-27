import type { StudioTranscriptStageId } from '@/lib/studio-pipeline-status';
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

export type StudioArtifactStreamFormation = {
  architecture: VideoPackArchitecture | null;
  artifacts: VideoPackArtifact[];
  tools: VideoPackStackTool[];
};

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

export function studioArtifactStreamStepIndex(
  stageId: StudioTranscriptStageId,
): number {
  if (stageId === 'failed' || stageId === 'idle') return STEP_INDEX.pack;
  return STEP_INDEX[stageId];
}

export function studioArtifactStreamPhase(input: {
  busy: boolean;
  hasFailed?: boolean;
  hasPack?: boolean;
  hasPackIdentity?: boolean;
  hasTranscript?: boolean;
  stageId: StudioTranscriptStageId;
}): StudioArtifactStreamPhase {
  if (input.hasFailed) return 'failed';
  if (input.busy) {
    // Unresolved initial identity stays skeletal. Once pack identity is verified
    // (hasPackIdentity), leave skeletal even if transcriptStage still reports
    // "pack" during the analysis wait — fill rows and surface available evidence.
    if (
      (input.stageId === 'pack' || input.stageId === 'idle') &&
      !input.hasPackIdentity
    ) {
      return 'skeletal';
    }
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
  hasPackIdentity?: boolean;
}): StudioArtifactStreamRow[] {
  if (input.phase === 'hidden') return [];

  if (input.phase === 'skeletal') {
    return STUDIO_ARTIFACT_STREAM_STEPS.map((step) => ({
      id: step.id,
      label: step.label,
      state: 'skeletal' as const,
    }));
  }

  let activeIdx = studioArtifactStreamStepIndex(input.stageId);
  // Verified identity completes the pack row; advance the active marker to the
  // next extract stage while transcriptStage may still report "pack".
  if (
    input.phase === 'filling' &&
    input.hasPackIdentity &&
    input.stageId === 'pack'
  ) {
    activeIdx = STEP_INDEX.captions;
  }

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

export function studioArtifactStreamPreview(
  formation: StudioArtifactStreamFormation | null | undefined,
): StudioArtifactStreamPreview | null {
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
  stageId: StudioTranscriptStageId;
  hasPack?: boolean;
  hasPackIdentity?: boolean;
  hasTranscript?: boolean;
  hasFailed?: boolean;
  formation?: StudioArtifactStreamFormation | null;
}): {
  stageId: StudioTranscriptStageId;
  phase: StudioArtifactStreamPhase;
  rows: StudioArtifactStreamRow[];
  preview: StudioArtifactStreamPreview | null;
} {
  const phase = studioArtifactStreamPhase({
    busy: input.busy,
    hasFailed: input.hasFailed,
    hasPack: input.hasPack,
    hasPackIdentity: input.hasPackIdentity,
    hasTranscript: input.hasTranscript,
    stageId: input.stageId,
  });
  const rows = studioArtifactStreamRows({
    phase,
    stageId: input.stageId,
    hasPackIdentity: input.hasPackIdentity,
  });
  const preview =
    phase === 'hidden' || phase === 'skeletal'
      ? null
      : studioArtifactStreamPreview(input.formation);

  return { stageId: input.stageId, phase, rows, preview };
}

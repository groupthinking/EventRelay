import { describe, expect, it } from 'vitest';
import { loadSamplePack } from '@/lib/sample-pack';
import {
  studioArtifactStreamModel,
  studioArtifactStreamPhase,
  studioArtifactStreamPreview,
  studioArtifactStreamRows,
  studioArtifactStreamStepIndex,
} from '@/lib/studio-artifact-stream';
import { studioPackFormation } from '@/lib/studio-pipeline-status';

describe('studio-artifact-stream', () => {
  it('maps real transcript stages onto extract row indexes', () => {
    expect(studioArtifactStreamStepIndex('pack')).toBe(0);
    expect(studioArtifactStreamStepIndex('captions')).toBe(1);
    expect(studioArtifactStreamStepIndex('transcript')).toBe(2);
    expect(studioArtifactStreamStepIndex('events')).toBe(3);
    expect(studioArtifactStreamStepIndex('ready')).toBe(4);
  });

  it('starts skeletal, fills on later stages, settles when pack is ready', () => {
    expect(
      studioArtifactStreamPhase({
        busy: true,
        stageId: 'pack',
      }),
    ).toBe('skeletal');

    expect(
      studioArtifactStreamPhase({
        busy: true,
        stageId: 'transcript',
      }),
    ).toBe('filling');

    expect(
      studioArtifactStreamPhase({
        busy: false,
        hasPack: true,
        stageId: 'ready',
      }),
    ).toBe('settled');

    expect(
      studioArtifactStreamPhase({
        busy: false,
        hasFailed: true,
        stageId: 'failed',
      }),
    ).toBe('failed');

    expect(
      studioArtifactStreamPhase({
        busy: false,
        stageId: 'idle',
      }),
    ).toBe('hidden');
  });

  it('keeps skeletal rows empty of invented labels and fills only real stages', () => {
    const skeletal = studioArtifactStreamRows({
      phase: 'skeletal',
      stageId: 'pack',
    });
    expect(skeletal).toHaveLength(5);
    expect(skeletal.every((row) => row.state === 'skeletal')).toBe(true);

    const filling = studioArtifactStreamRows({
      phase: 'filling',
      stageId: 'transcript',
    });
    expect(filling.map((row) => row.state)).toEqual([
      'done',
      'done',
      'active',
      'pending',
      'pending',
    ]);
    expect(filling[2]?.label).toMatch(/transcript/i);
  });

  it('builds settled preview from auJzb1D-fag fixture formation only', () => {
    const citation = loadSamplePack();
    expect(citation.videoId).toBe('auJzb1D-fag');
    const formation = studioPackFormation(citation);
    const preview = studioArtifactStreamPreview(formation);

    expect(preview).not.toBeNull();
    expect(preview?.architectureSummary).toMatch(/Multimodal ingestion/i);
    expect(preview?.architectureStages.some((s) => s.name === 'Multimodal Ingestion')).toBe(
      true,
    );
    expect(preview?.artifacts.some((a) => a.path_hint.includes('SpatialDetector'))).toBe(true);
    expect(preview?.tools.some((t) => t.name === 'Google AI Studio')).toBe(true);
  });

  it('returns null preview when formation has no real pack content (no mocks)', () => {
    expect(studioArtifactStreamPreview(undefined)).toBeNull();
    expect(
      studioArtifactStreamPreview({
        architecture: null,
        artifacts: [],
        tools: [],
      }),
    ).toBeNull();
  });

  it('builds the full model from real busy + fixture pack inputs', () => {
    const citation = loadSamplePack();
    const formation = studioPackFormation(citation);

    const extracting = studioArtifactStreamModel({
      busy: true,
      elapsedSeconds: 12,
      progress: 8,
      formation,
    });
    expect(extracting.phase).toBe('filling');
    expect(extracting.rows.some((row) => row.state === 'active')).toBe(true);

    const settled = studioArtifactStreamModel({
      busy: false,
      hasPack: true,
      hasTranscript: true,
      formation,
    });
    expect(settled.phase).toBe('settled');
    expect(settled.preview?.tools.length).toBeGreaterThan(0);
    expect(settled.rows.every((row) => row.state === 'done')).toBe(true);
  });
});

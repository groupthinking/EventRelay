/** @vitest-environment jsdom */
import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioArtifactStream from '@/components/studio/StudioArtifactStream';
import {
  studioArtifactStreamModel,
  studioArtifactStreamRows,
} from '@/lib/studio-artifact-stream';
import { loadSamplePack } from '@/lib/sample-pack';
import { studioPackFormation } from '@/lib/studio-pipeline-status';

describe('StudioArtifactStream', () => {
  beforeEach(() => {
    vi.stubGlobal('React', React);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders skeletal extract rows without inventing pack preview', () => {
    const rows = studioArtifactStreamRows({ phase: 'skeletal', stageId: 'pack' });
    render(
      <StudioArtifactStream
        phase="skeletal"
        rows={rows}
        videoId="auJzb1D-fag"
        statusText="Working · Pack identity"
      />,
    );

    const root = screen.getByTestId('studio-artifact-stream');
    expect(root.getAttribute('data-phase')).toBe('skeletal');
    expect(root.getAttribute('data-video-id')).toBe('auJzb1D-fag');
    expect(screen.queryByTestId('studio-artifact-stream-preview')).toBeNull();
    expect(screen.getAllByRole('listitem')).toHaveLength(5);
    expect(screen.getAllByRole('listitem').every((li) => li.getAttribute('data-state') === 'skeletal')).toBe(
      true,
    );
  });

  it('fills active extract rows from real transcript stage', () => {
    const rows = studioArtifactStreamRows({ phase: 'filling', stageId: 'events' });
    render(<StudioArtifactStream phase="filling" rows={rows} videoId="auJzb1D-fag" />);

    expect(screen.getByText('Extracting events & tasks')).toBeTruthy();
    const active = screen
      .getAllByRole('listitem')
      .find((li) => li.getAttribute('data-step') === 'events');
    expect(active?.getAttribute('data-state')).toBe('active');
  });

  it('settles into real architecture / artifacts / stack from auJzb1D-fag', () => {
    const citation = loadSamplePack();
    expect(citation.videoId).toBe('auJzb1D-fag');
    const formation = studioPackFormation(citation);
    const model = studioArtifactStreamModel({
      busy: false,
      hasPack: true,
      hasTranscript: true,
      formation,
    });

    render(
      <StudioArtifactStream
        phase={model.phase}
        rows={model.rows}
        preview={model.preview}
        videoId={citation.videoId}
      />,
    );

    expect(screen.getByTestId('studio-artifact-stream').getAttribute('data-phase')).toBe('settled');
    expect(screen.getByText('Video Pack ready')).toBeTruthy();
    expect(screen.getByTestId('studio-artifact-stream-preview')).toBeTruthy();
    expect(screen.getByTestId('studio-artifact-stream-architecture').textContent).toMatch(
      /Multimodal ingestion/i,
    );
    expect(screen.getByTestId('studio-artifact-stream-artifacts').textContent).toMatch(
      /SpatialDetector/,
    );
    expect(screen.getByTestId('studio-artifact-stream-tools').textContent).toMatch(
      /Google AI Studio/,
    );
  });

  it('renders nothing when phase is hidden', () => {
    const { container } = render(
      <StudioArtifactStream phase="hidden" rows={[]} videoId="auJzb1D-fag" />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders Architecture stages when optional summary is absent', () => {
    render(
      <StudioArtifactStream
        phase="settled"
        rows={studioArtifactStreamRows({ phase: 'settled', stageId: 'ready' })}
        preview={{
          architectureSummary: null,
          architectureStages: [
            { id: 'ingest', name: 'Multimodal Ingestion' },
            { id: 'output', name: 'Structured Generation' },
          ],
          artifacts: [],
          tools: [],
        }}
        videoId="auJzb1D-fag"
      />,
    );

    const architecture = screen.getByTestId('studio-artifact-stream-architecture');
    expect(architecture.textContent).toMatch(/Multimodal Ingestion/);
    expect(architecture.textContent).toMatch(/Structured Generation/);
    expect(architecture.querySelector('.studio-artifact-stream__preview-body')).toBeNull();
  });
});

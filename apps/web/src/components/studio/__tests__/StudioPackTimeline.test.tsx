// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioPackTimeline from '@/components/studio/StudioPackTimeline';
import { loadSamplePack } from '@/lib/sample-pack';
import type { EmittedVideoPack } from '@/lib/emit-video-pack';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.stubGlobal('React', React);
});

describe('StudioPackTimeline', () => {
  it('renders horizontal chapter markers from the fixture pack and seeks on click', () => {
    const onSeek = vi.fn();
    const { pack } = loadSamplePack();
    render(
      <StudioPackTimeline pack={pack} canSeek onSeek={onSeek} currentTime={14} playerDuration={481} />,
    );

    expect(screen.getByTestId('studio-pack-timeline')).toBeTruthy();
    expect(screen.getByTestId('studio-pack-timeline-track')).toBeTruthy();
    expect(screen.getByTestId('studio-timeline-chapter-0')).toBeTruthy();
    expect(screen.getByTestId('studio-timeline-chapter-1')).toBeTruthy();
    expect(screen.getByTestId('studio-timeline-keyframe-0')).toBeTruthy();
    expect(screen.getByTestId('studio-pack-timeline-playhead')).toBeTruthy();

    fireEvent.click(screen.getByTestId('studio-timeline-chapter-1'));
    expect(onSeek).toHaveBeenCalledWith(27);
    expect(screen.getByTestId('studio-timeline-chapter-1').getAttribute('data-selected')).toBe(
      'true',
    );
  });

  it('keeps markers visible but does not seek when selection-scoped gate fails', () => {
    const onSeek = vi.fn();
    const { pack } = loadSamplePack();
    render(<StudioPackTimeline pack={pack} canSeek={false} onSeek={onSeek} />);

    const chapter = screen.getByTestId('studio-timeline-chapter-0') as HTMLButtonElement;
    expect(chapter.disabled).toBe(true);
    fireEvent.click(chapter);
    expect(onSeek).not.toHaveBeenCalled();
    expect(screen.getByTestId('studio-pack-timeline').getAttribute('data-can-seek')).toBe('false');
  });

  it('keeps the pack span and hides the playhead when the player clock is withheld', () => {
    const { pack } = loadSamplePack();
    const packSpan = Math.max(...(pack.chapters ?? []).map((c) => c.end));
    render(<StudioPackTimeline pack={pack} canSeek={false} />);

    expect(screen.queryByTestId('studio-pack-timeline-playhead')).toBeNull();
    const spanText = screen.getByTestId('studio-pack-timeline-span').textContent ?? '';
    expect(spanText).toMatch(/^8:0[01]$/);
    expect(packSpan).toBeGreaterThanOrEqual(481);
  });

  it('renders nothing when the pack has no time surfaces (no mock filler)', () => {
    const empty: EmittedVideoPack = {
      version: 'v0',
      id: 'vp:v0:auJzb1D-fag',
      video_id: 'auJzb1D-fag',
      source_url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      provenance: { source_hash: 'a'.repeat(64) },
    };
    const { container } = render(<StudioPackTimeline pack={empty} canSeek onSeek={vi.fn()} />);
    expect(container.firstChild).toBeNull();
    expect(screen.queryByTestId('studio-pack-timeline')).toBeNull();
  });
});

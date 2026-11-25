// @vitest-environment jsdom
import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LiveStudioWorkspace from '@/components/studio/live/LiveStudioWorkspace';
import { loadSamplePack, sampleReplaySteps } from '@/lib/sample-pack';
import type { Video } from '@/store/dashboard-store';

const citation = loadSamplePack();
const steps = sampleReplaySteps(citation);

function videoAt(stepIndex: number, status: Video['status'] = 'processing'): Video {
  const step = steps[stepIndex];
  return {
    id: 'sample-row',
    title: 'Sample',
    url: citation.sourceUrl,
    status,
    progress: step.progress,
    videoPack: { ...citation, pack: step.pack },
  };
}

function workspace(video: Video, live: boolean) {
  return (
    <LiveStudioWorkspace
      header={<span>header</span>}
      player={<div>player</div>}
      chat={<div>chat</div>}
      deliverables={<div>deliverables</div>}
      video={video}
      live={live}
      statusText="status"
      canSeek
      onSeek={vi.fn()}
      onSaveTaskEdits={vi.fn()}
    />
  );
}

/** Step the clock so each reveal tick re-renders before the next timer is scheduled. */
function advance(ms: number) {
  for (let elapsed = 0; elapsed < ms; elapsed += 20) {
    act(() => {
      vi.advanceTimersByTime(20);
    });
  }
}

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.useFakeTimers();
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ available: false }), { status: 200 })));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('Live Studio streaming render', () => {
  it('shows skeleton rows for sections that have not arrived yet', () => {
    render(workspace(videoAt(0), true));
    expect(screen.getByTestId('live-transcript-skeleton')).toBeTruthy();
    expect(screen.getByTestId('live-chapters-skeleton')).toBeTruthy();
    expect(screen.getByTestId('live-tasks-skeleton')).toBeTruthy();
    expect(screen.queryByTestId('live-transcript-line-0')).toBeNull();
    const stages = screen.getByTestId('live-stages');
    expect(stages.querySelector('[data-stage="pack"]')?.getAttribute('data-state')).toBe('done');
    expect(stages.querySelector('[data-stage="transcript"]')?.getAttribute('data-state')).toBe('active');
  });

  it('fills transcript rows in place a few at a time instead of all at once', () => {
    const { rerender } = render(workspace(videoAt(0), true));
    const firstChunk = steps.findIndex((step) => step.stage === 'transcript');
    rerender(workspace(videoAt(firstChunk), true));
    const arrived = steps[firstChunk]?.pack.transcript?.segments?.length ?? 0;
    expect(arrived).toBeGreaterThan(4);

    advance(40);
    const early = screen.queryAllByTestId(/^live-transcript-line-/).length;
    expect(early).toBeGreaterThan(0);
    expect(early).toBeLessThan(arrived);
    expect(screen.getByTestId('live-transcript-skeleton')).toBeTruthy();

    advance(2_000);
    expect(screen.queryAllByTestId(/^live-transcript-line-/)).toHaveLength(arrived);
    expect(screen.getByTestId('live-transcript').textContent).toContain('streaming');
  });

  it('renders chapters, keyframes, tasks and checks once the pack completes, with no skeletons left', () => {
    const { rerender } = render(workspace(videoAt(0), true));
    rerender(workspace(videoAt(steps.length - 1, 'complete'), false));
    advance(5_000);
    expect(screen.queryAllByTestId(/^live-transcript-line-/)).toHaveLength(41);
    expect(screen.queryAllByTestId(/^live-chapter-\d+$/)).toHaveLength(9);
    expect(screen.queryAllByTestId(/^live-keyframe-\d+$/)).toHaveLength(12);
    expect(screen.getByTestId('live-task-G-REQ-01')).toBeTruthy();
    expect(screen.getByTestId('live-task-ACT-03')).toBeTruthy();
    expect(screen.queryByTestId('live-transcript-skeleton')).toBeNull();
    expect(screen.queryByTestId('live-tasks-skeleton')).toBeNull();
    const stages = screen.getByTestId('live-stages');
    expect([...stages.querySelectorAll('[data-state]')].every((node) => node.getAttribute('data-state') === 'done')).toBe(true);
    const eventsStage = stages.querySelector('[data-stage="events"]');
    expect(eventsStage?.textContent).toMatch(/Events\s*0/);
    expect(eventsStage?.textContent).not.toMatch(/Events\s*3/);
    expect(citation.pack.visual_context?.visual_elements.length).toBeGreaterThan(0);
    expect(citation.pack).not.toHaveProperty('events');
  });

  it('shows a transcript ETA while lines are still arriving and a retry when the fetch fails', () => {
    const onRetry = vi.fn();
    const { rerender } = render(
      <LiveStudioWorkspace
        header={<span>header</span>}
        player={<div>player</div>}
        chat={<div>chat</div>}
        deliverables={<div>deliverables</div>}
        video={videoAt(0)}
        live
        statusText="Working"
        transcriptEta="About 20s left (typical ~45s)"
        onRetryTranscript={onRetry}
        canSeek
        onSeek={vi.fn()}
        onSaveTaskEdits={vi.fn()}
      />,
    );
    expect(screen.getByTestId('live-transcript-eta').textContent).toMatch(/20s left/i);
    expect(screen.getByTestId('live-transcript').textContent).not.toMatch(/Paste a YouTube link/);

    const failed = videoAt(0, 'failed');
    failed.failure = {
      stage: 'analysis',
      message: 'Transcript fetch failed for pBsT6v-ciO8.',
      retryable: true,
      failedAt: '2026-11-22T00:00:00.000Z',
    };
    rerender(
      <LiveStudioWorkspace
        header={<span>header</span>}
        player={<div>player</div>}
        chat={<div>chat</div>}
        deliverables={<div>deliverables</div>}
        video={failed}
        live={false}
        statusText="Transcript fetch failed for pBsT6v-ciO8."
        onRetryTranscript={onRetry}
        canSeek
        onSeek={vi.fn()}
        onSaveTaskEdits={vi.fn()}
      />,
    );
    const transcript = screen.getByTestId('live-transcript');
    expect(transcript.textContent).toMatch(/Transcript fetch failed for pBsT6v-ciO8/);
    expect(transcript.textContent).not.toMatch(/Paste a YouTube link/);
    fireEvent.click(screen.getByTestId('live-transcript-retry'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('labels the sample as replayed cached data', () => {
    render(workspace({ ...videoAt(steps.length - 1, 'complete'), sample: { label: 'Cached sample · replayed in pipeline order', capturedAt: '2026-10-16T07:19:03.888Z' } }, false));
    expect(screen.getByTestId('live-sample-label').textContent).toMatch(/Cached sample/);
  });
});

import { describe, expect, it, vi } from 'vitest';
import {
  SAMPLE_VIDEO_ID,
  loadSamplePack,
  replaySamplePack,
  sampleCompletionPatch,
  sampleReplaySteps,
} from '@/lib/sample-pack';
import { inspectGroundedSpec } from '@/lib/grounded-build-spec';
import type { Video } from '@/store/dashboard-store';

describe('sample pack fixture', () => {
  it('verifies as a hashed v0 Video Pack for the fixture video', () => {
    const citation = loadSamplePack();
    expect(citation.videoId).toBe(SAMPLE_VIDEO_ID);
    expect(citation.sourceHash).toMatch(/^[0-9a-f]{64}$/);
    expect(citation.pack.transcript?.segments?.length).toBe(41);
    expect(citation.pack.chapters?.length).toBe(9);
    expect(citation.pack.keyframes?.length).toBe(12);
  });

  it('serves keyframe stills from /public so the sample works offline', () => {
    const { pack } = loadSamplePack();
    for (const frame of pack.keyframes ?? []) {
      expect(frame.image_path).toMatch(new RegExp(`^/sample-pack/${SAMPLE_VIDEO_ID}/\\d+\\.jpg$`));
    }
  });

  it('carries a grounded spec that inspects cleanly', () => {
    const inspection = inspectGroundedSpec(loadSamplePack().pack);
    expect(inspection.status).toBe('available');
  });
});

describe('sampleReplaySteps', () => {
  const citation = loadSamplePack();
  const steps = sampleReplaySteps(citation);

  it('starts with identity only and ends with the exact verified pack', () => {
    expect(steps[0].stage).toBe('identity');
    expect(steps[0].pack.transcript).toBeUndefined();
    expect(steps[0].pack.chapters).toBeUndefined();
    expect(steps.at(-1)?.pack).toBe(citation.pack);
  });

  it('follows pipeline order with monotonically increasing progress', () => {
    const order = [...new Set(steps.map((step) => step.stage))];
    expect(order).toEqual(['identity', 'transcript', 'chapters', 'keyframes', 'events', 'formation', 'spec', 'actions']);
    for (let i = 1; i < steps.length; i += 1) {
      expect(steps[i].progress).toBeGreaterThan(steps[i - 1].progress);
    }
  });

  it('streams the transcript in cumulative chunks without inventing segments', () => {
    const transcriptSteps = steps.filter((step) => step.stage === 'transcript');
    expect(transcriptSteps.length).toBeGreaterThan(1);
    const counts = transcriptSteps.map((step) => step.pack.transcript?.segments?.length ?? 0);
    expect(counts).toEqual([...counts].sort((a, b) => a - b));
    expect(counts.at(-1)).toBe(41);
    const first = transcriptSteps[0].pack.transcript?.segments ?? [];
    expect(first).toEqual(citation.pack.transcript?.segments?.slice(0, first.length));
  });

  it('only adds fields, never removes them', () => {
    for (let i = 1; i < steps.length; i += 1) {
      for (const key of Object.keys(steps[i - 1].pack)) {
        expect(steps[i].pack).toHaveProperty(key);
      }
    }
  });
});

describe('replaySamplePack', () => {
  it('applies every stage as processing, then the completion patch', async () => {
    vi.useFakeTimers();
    try {
      const citation = loadSamplePack();
      const patches: Array<Partial<Video>> = [];
      const done = replaySamplePack({ recordId: 'row-1', citation, apply: (patch) => patches.push(patch), stepDelayMs: 10 });
      await vi.runAllTimersAsync();
      await done;
      const steps = sampleReplaySteps(citation);
      expect(patches).toHaveLength(steps.length + 1);
      expect(patches.slice(0, -1).every((patch) => patch.status === 'processing')).toBe(true);
      expect(patches.at(-1)).toMatchObject({ status: 'complete', progress: 100, videoPack: citation });
    } finally {
      vi.useRealTimers();
    }
  });

  it('stops applying patches once aborted', async () => {
    vi.useFakeTimers();
    try {
      const controller = new AbortController();
      const patches: Array<Partial<Video>> = [];
      const done = replaySamplePack({
        recordId: 'row-1',
        citation: loadSamplePack(),
        apply: (patch) => {
          patches.push(patch);
          if (patches.length === 2) controller.abort();
        },
        stepDelayMs: 10,
        signal: controller.signal,
      });
      const settled = done.catch((error: unknown) => error);
      await vi.runAllTimersAsync();
      await settled;
      expect(patches).toHaveLength(2);
      expect(patches.some((patch) => patch.status === 'complete')).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('sampleCompletionPatch', () => {
  it('derives title, events and insights from the pack itself', () => {
    const citation = loadSamplePack();
    const patch = sampleCompletionPatch(citation, 'row-9');
    expect(patch.title).toBe(`Sample · ${citation.pack.chapters?.[0]?.topic}`);
    expect(patch.events ?? []).toEqual([]);
    expect(citation.pack.visual_context?.visual_elements.length).toBeGreaterThan(0);
    expect(patch.insights?.actions.map((action) => (typeof action === 'string' ? action : action.title))).toEqual(
      (citation.pack.action_items ?? []).map((item) => item.title),
    );
  });
});

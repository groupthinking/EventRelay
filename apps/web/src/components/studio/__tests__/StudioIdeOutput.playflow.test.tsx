// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioIdeOutput from '@/components/studio/StudioIdeOutput';
import type { Video } from '@/store/dashboard-types';
import { reviewPackFixture } from '@/test/grounded-spec-fixture';

const baseVideo: Video = {
  id: 'row-output',
  title: 'Playflow output',
  url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
  status: 'complete',
  progress: 100,
  transcript: 'Enough transcript text for analysis ready state in Studio tests.',
};

beforeEach(() => {
  vi.stubGlobal('React', React);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('StudioIdeOutput playflow', () => {
  it('renders 4 single-row plain-English tabs and defaults to Tasks & Tools', () => {
    const pack = reviewPackFixture();
    pack.chapters = [
      { start: 0, end: 30, topic: 'Camera setup', key_points: ['Mount overhead camera'] },
    ];
    pack.stack.tools = [{ name: 'Next.js', kind: 'framework', evidence: 'Mentioned at 0:15' }];
    render(
      <StudioIdeOutput
        video={{
          ...baseVideo,
          insights: {
            summary: 'Build summary',
            actions: [],
            sentiment: 'neutral',
            topics: ['Robotics', 'Telemetry'],
          },
          videoPack: {
            packId: pack.id,
            videoId: pack.video_id,
            sourceUrl: pack.source_url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack,
          },
        }}
      />,
    );

    const tablist = screen.getByTestId('studio-ide-output-tablist');
    expect(tablist.className).toContain('flex-nowrap');
    expect(tablist.className).toContain('overflow-x-auto');

    const tabs = screen.getAllByRole('tab');
    expect(tabs.map((tab) => tab.textContent)).toEqual([
      'Preview',
      'Tasks & Tools',
      'Code & Spec',
      'Transcript',
    ]);
    expect(screen.getByTestId('studio-download-md')).toBeTruthy();
    expect(screen.queryByRole('tab', { name: 'Lingo' })).toBeNull();
    expect(screen.queryByRole('tab', { name: 'Signals' })).toBeNull();
    expect(screen.queryByRole('tab', { name: 'Intent' })).toBeNull();

    // Default active tab surfaces Tasks & Tools immediately without requiring extra clicks.
    expect(screen.getByTestId('studio-ide-output-tab-tasks').getAttribute('aria-selected')).toBe('true');
    expect(screen.getByTestId('studio-pack-chapters').textContent).toContain('Camera setup');
    expect(screen.getByTestId('studio-ide-output-tools').textContent).toContain('Next.js');
    expect(screen.getByTestId('studio-proposed-tool-card').textContent).toMatch(/Proposed/);
    expect(screen.getByTestId('studio-proposed-tool-card').textContent).toMatch(/not run/i);
    expect(screen.getByTestId('studio-ide-output-topics').textContent).toContain('Robotics');

    // Keyboard tab navigation across the 4 tabs.
    const tasksTab = screen.getByTestId('studio-ide-output-tab-tasks');
    fireEvent.keyDown(tasksTab, { key: 'ArrowRight' });
    expect(screen.getByTestId('studio-ide-output-tab-code').getAttribute('aria-selected')).toBe('true');
    fireEvent.keyDown(screen.getByTestId('studio-ide-output-tab-code'), { key: 'Home' });
    expect(screen.getByTestId('studio-ide-output-tab-preview').getAttribute('aria-selected')).toBe('true');
  });

  it('renders the Webflow Desktop | Mobile preview frame directly when a pack exists without duplicate Build live clutter', () => {
    const pack = reviewPackFixture();
    render(
      <StudioIdeOutput
        video={{
          ...baseVideo,
          videoPack: {
            packId: pack.id,
            videoId: pack.video_id,
            sourceUrl: pack.source_url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack,
          },
        }}
        onBuildLive={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-preview'));

    const iframe = screen.getByTestId('studio-ide-preview-iframe') as HTMLIFrameElement;
    expect(iframe.getAttribute('src')).toBe('/d/auJzb1D-fag');
    const openLink = screen.getByTestId('studio-ide-preview-open-tab') as HTMLAnchorElement;
    expect(openLink.textContent).toMatch(/Open full preview/);
    expect(openLink.getAttribute('href')).toBe('/d/auJzb1D-fag');
    expect(screen.queryByTestId('studio-ide-preview-build-cta')).toBeNull();

    const frame = screen.getByTestId('studio-ide-preview-frame');
    expect(frame.dataset.viewport).toBe('desktop');
    expect(screen.getByTestId('studio-ide-preview-mode-desktop').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('studio-ide-preview-mode-mobile').getAttribute('aria-pressed')).toBe('false');

    fireEvent.click(screen.getByTestId('studio-ide-preview-mode-mobile'));
    expect(frame.dataset.viewport).toBe('mobile');
    expect(frame.style.width).toBe('390px');
    expect(screen.getByTestId('studio-ide-preview-mode-mobile').getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(screen.getByTestId('studio-ide-preview-mode-desktop'));
    expect(frame.dataset.viewport).toBe('desktop');
    expect(frame.style.width).toBe('');
  });

  it('shows a single empty-state Generate preview trigger when no pack is present and focuses Preview when ready', () => {
    const onBuildLive = vi.fn();
    const view = render(
      <StudioIdeOutput
        video={baseVideo}
        previewVideoId="auJzb1D-fag"
        previewReady={false}
        onBuildLive={onBuildLive}
        activeSection="preview"
      />,
    );

    const cta = screen.getByTestId('studio-ide-preview-build-cta');
    fireEvent.click(cta);
    expect(onBuildLive).toHaveBeenCalledTimes(1);

    view.rerender(
      <StudioIdeOutput
        video={baseVideo}
        previewVideoId="auJzb1D-fag"
        previewReady
        onBuildLive={onBuildLive}
      />,
    );
    expect(screen.getByTestId('studio-ide-output-tab-preview').getAttribute('aria-selected')).toBe('true');
    expect(screen.getByTestId('studio-ide-preview-iframe').getAttribute('src')).toBe('/d/auJzb1D-fag');
  });

  it('renders pack-named stack checks as skip/unknown rows inside Code & Spec without claiming a hold', () => {
    render(
      <StudioIdeOutput
        video={baseVideo}
        stackChecks={[
          {
            id: 'chk_tool_seadance',
            title: 'Use SeaDance 2.5 as named in the video',
            status: 'unknown',
            statusLabel: 'Can be skipped — not a production hold. UVAI cannot run this check.',
            holdsShip: false,
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-code'));
    const row = screen.getByTestId('studio-stack-check-chk_tool_seadance');
    expect(row.textContent).toMatch(/SeaDance 2\.5/);
    expect(row.textContent).toMatch(/can be skipped/i);
    expect(row.textContent).toMatch(/not a production hold/i);
    expect(row.textContent).toMatch(/cannot run this check/i);
    expect(row.textContent).not.toMatch(/\bpassed\b/i);
  });

  it('does not render INSIGHT cards when the pack has no events[]', () => {
    const pack = reviewPackFixture();
    pack.architecture = {
      summary: 'Five-step pipeline',
      stages: [{ id: 'extract', name: 'Extract' }],
    };
    pack.artifacts = [{ path_hint: 'src/pipeline.ts', purpose: 'Run the pack', interface: 'extract()' }];
    render(
      <StudioIdeOutput
        video={{
          ...baseVideo,
          events: [
            {
              id: 'evt_1',
              type: 'insight',
              title: 'Five-Step AI Video Retainer Pipeline',
              description: 'Workflow step, not a pack event.',
            },
            { id: 'evt_2', type: 'insight', title: 'Cluey two-engineer architecture' },
            { id: 'evt_3', type: 'insight', title: 'creator affiliate network' },
            { id: 'evt_4', type: 'insight', title: 'Fable/safety' },
          ],
          videoPack: {
            packId: pack.id,
            videoId: pack.video_id,
            sourceUrl: pack.source_url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack,
          },
        }}
        eventsEmptyMessage="This pack has no extracted events. Architecture, artifacts, and stack from the video are below — export them from this page."
      />,
    );
    const events = screen.getByTestId('studio-ide-output-events');
    expect(events.textContent).toMatch(/no extracted events/i);
    expect(events.textContent).not.toMatch(/INSIGHT/i);
    expect(events.textContent).not.toContain('Five-Step AI Video Retainer Pipeline');
    expect(events.textContent).not.toContain('Cluey two-engineer architecture');
  });

  it('uses the honest Events empty copy and hosts the pack workbench inside Tasks & Tools', () => {
    render(
      <StudioIdeOutput
        video={baseVideo}
        eventsEmptyMessage="This pack has no extracted events. Architecture and artifacts stay on this page."
        packWorkbench={<div data-testid="studio-pack-workbench">Pack workbench</div>}
      />,
    );
    const events = screen.getByTestId('studio-ide-output-events');
    expect(events.textContent).toMatch(/no extracted events/i);
    expect(events.textContent).not.toMatch(/INSIGHT/i);
    expect(screen.getByTestId('studio-pack-workbench')).toBeTruthy();
  });

  it('shows a transcript ETA while the fetch is in progress and a retry when it fails', () => {
    const onRetry = vi.fn();
    const view = render(
      <StudioIdeOutput
        video={{ ...baseVideo, status: 'processing', transcript: '' }}
        transcriptEta="About 33s left (typical ~45s)"
        activeSection="transcript"
      />,
    );
    expect(screen.getByTestId('studio-transcript-eta').textContent).toMatch(/33s left/i);
    expect(screen.queryByText('Nothing yet.')).toBeNull();

    view.rerender(
      <StudioIdeOutput
        video={{
          ...baseVideo,
          status: 'failed',
          transcript: '',
          failure: {
            stage: 'analysis',
            message: 'Gemini 3.8 Flash returned no extracted spec content.',
            retryable: true,
            failedAt: '2026-11-22T00:00:00.000Z',
          },
        }}
        showTranscriptRetry
        onRetryTranscript={onRetry}
        activeSection="transcript"
      />,
    );
    expect(screen.getByTestId('studio-transcript-body').textContent).toMatch(
      /Gemini 3\.8 Flash returned no extracted spec content/,
    );
    fireEvent.click(screen.getByTestId('studio-transcript-pane-retry'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders pBsT6v-ciO8 named tools as proposed cards instead of a dead name list', () => {
    const pack = reviewPackFixture();
    pack.video_id = 'pBsT6v-ciO8';
    pack.source_url = 'https://www.youtube.com/watch?v=pBsT6v-ciO8';
    pack.stack.tools = [
      { name: 'SeaDance 2.5', evidence: 'Named on screen.' },
      { name: 'Claude Fable 5' },
      { name: 'Character.ai' },
      { name: 'Cluely Desktop' },
    ];
    render(
      <StudioIdeOutput
        video={{
          ...baseVideo,
          url: 'https://www.youtube.com/watch?v=pBsT6v-ciO8',
          videoPack: {
            packId: pack.id,
            videoId: 'pBsT6v-ciO8',
            sourceUrl: pack.source_url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack,
          },
        }}
      />,
    );
    const cards = screen.getAllByTestId('studio-proposed-tool-card');
    expect(cards).toHaveLength(4);
    expect(cards.map((card) => card.textContent).join('\n')).toMatch(/SeaDance 2\.5/);
    expect(cards.map((card) => card.textContent).join('\n')).toMatch(/Cluely Desktop/);
    for (const card of cards) {
      expect(card.textContent).toMatch(/Proposed/);
      expect(card.textContent).toMatch(/not run/i);
      expect(card.textContent).not.toMatch(/\b(passed|done|executed)\b/i);
    }
  });

  it('renders review_action results and pending tool proposals inside Tasks & Tools', () => {
    render(
      <StudioIdeOutput
        video={baseVideo}
        reviewActions={[
          { tool: 'review_action', status: 'proposed', result: 'Review evidence' },
          {
            tool: 'create_workflow_task',
            input: { title: 'Draft a task from the video' },
            status: 'pending',
            result: 'Draft a task from the video',
          },
        ]}
      />,
    );
    const cards = screen.getAllByTestId('studio-review-action-card');
    expect(cards).toHaveLength(2);
    expect(cards[0]?.textContent).toMatch(/review this result/i);
    expect(cards[0]?.textContent).toMatch(/needs review/i);
    expect(cards[0]?.textContent).toMatch(/Review evidence/);

    const buttons = screen.getAllByTestId('studio-review-act-button');
    fireEvent.click(buttons[0]!);
    expect(screen.getByTestId('studio-proposal-detail').textContent).toMatch(/No tool has been executed/i);

    fireEvent.click(buttons[1]!);
    expect(screen.getByTestId('studio-proposal-detail').textContent).toMatch(/create_workflow_task/);
    expect(screen.getByTestId('studio-proposal-detail').textContent).toMatch(/"title": "Draft a task from the video"/);
  });

  it('renders extracted code snippets and spec review inside Code & Spec', () => {
    const pack = reviewPackFixture();
    pack.code_snippets = [
      {
        path_hint: 'robotics/cornhole_pipeline.py',
        lang: 'python',
        content: 'def throw_bag(obs: np.ndarray) -> np.ndarray:\n    return obs[..., :3]',
      },
    ];
    render(
      <StudioIdeOutput
        video={{
          ...baseVideo,
          videoPack: {
            packId: pack.id,
            videoId: pack.video_id,
            sourceUrl: pack.source_url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack,
          },
        }}
        specReview={<div data-testid="custom-spec-review">Spec review panel</div>}
      />,
    );
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-code'));
    const snippets = screen.getByTestId('studio-pack-code-snippets');
    expect(snippets.textContent).toContain('robotics/cornhole_pipeline.py');
    expect(snippets.textContent).toContain('def throw_bag');
    expect(screen.getByTestId('custom-spec-review')).toBeTruthy();
  });

  it('supports click-to-seek on chapters, events, transcript segments, and keyframes', () => {
    const onSeek = vi.fn();
    const pack = reviewPackFixture();
    pack.chapters = [
      { start: 12, end: 40, topic: 'Camera setup and calibration', key_points: ['Mount overhead camera'] },
      { start: 40, end: 75, topic: 'Stance trajectory estimation', key_points: ['Track release angle'] },
    ];
    pack.transcript = {
      language: 'en',
      full_text: 'Mount overhead camera then track release angle.',
      segments: [
        { idx: 0, start_s: 12, end_s: 40, text: 'Mount overhead camera.' },
        { idx: 1, start_s: 40, end_s: 75, text: 'Track release angle.' },
      ],
    };
    pack.keyframes = [{ t_s: 42, desc: 'Release frame' }];
    Object.assign(pack, {
      events: [
        {
          id: 'evt-1',
          type: 'action',
          title: 'Calibrate camera',
          description: 'Run checkerboard capture',
          timestamp: 25,
        },
      ],
    });

    render(
      <StudioIdeOutput
        onSeek={onSeek}
        video={{
          ...baseVideo,
          events: [
            {
              id: 'ignored-insight',
              type: 'insight',
              title: 'Five-Step AI Video Retainer Pipeline',
              timestamp: '0:01',
            },
          ],
          videoPack: {
            packId: pack.id,
            videoId: pack.video_id,
            sourceUrl: pack.source_url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack,
          },
        }}
      />,
    );

    const chapters = screen.getByTestId('studio-pack-chapters');
    expect(chapters.textContent).toContain('01');
    expect(chapters.textContent).toContain('Camera setup and calibration');
    fireEvent.click(screen.getByTestId('studio-chapter-seek-1'));
    expect(onSeek).toHaveBeenCalledWith(40);

    fireEvent.click(screen.getByTestId('studio-event-seek-evt-1'));
    expect(onSeek).toHaveBeenCalledWith(25);

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-transcript'));
    fireEvent.click(screen.getByTestId('studio-transcript-seek-0'));
    expect(onSeek).toHaveBeenCalledWith(12);

    expect(screen.getByTestId('studio-ide-output-keyframes').textContent).toContain('Release frame');
    fireEvent.click(screen.getByTestId('studio-keyframe-seek-0'));
    expect(onSeek).toHaveBeenCalledWith(42);
  });

  it('keeps Tools/Files/Code after Build live when focusPreviewSignal stays truthy (Cut 4)', () => {
    // After verification, previewFocusEpoch stays nonzero. Controlled section
    // changes must not re-apply the stale focus signal and force Canvas/Preview.
    type Section = 'preview' | 'tasks' | 'code' | 'transcript';
    let section: Section = 'tasks';
    const onSectionChange = vi.fn((next: Section) => {
      section = next;
    });

    const propsFor = (active: Section, signal: number) => ({
      video: baseVideo,
      previewVideoId: 'auJzb1D-fag',
      previewReady: true as const,
      focusPreviewSignal: signal,
      activeSection: active,
      onSectionChange,
    });

    const view = render(<StudioIdeOutput {...propsFor(section, 1)} />);
    expect(onSectionChange).toHaveBeenCalledWith('preview');
    section = 'preview';
    view.rerender(<StudioIdeOutput {...propsFor(section, 1)} />);
    onSectionChange.mockClear();

    for (const next of ['tasks', 'code', 'transcript'] as const) {
      section = next;
      view.rerender(<StudioIdeOutput {...propsFor(section, 1)} />);
      expect(onSectionChange).not.toHaveBeenCalledWith('preview');
      expect(screen.getByTestId(`studio-ide-output-tab-${next}`).getAttribute('aria-selected')).toBe(
        'true',
      );
    }

    // A new focus signal still focuses Preview once.
    section = 'tasks';
    view.rerender(<StudioIdeOutput {...propsFor(section, 2)} />);
    expect(onSectionChange).toHaveBeenCalledWith('preview');
  });
});

// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/studio',
}));
vi.mock('@/components/Nav', () => ({ default: () => null }));
vi.mock('@/app/studio/actions', () => ({ openGitHubPrsForApprovedSpecs: vi.fn() }));
vi.mock('@/lib/use-youtube-player', () => ({
  useYouTubePlayer: () => ({
    containerRef: { current: null },
    ready: true,
    failed: false,
    seekTo: vi.fn(),
  }),
}));

const dogfoodVideo: Video = {
  id: 'pBsT6v-ciO8',
  title: 'AI gold rushes',
  url: 'https://www.youtube.com/watch?v=pBsT6v-ciO8',
  status: 'complete',
  progress: 100,
  transcript:
    'What do you think are the three mini gold rushes happening inside AI right now that no one is talking about? SeaDance 2.5 and Cluely Desktop.',
  events: [],
};

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => undefined);
  useDashboardStore.setState({ videos: [], selectedVideoId: null });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('OneLoopStudio playflow CTAs after the IDE rebuild', () => {
  it('shows Retry transcript when analysis failed and does not leave a silent wait', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    useDashboardStore.setState({
      videos: [
        {
          ...dogfoodVideo,
          status: 'failed',
          transcript: '',
          failure: {
            stage: 'analysis',
            message: 'Captions were not available.',
            retryable: true,
            failedAt: '2026-10-17T00:00:00.000Z',
          },
          videoPack: {
            packId: pack.id,
            videoId: 'pBsT6v-ciO8',
            sourceUrl: dogfoodVideo.url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack: { ...pack, video_id: 'pBsT6v-ciO8', source_url: dogfoodVideo.url },
          },
        },
      ],
      selectedVideoId: dogfoodVideo.id,
    });

    render(<OneLoopStudio showAgentWorkflowUi />);

    expect(screen.getByTestId('studio-transcript-retry').textContent).toMatch(/retry transcript/i);
    expect(screen.getByTestId('studio-ide-status').textContent.toLowerCase()).not.toMatch(
      /reviewed actions|durable workflows/,
    );
  });

  it('keeps Export and Build live enabled for anonymous SeaDance/Cluely packs with empty events[]', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    pack.architecture = {
      summary: 'Five-stage monetization pipeline.',
      stages: [{ id: 'stage_1', name: 'Target Lead Extraction' }],
      mermaid: null,
    };
    pack.artifacts = [
      {
        path_hint: 'interfaces/agency_pipeline.ts',
        purpose: 'Lead and retainer contracts.',
        interface: 'export interface AgencyClientPipeline {}',
      },
      {
        path_hint: 'interfaces/cluely_architecture.ts',
        purpose: 'Micro-app factory.',
        interface: 'export interface ProductSuiteManager {}',
      },
    ];
    pack.stack = {
      tools: [
        { name: 'SeaDance 2.5', check: 'seadance --version' },
        { name: 'Cluely Desktop', check: 'curl -I https://cluely.com' },
      ],
    };

    useDashboardStore.setState({
      videos: [
        {
          ...dogfoodVideo,
          videoPack: {
            packId: pack.id,
            videoId: 'pBsT6v-ciO8',
            sourceUrl: dogfoodVideo.url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack: { ...pack, video_id: 'pBsT6v-ciO8', source_url: dogfoodVideo.url },
          },
        },
      ],
      selectedVideoId: dogfoodVideo.id,
    });

    render(<OneLoopStudio showAgentWorkflowUi />);

    expect(screen.getByTestId('studio-ide-ship').hasAttribute('disabled')).toBe(false);
    expect(screen.getByTestId('studio-ide-ship').textContent).toMatch(/ship this/i);
    expect(screen.getByTestId('studio-build-live-button').hasAttribute('disabled')).toBe(false);
    expect(screen.getByTestId('studio-act-button').textContent).toMatch(/act on this run/i);

    expect(screen.getByTestId('studio-ide-output-events').textContent).toMatch(/no extracted events/i);
    expect(screen.getByTestId('studio-ide-output-events').textContent.toLowerCase()).not.toContain(
      'insights',
    );
    expect(screen.getByTestId('pack-workbench')).toBeTruthy();
    expect(screen.getByTestId('pack-architecture').textContent).toMatch(/five-stage/i);

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-tools'));
    const tools = screen.getByTestId('studio-ide-output-tools');
    expect(tools.textContent).toMatch(/SeaDance/i);
    expect(tools.textContent).toMatch(/Cluely/i);
    expect(tools.textContent).toMatch(/cannot run this check/i);
  });
});

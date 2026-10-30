// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';
import { pollVideoToActions, startVideoToActions } from '@/lib/studio-workflow';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/studio',
}));
const mockSession = vi.hoisted(() => ({ current: null as null | { user: { email: string } } }));
vi.mock('next-auth/react', () => ({ useSession: () => ({ data: mockSession.current, status: mockSession.current ? 'authenticated' : 'unauthenticated' }) }));
vi.mock('@/lib/studio-workflow', () => ({ startVideoToActions: vi.fn(), pollVideoToActions: vi.fn() }));
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
  mockSession.current = null;
  vi.mocked(startVideoToActions).mockReset();
  vi.mocked(pollVideoToActions).mockReset();
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

  it('requires a stored analyzed pack before Act is enabled', () => {
    useDashboardStore.setState({ videos: [dogfoodVideo], selectedVideoId: dogfoodVideo.id });
    render(<OneLoopStudio showAgentWorkflowUi />);
    expect(screen.getByTestId('studio-act-button').hasAttribute('disabled')).toBe(true);
    fireEvent.click(screen.getByTestId('studio-act-button'));
    expect(startVideoToActions).not.toHaveBeenCalled();
  });

  it('shows runnable stack checks as pending for a signed-in viewer', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    pack.stack = { tools: [{ name: 'Vercel' }] };
    mockSession.current = { user: { email: 'viewer@example.com' } };
    useDashboardStore.setState({
      videos: [{ ...dogfoodVideo, videoPack: {
        packId: pack.id, videoId: dogfoodVideo.id, sourceUrl: dogfoodVideo.url,
        sourceHash: pack.provenance.source_hash, version: pack.version,
        pack: { ...pack, video_id: dogfoodVideo.id, source_url: dogfoodVideo.url },
      } }],
      selectedVideoId: dogfoodVideo.id,
    });
    render(<OneLoopStudio showAgentWorkflowUi />);
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-tools'));
    expect(screen.getByTestId('studio-stack-checks').textContent).toMatch(/pending/i);
    expect(screen.getByTestId('studio-stack-checks').textContent).not.toMatch(/signed out/i);
  });

  it('shows named tools in the promoted workbench for a tool-only pack', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    pack.architecture = null;
    pack.artifacts = [];
    pack.stack = { tools: [{ name: 'Vercel', evidence: 'Mentioned in the video' }] };
    useDashboardStore.setState({
      videos: [{ ...dogfoodVideo, videoPack: {
        packId: pack.id, videoId: dogfoodVideo.id, sourceUrl: dogfoodVideo.url,
        sourceHash: pack.provenance.source_hash, version: pack.version,
        pack: { ...pack, video_id: dogfoodVideo.id, source_url: dogfoodVideo.url },
      } }],
      selectedVideoId: dogfoodVideo.id,
    });
    render(<OneLoopStudio showAgentWorkflowUi />);
    expect(screen.getByTestId('pack-tools').textContent).toMatch(/Vercel/);
    expect(screen.getByTestId('pack-tools').textContent).toMatch(/Mentioned in the video/);
  });

  it('discards late Act results after switching to another stored pack', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    const rowA: Video = { ...dogfoodVideo, videoPack: {
      packId: pack.id, videoId: dogfoodVideo.id, sourceUrl: dogfoodVideo.url,
      sourceHash: pack.provenance.source_hash, version: pack.version,
      pack: { ...pack, video_id: dogfoodVideo.id, source_url: dogfoodVideo.url },
    } };
    const otherUrl = 'https://www.youtube.com/watch?v=auJzb1D-fag';
    const rowB: Video = { ...rowA, id: 'auJzb1D-fag', url: otherUrl,
      videoPack: { ...rowA.videoPack!, packId: 'other-pack', videoId: 'auJzb1D-fag', sourceUrl: otherUrl,
        pack: { ...pack, id: 'other-pack', video_id: 'auJzb1D-fag', source_url: otherUrl } },
    };
    useDashboardStore.setState({ videos: [rowA, rowB], selectedVideoId: rowA.id });
    vi.mocked(startVideoToActions).mockResolvedValue({ ok: true, status: 200, runId: 'run-a' });
    let finishPoll!: (value: Awaited<ReturnType<typeof pollVideoToActions>>) => void;
    vi.mocked(pollVideoToActions).mockImplementation(() => new Promise((resolve) => { finishPoll = resolve; }));
    render(<OneLoopStudio showAgentWorkflowUi />);
    fireEvent.click(screen.getByTestId('studio-act-button'));
    await waitFor(() => expect(pollVideoToActions).toHaveBeenCalled());
    useDashboardStore.setState({ selectedVideoId: rowB.id });
    finishPoll({ ok: true, status: 200, runId: 'run-a', runStatus: 'completed',
      result: { url: rowA.url, transcriptChars: 0, actionCount: 1,
        actions: [{ tool: 'Old pack action', status: 'completed', result: 'from A' }] } });
    await waitFor(() => expect(screen.getByTestId('studio-act-button').textContent).toMatch(/Act on this run/));
    expect(screen.queryByText('Old pack action')).toBeNull();
    expect(screen.queryByText('from A')).toBeNull();
  });

});

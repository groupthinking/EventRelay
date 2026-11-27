// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';
import * as studioWorkflow from '@/lib/studio-workflow';
import { GATE_RECEIPT_VERSION } from '@/lib/gate-transition';

const navigation = { push: vi.fn() };

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: navigation.push }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock('@/components/Nav', () => ({ default: () => null }));
vi.mock('@/lib/use-youtube-player', () => ({
  useYouTubePlayer: () => ({
    containerRef: { current: null },
    ready: false,
    failed: false,
    seekTo: vi.fn(),
  }),
}));

const FIXTURE_ID = 'auJzb1D-fag';
const FIXTURE_URL = `https://www.youtube.com/watch?v=${FIXTURE_ID}`;

const baseVideo: Video = {
  id: 'row-fixture',
  title: 'Cut 5 deploy unify',
  url: FIXTURE_URL,
  status: 'complete',
  progress: 100,
  transcript: 'Enough transcript text for analysis ready state in Studio Cut 5 tests.',
};

beforeEach(() => {
  vi.stubGlobal('React', React);
  navigation.push.mockReset();
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => Promise.resolve());
  useDashboardStore.setState({ videos: [baseVideo], selectedVideoId: baseVideo.id });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('OneLoopStudio Deploy unify', () => {
  it('exposes one deploy path (Check preflight) without a toolbar Build live button', () => {
    render(<OneLoopStudio />);
    expect(screen.getByTestId('studio-deploy-button').textContent?.trim()).toBe('Check preflight');
    expect(screen.queryByTestId('studio-build-live-button')).toBeNull();
  });

  it('shows a HOLD receipt with no live URL after preflight gate', async () => {
    vi.spyOn(studioWorkflow, 'startStudioDeploy').mockResolvedValue({
      ok: false,
      status: 409,
      message: 'Artifact-bound evidence required.',
      gate: {
        decision: 'HOLD',
        reason: 'Artifact-bound evidence required.',
        reason_code: 'GATE_HOLD_MISSING_EVIDENCE',
        receiptId: 'er:gate:v2:hold',
        receiptHash: 'c'.repeat(64),
        version: 'eventrelay.gate-receipt.v2',
        transitionId: `attempt:${FIXTURE_ID}`,
        retained: false,
      },
    });

    render(<OneLoopStudio />);
    fireEvent.click(screen.getByTestId('studio-deploy-button'));

    await waitFor(() => {
      expect(screen.getByTestId('studio-gate-receipt')).toBeTruthy();
    });
    expect(screen.getByTestId('studio-gate-decision').textContent).toBe('HOLD');
    expect(screen.getByTestId('studio-gate-reason').textContent).toMatch(/Artifact-bound/i);
    expect(screen.queryByTestId('studio-gate-live-url')).toBeNull();
    expect(screen.getByTestId('studio-gate-receipt').textContent).not.toMatch(/Deploy completed/i);
  });

  it('redirects to login when preflight returns 401 (existing auth wall)', async () => {
    vi.spyOn(studioWorkflow, 'startStudioDeploy').mockResolvedValue({
      ok: false,
      status: 401,
      error: 'Sign in required',
    });
    render(<OneLoopStudio />);
    fireEvent.click(screen.getByTestId('studio-deploy-button'));
    await waitFor(() => {
      expect(navigation.push).toHaveBeenCalledWith(
        expect.stringMatching(/^\/login\?callbackUrl=/),
      );
    });
    expect(screen.queryByTestId('studio-gate-receipt')).toBeNull();
  });

  it('clears the gate receipt when the selected pack changes', async () => {
    vi.spyOn(studioWorkflow, 'startStudioDeploy').mockResolvedValue({
      ok: false,
      status: 409,
      gate: {
        decision: 'HOLD',
        reason: 'Held for selection scope.',
        reason_code: 'GATE_HOLD_MISSING_EVIDENCE',
        receiptId: 'er:gate:v2:scope',
        receiptHash: 'e'.repeat(64),
        version: GATE_RECEIPT_VERSION,
      },
    });
    const other: Video = {
      ...baseVideo,
      id: 'row-other',
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      title: 'Other selection',
    };
    useDashboardStore.setState({
      videos: [baseVideo, other],
      selectedVideoId: baseVideo.id,
    });
    render(<OneLoopStudio />);
    fireEvent.click(screen.getByTestId('studio-deploy-button'));
    await waitFor(() => {
      expect(screen.getByTestId('studio-gate-receipt')).toBeTruthy();
    });
    useDashboardStore.setState({ selectedVideoId: other.id });
    await waitFor(() => {
      expect(screen.queryByTestId('studio-gate-receipt')).toBeNull();
    });
  });
});

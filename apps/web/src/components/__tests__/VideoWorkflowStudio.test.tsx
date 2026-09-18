// @vitest-environment jsdom
import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import VideoWorkflowStudio from '@/components/VideoWorkflowStudio';
import { startStudioDeploy } from '@/lib/studio-workflow';

const navigation = { push: vi.fn() };

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: navigation.push }),
}));
vi.mock('@/hooks/use-realtime-voice', () => ({
  useRealtimeVoice: () => ({
    disconnect: vi.fn(),
    isActive: false,
    start: vi.fn(),
    status: 'idle',
    stop: vi.fn(),
    toggleMute: vi.fn(),
  }),
}));
vi.mock('@/lib/studio-deploy', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/lib/studio-deploy')>(),
  kickoffStudioDeploy: vi.fn(),
  pollStudioJob: vi.fn(),
}));
vi.mock('@/lib/studio-workflow', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/lib/studio-workflow')>(),
  pollStudioDeploy: vi.fn(),
  startStudioDeploy: vi.fn(),
}));

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: false,
    status: 503,
    json: async () => ({}),
  }));
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('VideoWorkflowStudio', () => {
  it('uses client routing for an unauthorized deploy handoff', async () => {
    vi.mocked(startStudioDeploy).mockResolvedValue({ ok: false, status: 401 });
    render(<VideoWorkflowStudio />);

    expect(screen.getByRole('link', { name: 'Sign in' }).getAttribute('href')).toBe(
      '/login?callbackUrl=%2Fstudio',
    );

    fireEvent.change(screen.getByLabelText('Paste a YouTube link'), {
      target: { value: 'https://www.youtube.com/watch?v=auJzb1D-fag' },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /^Run$/ }));
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(screen.getByText('Planning draft only. Studio does not run the full agent pipeline; use Dashboard for live results.')).toBeTruthy();
    const deployCard = screen.getByText('Deploy').closest('button');
    expect(deployCard).not.toBeNull();
    await act(async () => {
      fireEvent.click(deployCard!);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Run deploy handoff' }));
      await Promise.resolve();
    });
    expect(navigation.push).toHaveBeenCalledWith('/login?callbackUrl=%2Fstudio');
  });
});

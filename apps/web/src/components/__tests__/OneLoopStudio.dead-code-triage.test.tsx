// @vitest-environment jsdom
/**
 * Cut 6 — Dead-code triage contract.
 *
 * Decision (logged): DELETE PackWorkbench / Act UI leftovers / GitHub PR opener
 * surfaces. Capabilities already live under Cut 4 IA (Files / Canvas / Code /
 * Tools). Do not restore as a parallel first-class shell.
 *
 * Fixture: auJzb1D-fag only.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';
import { studioEventsEmptyMessage } from '@/lib/studio-pipeline-status';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/studio',
}));

vi.mock('@/components/Nav', () => ({ default: () => null }));

vi.mock('@/lib/use-youtube-player', () => ({
  useYouTubePlayer: () => ({
    containerRef: (() => undefined) as (node: HTMLDivElement | null) => void,
    ready: false,
    failed: false,
    direct: false,
    currentTime: 0,
    duration: null,
    isPlaying: false,
    seekTo: vi.fn(),
    play: vi.fn(),
    pause: vi.fn(),
  }),
}));

const FIXTURE_ID = 'auJzb1D-fag';

const baseVideo: Video = {
  id: 'vid-cut6',
  url: `https://www.youtube.com/watch?v=${FIXTURE_ID}`,
  title: 'Cut 6 fixture',
  status: 'complete',
  progress: 100,
  transcript: 'Enough transcript text for analysis ready state in Studio tests.',
};

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => Promise.resolve());
  useDashboardStore.setState({ videos: [baseVideo], selectedVideoId: baseVideo.id });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Cut 6 dead-code triage', () => {
  it('does not render PackWorkbench, Act, or GitHub PR opener controls', () => {
    render(<OneLoopStudio />);
    expect(screen.queryByTestId('pack-workbench')).toBeNull();
    expect(screen.queryByTestId('pack-architecture')).toBeNull();
    expect(screen.queryByTestId('pack-artifacts')).toBeNull();
    expect(screen.queryByTestId('studio-act-button')).toBeNull();
    expect(screen.queryByTestId('studio-open-github-prs')).toBeNull();
    expect(screen.queryByRole('button', { name: /open.*github.*pr/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /^act$/i })).toBeNull();
  });

  it('keeps architecture and artifacts on Cut 4 Code & Spec IA', () => {
    render(<OneLoopStudio />);
    // Code & Spec tab hosts the successors — not a parallel PackWorkbench shell.
    expect(screen.getByTestId('studio-ide-output-tab-code')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output-tab-tasks')).toBeTruthy();
  });

  it('points empty-events copy at Code & Spec / Tasks & Tools — not a dead workbench below', () => {
    const message = studioEventsEmptyMessage({
      busy: false,
      hasCompletedRun: true,
      eventCount: 0,
      hasArchitecture: true,
      artifactCount: 2,
      toolCount: 1,
    });
    expect(message.toLowerCase()).toMatch(/no extracted events/);
    expect(message.toLowerCase()).toMatch(/code & spec|tasks & tools/);
    expect(message.toLowerCase()).not.toContain('are below');
  });

  it('removes PackWorkbench / Act leftovers / PR opener from Studio sources', () => {
    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    const output = readFileSync(
      join(process.cwd(), 'src/components/studio/StudioIdeOutput.tsx'),
      'utf8',
    );

    expect(studio).not.toMatch(/function PackWorkbench/);
    expect(studio).not.toContain('pack-workbench');
    expect(studio).not.toContain('studioPromotePackWorkbench');
    expect(studio).not.toContain('setWorkflowActions');
    expect(studio).not.toContain('workflowActionSelectionId');
    expect(studio).not.toContain('openGitHubPrs');
    expect(studio).not.toContain('openApprovedSpecsPrs');
    expect(studio).not.toContain('github-pr-client');
    expect(studio).not.toContain('studio-act-button');
    expect(output).not.toContain('packWorkbench');
    expect(output).toContain('studio-pack-architecture');
    expect(output).toContain('studio-pack-artifacts');
    expect(studio).not.toMatch(/dQw4w9WgXcQ/);
    expect(output).not.toMatch(/dQw4w9WgXcQ/);
  });

  it('drops the orphaned GitHub PR client module (no Studio callers)', () => {
    const webRoot = process.cwd();
    expect(() => readFileSync(join(webRoot, 'src/lib/github-pr-client.ts'), 'utf8')).toThrow();
    expect(() =>
      readFileSync(join(webRoot, 'src/lib/__tests__/github-pr-client.test.ts'), 'utf8'),
    ).toThrow();
    expect(() =>
      readFileSync(join(webRoot, 'src/app/studio/actions.ts'), 'utf8'),
    ).toThrow();
  });
});

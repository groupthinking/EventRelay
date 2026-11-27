/* @vitest-environment jsdom */
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioIdeOutput from '@/components/studio/StudioIdeOutput';
import type { Video } from '@/store/dashboard-types';
import { reviewPackFixture } from '@/test/grounded-spec-fixture';

const downloads = vi.hoisted(() => ({ calls: [] as Array<{ name: string; content: string }> }));
vi.mock('@/lib/download-file', async (original) => ({
  ...(await original<object>()),
  downloadTextFile: (name: string, content: string) => {
    downloads.calls.push({ name, content });
  },
}));

function videoWithSegments(): Video {
  const pack = reviewPackFixture();
  pack.transcript = {
    language: 'en',
    full_text: 'Welcome Install Next.js Deploy',
    segments: [
      { idx: 0, start_s: 0, end_s: 10, text: 'Welcome to the build' },
      { idx: 1, start_s: 10, end_s: 25, text: 'Install Next.js first' },
      { idx: 2, start_s: 40, end_s: 50, text: 'Deploy to Vercel' },
    ],
  };
  return {
    id: 'row-transcript',
    title: 'Transcript tools',
    url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    status: 'complete',
    progress: 100,
    transcript: 'Welcome Install Next.js Deploy',
    videoPack: {
      packId: pack.id,
      videoId: pack.video_id,
      sourceUrl: pack.source_url,
      sourceHash: pack.provenance.source_hash,
      version: pack.version,
      pack,
    },
  };
}

beforeEach(() => {
  vi.stubGlobal('React', React);
  downloads.calls.length = 0;
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('StudioIdeOutput transcript tools', () => {
  it('searches the transcript, shows the caption source, and exports SRT/VTT', () => {
    render(<StudioIdeOutput video={videoWithSegments()} activeSection="transcript" />);
    expect(screen.getByTestId('studio-transcript-caption-source').textContent).toBe('Timed captions');
    expect(screen.getAllByRole('listitem').length).toBeGreaterThanOrEqual(3);

    fireEvent.change(screen.getByLabelText('Search transcript'), { target: { value: 'vercel' } });
    expect(screen.getByTestId('studio-transcript-match-count').textContent).toBe('1 of 3');
    expect(screen.getByTestId('studio-transcript-body').textContent).toContain('Deploy to Vercel');
    expect(screen.getByTestId('studio-transcript-body').textContent).not.toContain('Welcome to the build');

    fireEvent.change(screen.getByLabelText('Search transcript'), { target: { value: 'zzz' } });
    expect(screen.getByTestId('studio-transcript-body').textContent).toMatch(/No transcript lines match/);

    fireEvent.click(screen.getByTestId('studio-transcript-download-srt'));
    fireEvent.click(screen.getByTestId('studio-transcript-download-vtt'));
    expect(downloads.calls.map((call) => call.name)).toEqual(['auJzb1D-fag.srt', 'auJzb1D-fag.vtt']);
    // Exports always cover the whole transcript, not the filtered view.
    expect(downloads.calls[0].content).toContain('Welcome to the build');
    expect(downloads.calls[0].content).toContain('Deploy to Vercel');
    expect(downloads.calls[1].content.startsWith('WEBVTT')).toBe(true);
  });

  it('only offers Quote when a handler is provided and passes text and seconds', () => {
    const { rerender } = render(<StudioIdeOutput video={videoWithSegments()} activeSection="transcript" />);
    expect(screen.queryByTestId('studio-transcript-quote-1')).toBeNull();

    const onQuote = vi.fn();
    rerender(<StudioIdeOutput video={videoWithSegments()} activeSection="transcript" onQuoteToChat={onQuote} />);
    fireEvent.click(screen.getByTestId('studio-transcript-quote-1'));
    expect(onQuote).toHaveBeenCalledWith('Install Next.js first', 10);
  });

  it('keeps the existing transcript test ids', () => {
    render(<StudioIdeOutput video={videoWithSegments()} activeSection="transcript" onSeek={() => undefined} />);
    expect(screen.getByTestId('studio-ide-output-transcript')).toBeTruthy();
    expect(screen.getByTestId('studio-transcript-body')).toBeTruthy();
    expect(screen.getByTestId('studio-transcript-seek-1')).toBeTruthy();
  });
});

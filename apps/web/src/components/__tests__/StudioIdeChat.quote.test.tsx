/* @vitest-environment jsdom */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioIdeChat from '@/components/studio/StudioIdeChat';

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal('React', React);
  fetchMock.mockReset();
  fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => ({ answer: 'ok' }) });
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const composer = () => screen.getByTestId('studio-ide-chat-input') as HTMLTextAreaElement;

describe('StudioIdeChat quote and quick-action signals', () => {
  it('appends a timestamped quote once per nonce and focuses the composer', async () => {
    const { rerender } = render(<StudioIdeChat videoId="auJzb1D-fag" packId="vp:v0:auJzb1D-fag" />);
    expect(composer().value).toBe('');

    rerender(
      <StudioIdeChat
        videoId="auJzb1D-fag"
        packId="vp:v0:auJzb1D-fag"
        quoteSignal={{ text: ' Install Next.js first ', timestampSec: 70, nonce: 1 }}
      />,
    );
    await waitFor(() => expect(composer().value).toBe('> [1:10] "Install Next.js first"\n\n'));
    await waitFor(() => expect(document.activeElement).toBe(composer()));

    // The same nonce is not applied twice.
    rerender(
      <StudioIdeChat
        videoId="auJzb1D-fag"
        packId="vp:v0:auJzb1D-fag"
        quoteSignal={{ text: ' Install Next.js first ', timestampSec: 70, nonce: 1 }}
      />,
    );
    expect(composer().value).toBe('> [1:10] "Install Next.js first"\n\n');

    // A new nonce appends after what the user already has.
    rerender(
      <StudioIdeChat
        videoId="auJzb1D-fag"
        packId="vp:v0:auJzb1D-fag"
        quoteSignal={{ text: 'Deploy to Vercel', nonce: 2 }}
      />,
    );
    await waitFor(() =>
      expect(composer().value).toBe('> [1:10] "Install Next.js first"\n\n> "Deploy to Vercel"\n\n'),
    );
  });

  it('ignores an empty quote', async () => {
    const { rerender } = render(<StudioIdeChat videoId="auJzb1D-fag" packId="vp:v0:auJzb1D-fag" />);
    rerender(
      <StudioIdeChat videoId="auJzb1D-fag" packId="vp:v0:auJzb1D-fag" quoteSignal={{ text: '   ', nonce: 1 }} />,
    );
    expect(composer().value).toBe('');
  });

  it('sends a quick-action prompt once per nonce', async () => {
    const { rerender } = render(<StudioIdeChat videoId="auJzb1D-fag" packId="vp:v0:auJzb1D-fag" />);
    rerender(
      <StudioIdeChat
        videoId="auJzb1D-fag"
        packId="vp:v0:auJzb1D-fag"
        quickActionSignal={{ prompt: 'Draft a step-by-step SOP from this video', nonce: 1 }}
      />,
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body)).query).toBe(
      'Draft a step-by-step SOP from this video',
    );
    await screen.findByText('ok');

    rerender(
      <StudioIdeChat
        videoId="auJzb1D-fag"
        packId="vp:v0:auJzb1D-fag"
        quickActionSignal={{ prompt: 'Draft a step-by-step SOP from this video', nonce: 1 }}
      />,
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('keeps working without either signal', () => {
    render(<StudioIdeChat videoId="auJzb1D-fag" packId="vp:v0:auJzb1D-fag" />);
    fireEvent.change(composer(), { target: { value: 'hello' } });
    expect(composer().value).toBe('hello');
  });
});

/* @vitest-environment jsdom */
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProjectWorkspaceHome from './ProjectWorkspaceHome';
import { SHOWCASE_CARDS, SHOWCASE_SAMPLE_URL } from './showcase-data';

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  submitHomePaste: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mocks.push }),
  usePathname: () => '/',
}));

vi.mock('@/lib/studio-handoff', () => ({
  submitHomePaste: mocks.submitHomePaste,
}));

beforeEach(() => {
  vi.stubGlobal('React', React);
  mocks.push.mockReset();
  mocks.submitHomePaste.mockReset();
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('ProjectWorkspaceHome', () => {
  it('rejects an invalid URL with an announced error and does not navigate', () => {
    mocks.submitHomePaste.mockReturnValue(null);
    render(<ProjectWorkspaceHome />);

    const input = screen.getByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: 'not a YouTube URL' } });
    fireEvent.submit(input.closest('form')!);

    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(input.getAttribute('aria-describedby')).toBe('home-dock-error');
    const alert = screen.getByRole('alert');
    expect(alert.id).toBe('home-dock-error');
    expect(mocks.push).not.toHaveBeenCalled();
  });

  it('hands a valid URL and the selected intent to Studio', () => {
    mocks.submitHomePaste.mockReturnValue('/studio?video=fixture');
    render(<ProjectWorkspaceHome />);

    fireEvent.click(screen.getByRole('button', { name: 'Build SOP' }));
    expect(screen.getByRole('button', { name: 'Build SOP' }).getAttribute('aria-pressed')).toBe('true');

    const input = screen.getByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: SHOWCASE_SAMPLE_URL } });
    fireEvent.submit(input.closest('form')!);

    expect(mocks.submitHomePaste).toHaveBeenCalledWith(SHOWCASE_SAMPLE_URL);
    expect(mocks.push).toHaveBeenCalledWith('/studio?video=fixture&intent=sop');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('shows the sample link by default and hides it when sampleEnabled is false', () => {
    const { unmount } = render(<ProjectWorkspaceHome />);
    expect(screen.getByRole('link', { name: /try a sample/i }).getAttribute('href')).toBe(
      '/studio?sample=1',
    );
    unmount();

    mocks.submitHomePaste.mockReturnValue(null);
    render(<ProjectWorkspaceHome sampleEnabled={false} />);
    expect(screen.queryByRole('link', { name: /try a sample/i })).toBeNull();

    const input = screen.getByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: 'not a YouTube URL' } });
    fireEvent.submit(input.closest('form')!);
    expect(screen.getByRole('alert').textContent).toBe(
      'Paste a valid YouTube URL to start a Video Pack run.',
    );
  });

  it('uses the Studio-bound fixture video id in the sample URL', () => {
    expect(SHOWCASE_SAMPLE_URL).toContain('auJzb1D-fag');
    expect(SHOWCASE_SAMPLE_URL).not.toContain('dQw4w9WgXcQ');
  });

  it('filters showcase cards by category tab', () => {
    render(<ProjectWorkspaceHome />);
    expect(screen.getAllByTestId('showcase-card')).toHaveLength(SHOWCASE_CARDS.length);

    fireEvent.click(screen.getByRole('tab', { name: 'Meetings → SOP' }));
    const expected = SHOWCASE_CARDS.filter((card) => card.category === 'Meetings → SOP');
    const cards = screen.getAllByTestId('showcase-card');
    expect(cards).toHaveLength(expected.length);
    for (const card of cards) expect(card.getAttribute('data-category')).toBe('Meetings → SOP');
    expect(screen.getByRole('tab', { name: 'Meetings → SOP' }).getAttribute('aria-selected')).toBe('true');

    fireEvent.click(screen.getByRole('tab', { name: 'All' }));
    expect(screen.getAllByTestId('showcase-card')).toHaveLength(SHOWCASE_CARDS.length);
  });

  it('prefills the dock, selects the intent, and focuses the field when a card is picked', () => {
    render(<ProjectWorkspaceHome />);
    const card = SHOWCASE_CARDS.find((item) => item.id === 'meeting-sop')!;

    fireEvent.click(screen.getByRole('button', { name: new RegExp(card.title) }));

    const input = screen.getByLabelText('YouTube URL') as HTMLInputElement;
    expect(input.value).toBe(SHOWCASE_SAMPLE_URL);
    expect(document.activeElement).toBe(input);
    expect(screen.getByRole('button', { name: 'Build SOP' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByText(/Selected Recording to SOP/)).toBeTruthy();
  });

  it('does not overwrite a URL the user already typed when a card is picked', () => {
    render(<ProjectWorkspaceHome />);
    const input = screen.getByLabelText('YouTube URL') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'https://youtu.be/example' } });

    fireEvent.click(screen.getAllByTestId('showcase-card')[0]!);

    expect(input.value).toBe('https://youtu.be/example');
  });

  it('keeps every showcase description free of results, metrics, and banned claims', () => {
    for (const card of SHOWCASE_CARDS) {
      const copy = `${card.title} ${card.description}`;
      expect(copy).not.toMatch(/\d+\s?(%|x\b)/i);
      expect(copy).not.toMatch(/any video|verified transcript|reliable transcript|guaranteed/i);
    }
  });
});

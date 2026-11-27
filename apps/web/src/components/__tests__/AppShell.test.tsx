// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AppShell, { readRecentRuns } from '@/components/AppShell';

const usePathnameMock = vi.fn();

vi.mock('next/navigation', () => ({
  usePathname: () => usePathnameMock(),
}));

beforeEach(() => {
  vi.stubGlobal('React', React);
  usePathnameMock.mockReset();
  usePathnameMock.mockReturnValue('/');
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  delete document.documentElement.dataset.theme;
  delete document.documentElement.dataset.contrast;
  window.localStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function seedRuns(videos: unknown[]) {
  window.localStorage.setItem('eventrelay-dashboard-v1', JSON.stringify({ state: { videos }, version: 0 }));
}

describe('AppShell', () => {
  it('renders the primary navigation and keeps secondary links behind See more', () => {
    render(
      <AppShell>
        <p>page body</p>
      </AppShell>,
    );

    for (const name of ['New project', 'Studio', 'Skills', 'Connectors', 'Examples']) {
      expect(screen.getByRole('link', { name })).toBeTruthy();
    }
    expect(screen.getByText('page body')).toBeTruthy();
    expect(screen.queryByRole('link', { name: 'Pricing' })).toBeNull();

    const more = screen.getByRole('button', { name: /see more/i });
    expect(more.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(more);
    expect(more.getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByRole('link', { name: 'Pricing' }).getAttribute('href')).toBe('/pricing');
    expect(screen.getByRole('link', { name: 'API Docs' }).getAttribute('href')).toBe('/docs/api');
  });

  it('marks the current route and links Get Pro to /pricing', () => {
    usePathnameMock.mockReturnValue('/studio');
    render(<AppShell>{null}</AppShell>);

    expect(screen.getByRole('link', { name: 'Studio' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByRole('link', { name: 'New project' }).getAttribute('aria-current')).toBeNull();
    const getPro = screen.getAllByRole('link', { name: 'Get Pro' });
    expect(getPro.length).toBeGreaterThan(0);
    for (const link of getPro) expect(link.getAttribute('href')).toBe('/pricing');
  });

  it('collapses with the toggle button and the Ctrl+/ shortcut', () => {
    render(<AppShell>{null}</AppShell>);
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    expect(nav.dataset.collapsed).toBe('false');

    fireEvent.click(screen.getByRole('button', { name: 'Collapse sidebar' }));
    expect(nav.dataset.collapsed).toBe('true');
    expect(screen.getByRole('button', { name: 'Expand sidebar' }).getAttribute('aria-expanded')).toBe('false');

    fireEvent.keyDown(window, { key: '/', ctrlKey: true });
    expect(nav.dataset.collapsed).toBe('false');
  });

  it('lists real local runs and shows an honest empty state otherwise', async () => {
    const empty = render(<AppShell>{null}</AppShell>);
    expect(await screen.findByText('No local runs yet')).toBeTruthy();
    empty.unmount();

    const url = 'https://www.youtube.com/watch?v=auJzb1D-fag';
    seedRuns([{ id: 'run-1', title: 'Video One', url, progress: 100, status: 'complete' }]);
    render(<AppShell>{null}</AppShell>);
    const link = await screen.findByRole('link', { name: 'Video One' });
    expect(link.getAttribute('href')).toBe(`/studio?video=${encodeURIComponent(url)}`);
    expect(screen.queryByText('No local runs yet')).toBeNull();
  });

  it('readRecentRuns ignores malformed storage and caps the list at five', () => {
    window.localStorage.setItem('eventrelay-dashboard-v1', '{not json');
    expect(readRecentRuns()).toEqual([]);

    seedRuns([
      ...Array.from({ length: 8 }, (_, index) => ({ id: `r${index}`, title: `Run ${index}`, url: `u${index}` })),
      { id: 'bad', title: 42, url: 'x' },
    ]);
    const runs = readRecentRuns();
    expect(runs).toHaveLength(5);
    expect(runs[0]).toEqual({ id: 'r0', title: 'Run 0', url: 'u0' });
  });

  it('shares the document theme toggle with the rest of the app', () => {
    render(<AppShell>{null}</AppShell>);
    fireEvent.click(screen.getByRole('button', { name: 'Switch to light mode' }));
    expect(document.documentElement.dataset.theme).toBe('light');
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark mode' }));
    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  it('focuses the Home dock instead of navigating when New project is clicked on /', () => {
    render(
      <AppShell>
        <input id="home-dock-input" aria-label="dock" />
      </AppShell>,
    );
    fireEvent.click(screen.getByRole('link', { name: 'New project' }));
    expect(document.activeElement?.id).toBe('home-dock-input');
  });
});

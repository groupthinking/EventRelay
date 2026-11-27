/* @vitest-environment jsdom */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProjectWorkspace from '../ProjectWorkspace';
import { createOrUpdateLocalProject } from '@/lib/projects/project-local-store';

const nav = vi.hoisted(() => {
  let params = new URLSearchParams();
  const listeners = new Set<() => void>();
  return {
    replace: vi.fn(),
    get: () => params,
    set(search: string) {
      params = new URLSearchParams(search);
      listeners.forEach((listener) => listener());
    },
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
});

vi.mock('next/navigation', async () => {
  const react = await import('react');
  return {
    usePathname: () => '/projects/test',
    useRouter: () => ({
      push: vi.fn(),
      replace: (url: string, options?: unknown) => {
        nav.replace(url, options);
        nav.set(url.split('?')[1] ?? '');
      },
    }),
    useSearchParams: () => react.useSyncExternalStore(nav.subscribe, nav.get, nav.get),
  };
});
vi.mock('next-auth/react', () => ({ useSession: () => ({ status: 'unauthenticated', data: null }) }));

const downloads = vi.hoisted(() => ({ calls: [] as Array<{ name: string; content: string; mime?: string }> }));
vi.mock('@/lib/download-file', async (original) => ({
  ...(await original<object>()),
  downloadTextFile: (name: string, content: string, mime?: string) => {
    downloads.calls.push({ name, content, mime });
  },
}));

const URL_A = 'https://www.youtube.com/watch?v=auJzb1D-fag';
const HASH = '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea';
const fetchMock = vi.fn<typeof fetch>();
let packMode: 'ready' | 'missing' = 'ready';

const packData = {
  version: 'v0',
  id: 'vp:v0:auJzb1D-fag',
  video_id: 'auJzb1D-fag',
  source_url: URL_A,
  provenance: { source_hash: HASH },
  transcript: {
    language: 'en',
    full_text: 'Welcome to the build Install Next.js first Deploy to Vercel',
    segments: [
      { idx: 0, start_s: 0, end_s: 10, text: 'Welcome to the build' },
      { idx: 1, start_s: 10, end_s: 25, text: 'Install Next.js first' },
      { idx: 2, start_s: 40, end_s: 50, text: 'Deploy to Vercel' },
    ],
  },
  chapters: [
    { start: 0, end: 20, topic: 'Setup', key_points: ['Install tooling'] },
    { start: 20, end: 60, topic: 'Deploy', key_points: ['Ship to production'] },
  ],
  keyframes: [{ t_s: 5 }, { t_s: 20 }, { t_s: 60 }, { t_s: 90 }],
  events: [
    { id: 'e1', type: 'topic', title: 'Intro', timestamp: '0:10' },
    { id: 'e2', type: 'topic', title: 'Late', timestamp: '0:45' },
    { id: 'e3', type: 'topic', title: 'Untimed' },
  ],
  requirements: [{ id: 'r1', title: 'Req' }],
  action_items: [{ id: 'a1', title: 'Ship it', description: 'Deploy the app', priority: 'high' }],
  stack: { tools: [{ name: 'Next.js', kind: 'framework', evidence: 'said at 0:15' }, { name: 'Vercel' }] },
  architecture: { summary: 'A small deploy walkthrough.', stages: [] },
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });
}

function seedProject(): string {
  const created = createOrUpdateLocalProject({ sourceUrl: URL_A, title: 'Test Video Pack' });
  if (!created.ok) throw new Error('seed failed');
  return created.project.id;
}

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (input) => {
    const url = String(input);
    if (url.startsWith('/api/video/pack')) {
      return packMode === 'ready' ? json({ status: 'success', data: packData }) : json({ status: 'error', error: 'Video pack not found' }, 404);
    }
    if (url === '/api/chat') return json({ answer: 'ok' });
    return json({}, 404);
  });
  packMode = 'ready';
  downloads.calls.length = 0;
  nav.replace.mockReset();
  nav.set('');
  window.localStorage.clear();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

async function renderWorkspace(search = '') {
  const id = seedProject();
  nav.set(search);
  render(<ProjectWorkspace projectId={id} />);
  await screen.findByTestId('project-folders');
  return id;
}

describe('ProjectWorkspace', () => {
  it('shows an honest not-found state for an unknown project', async () => {
    nav.set('');
    render(<ProjectWorkspace projectId="nope" />);
    expect(await screen.findByTestId('project-not-found')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Back to Projects' }).getAttribute('href')).toBe('/projects');
  });

  it('builds the Brief and chapter folders from real pack fields', async () => {
    await renderWorkspace();
    expect(await screen.findByText('A small deploy walkthrough.')).toBeTruthy();
    expect(screen.getByTestId('brief-caption-source').textContent).toBe('Timed captions');
    expect(screen.getByTestId('brief-chapters').textContent).toContain('Setup');
    expect(screen.getByTestId('brief-stack').textContent).toContain('Next.js');
    expect(screen.getByTestId('brief-actions').textContent).toContain('Ship it');
    expect(screen.getByTestId('brief-questions').textContent).toContain('No evidence was captured for Vercel.');

    await waitFor(() => expect(screen.getByTestId('project-folder-ch-2')).toBeTruthy());
    expect(screen.getByTestId('project-folder-count-all').textContent).toBe('9');
    expect(screen.getByTestId('project-folder-count-ch-1').textContent).toBe('1k · 1e');
    expect(screen.getByTestId('project-folder-count-ch-2').textContent).toBe('2k · 1e');
    expect(screen.getByTestId('project-nav-brief').getAttribute('aria-current')).toBe('page');
  });

  it('downloads the Brief as Markdown through the Blob helper', async () => {
    await renderWorkspace();
    fireEvent.click(await screen.findByTestId('brief-download-md'));
    expect(downloads.calls).toHaveLength(1);
    expect(downloads.calls[0].name).toBe('auJzb1D-fag-brief.md');
    expect(downloads.calls[0].mime).toBe('text/markdown;charset=utf-8');
    expect(downloads.calls[0].content).toContain('# Test Video Pack');
    expect(downloads.calls[0].content).toContain('1. [0:00–0:20] Setup');
  });

  it('shows an extract action instead of inventing content when no pack is stored', async () => {
    packMode = 'missing';
    await renderWorkspace();
    expect(await screen.findByTestId('project-brief-no-pack')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Extract Video Pack' })).toBeTruthy();
    expect(screen.getByText('No summary was extracted.')).toBeTruthy();
    expect(screen.getByText('No chapters were extracted.')).toBeTruthy();
  });

  it('syncs the view, folder, and time to the URL', async () => {
    await renderWorkspace();
    fireEvent.click(screen.getByTestId('project-nav-run'));
    expect(nav.replace).toHaveBeenLastCalledWith('/projects/test?view=run', { scroll: false });

    fireEvent.click(await screen.findByTestId('project-folder-ch-2'));
    const last = nav.replace.mock.calls.at(-1)![0] as string;
    const params = new URLSearchParams(last.split('?')[1]);
    expect(params.get('view')).toBe('run');
    expect(params.get('folder')).toBe('ch-2');
    expect(params.get('t')).toBe('20');
    expect(await screen.findByTestId('project-run-folder-chip')).toBeTruthy();

    fireEvent.click(screen.getByTestId('project-nav-brief'));
    expect(new URLSearchParams((nav.replace.mock.calls.at(-1)![0] as string).split('?')[1]).get('view')).toBeNull();
  });

  it('opens a chapter from the Brief into the Run view', async () => {
    await renderWorkspace();
    fireEvent.click(await screen.findByTestId('brief-chapter-2'));
    const params = new URLSearchParams((nav.replace.mock.calls.at(-1)![0] as string).split('?')[1]);
    expect(params.get('view')).toBe('run');
    expect(params.get('folder')).toBe('ch-2');
    expect(params.get('t')).toBe('20');
  });
});

describe('ProjectWorkspace run view', () => {
  it('lists Transcript | Subtitles | Chapters and filters by search and folder', async () => {
    await renderWorkspace('view=run');
    const transcript = await screen.findByTestId('run-transcript');
    expect(within(transcript).getAllByRole('listitem')).toHaveLength(3);
    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual([
      'Transcript',
      'Subtitles',
      'Chapters',
      'AI Notes',
      'AI Chat',
    ]);
    expect(screen.getByTestId('studio-timeline-bar')).toBeTruthy();
    expect(screen.getByTestId('project-run-caption-source').textContent).toBe('Timed captions');

    fireEvent.change(screen.getByLabelText('Search transcript'), { target: { value: 'NEXT.JS' } });
    expect(within(screen.getByTestId('run-transcript')).getAllByRole('listitem')).toHaveLength(1);
    fireEvent.change(screen.getByLabelText('Search transcript'), { target: { value: 'zzz' } });
    expect(screen.getByTestId('run-transcript-empty').textContent).toMatch(/No transcript lines match/);
    fireEvent.change(screen.getByLabelText('Search transcript'), { target: { value: '' } });

    fireEvent.click(screen.getByTestId('project-folder-ch-1'));
    expect(within(await screen.findByTestId('run-transcript')).getAllByRole('listitem')).toHaveLength(2);
    fireEvent.click(screen.getByRole('button', { name: 'Clear folder filter' }));
    expect(within(await screen.findByTestId('run-transcript')).getAllByRole('listitem')).toHaveLength(3);
  });

  it('exports .md, .srt, .vtt and .json through the Blob helper', async () => {
    await renderWorkspace('view=run');
    await screen.findByTestId('run-transcript');
    fireEvent.click(screen.getByTestId('run-download-srt'));
    fireEvent.click(screen.getByTestId('run-download-vtt'));
    fireEvent.click(screen.getByTestId('run-download-json'));
    fireEvent.click(screen.getByTestId('run-download-md'));
    expect(downloads.calls.map((call) => call.name)).toEqual([
      'auJzb1D-fag.srt',
      'auJzb1D-fag.vtt',
      'auJzb1D-fag.json',
      'auJzb1D-fag-transcript.md',
    ]);
    expect(downloads.calls[0].content).toContain('00:00:00,000 --> 00:00:10,000');
    expect(downloads.calls[1].content.startsWith('WEBVTT')).toBe(true);
    expect(JSON.parse(downloads.calls[2].content).segments).toHaveLength(3);
    expect(downloads.calls[3].content).toContain('**[0:10]** Install Next.js first');
  });

  it('previews subtitles in SRT and VTT', async () => {
    await renderWorkspace('view=run');
    fireEvent.click(await screen.findByRole('tab', { name: 'Subtitles' }));
    expect(screen.getByTestId('run-subtitles-preview').textContent).toContain('00:00:10,000 --> 00:00:25,000');
    fireEvent.click(screen.getByRole('button', { name: 'VTT' }));
    expect(screen.getByTestId('run-subtitles-preview').textContent).toContain('00:00:10.000 --> 00:00:25.000');
  });

  it('quotes a transcript line into the chat composer and switches to AI Chat', async () => {
    await renderWorkspace('view=run');
    fireEvent.click(await screen.findByTestId('run-quote-1'));
    expect(screen.getByTestId('run-tab-chat').getAttribute('aria-selected')).toBe('true');
    await waitFor(() =>
      expect((screen.getByTestId('studio-ide-chat-input') as HTMLTextAreaElement).value).toBe(
        '> [0:10] "Install Next.js first"\n\n',
      ),
    );
  });

  it('sends the summarize quick action to chat and keeps the conversation when toggling tabs', async () => {
    await renderWorkspace('view=run');
    const summarize = await screen.findByTestId('run-summarize');
    await waitFor(() => expect((summarize as HTMLButtonElement).disabled).toBe(false));
    await act(async () => {
      fireEvent.click(summarize);
    });
    await waitFor(() => {
      const chatCall = fetchMock.mock.calls.find(([input]) => String(input) === '/api/chat');
      expect(chatCall).toBeTruthy();
      expect(JSON.parse(String(chatCall![1]?.body)).query).toBe('Summarize key steps & decisions');
    });
    expect(screen.getByTestId('run-tab-chat').getAttribute('aria-selected')).toBe('true');
    expect(await screen.findByText('ok')).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: 'AI Notes' }));
    fireEvent.click(screen.getByTestId('run-tab-chat'));
    expect(screen.getByText('ok')).toBeTruthy();
  });

  it('asks about a chapter through the chat', async () => {
    await renderWorkspace('view=run');
    fireEvent.click(await screen.findByRole('tab', { name: 'Chapters' }));
    await act(async () => {
      fireEvent.click(screen.getByTestId('run-ask-chapter-1'));
    });
    await waitFor(() => {
      const chatCall = fetchMock.mock.calls.find(([input]) => String(input) === '/api/chat');
      expect(JSON.parse(String(chatCall![1]?.body)).query).toBe('Summarize chapter 1: "Setup" (0:00–0:20).');
    });
  });

  it('disables transcript exports and says why when the pack has no timed transcript', async () => {
    packMode = 'missing';
    await renderWorkspace('view=run');
    expect(await screen.findByTestId('run-transcript-empty')).toBeTruthy();
    for (const id of ['run-download-srt', 'run-download-vtt', 'run-download-json', 'run-download-md', 'run-copy']) {
      expect((screen.getByTestId(id) as HTMLButtonElement).disabled).toBe(true);
    }
    expect(screen.queryByTestId('studio-timeline-bar')).toBeNull();
  });

  it('renders the Elements and Canvas previews from real data only', async () => {
    await renderWorkspace('view=elements');
    expect(await screen.findByTestId('project-elements')).toBeTruthy();
    expect(screen.getByText('Tools (2)')).toBeTruthy();
    cleanup();
    await renderWorkspace('view=canvas');
    const stages = await screen.findByRole('list', { name: 'Pipeline stages' });
    expect(stages.textContent).toContain('auJzb1D-fag');
    expect(stages.textContent).toContain('Extracted');
  });
});

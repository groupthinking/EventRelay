/* @vitest-environment jsdom */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProjectsLibrary from '../ProjectsLibrary';
import { createOrUpdateLocalProject, readLocalProjects } from '@/lib/projects/project-local-store';

const mocks = vi.hoisted(() => ({ status: 'unauthenticated' as string }));

vi.mock('next-auth/react', () => ({
  useSession: () => ({ status: mocks.status, data: null }),
}));
vi.mock('next/navigation', () => ({
  usePathname: () => '/projects',
  useRouter: () => ({ push: vi.fn() }),
}));

const URL_A = 'https://www.youtube.com/watch?v=auJzb1D-fag';
const URL_B = 'https://www.youtube.com/watch?v=jNQXAC9IVRw';
const fetchMock = vi.fn<typeof fetch>();

function remoteProject(over: Record<string, unknown> = {}) {
  return {
    id: '0b0b55ec-81f8-4cbf-91b3-75f67796b9c1',
    sourceHash: '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea',
    sourceUrl: URL_A,
    videoId: 'auJzb1D-fag',
    title: 'Remote Pack',
    visibility: 'private',
    createdAt: '2026-11-27T00:00:00.000Z',
    updatedAt: '2026-11-27T00:00:00.000Z',
    storage: 'remote',
    ...over,
  };
}
function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });
}

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  mocks.status = 'unauthenticated';
  window.localStorage.clear();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe('ProjectsLibrary (guest)', () => {
  it('shows the sign-in-to-save banner and an honest empty state', async () => {
    render(<ProjectsLibrary />);
    expect(await screen.findByText(/No projects yet/)).toBeTruthy();
    expect(screen.getByTestId('guest-banner')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Sign in to save' }).getAttribute('href')).toBe(
      '/login?callbackUrl=%2Fprojects',
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects an invalid URL with an announced error', async () => {
    render(<ProjectsLibrary />);
    const input = await screen.findByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: 'not a url' } });
    fireEvent.submit(input.closest('form')!);
    expect(screen.getByRole('alert').textContent).toMatch(/valid YouTube/);
    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(readLocalProjects()).toEqual([]);
  });

  it('creates, dedupes, renames, toggles visibility, and deletes a local project', async () => {
    render(<ProjectsLibrary />);
    const input = await screen.findByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: URL_A } });
    fireEvent.change(screen.getByLabelText('Project title (optional)'), { target: { value: 'Test Video Pack' } });
    fireEvent.submit(input.closest('form')!);
    expect(await screen.findByText('Test Video Pack')).toBeTruthy();
    expect(screen.getByText('Local only')).toBeTruthy();
    expect(screen.getByText('Project created in this browser.')).toBeTruthy();

    fireEvent.change(screen.getByLabelText('YouTube URL'), { target: { value: URL_A } });
    fireEvent.submit(screen.getByLabelText('YouTube URL').closest('form')!);
    expect(await screen.findByText('Project already exists for this video.')).toBeTruthy();
    expect(screen.getAllByTestId('project-card')).toHaveLength(1);

    fireEvent.click(screen.getByRole('button', { name: 'Make shared' }));
    expect(await screen.findByRole('button', { name: 'Make private' })).toBeTruthy();
    expect(readLocalProjects()[0].visibility).toBe('shared');

    fireEvent.click(screen.getByRole('button', { name: 'Rename' }));
    const rename = screen.getByLabelText('Project title');
    fireEvent.change(rename, { target: { value: 'Renamed Pack' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText('Renamed Pack')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }));
    await waitFor(() => expect(screen.queryByTestId('project-card')).toBeNull());
    expect(readLocalProjects()).toEqual([]);
  });

  it('links Open in Studio to the canonical /studio?video= handoff', async () => {
    createOrUpdateLocalProject({ sourceUrl: URL_A, title: 'Test Video Pack' });
    render(<ProjectsLibrary />);
    const link = await screen.findByRole('link', { name: 'Open in Studio' });
    expect(link.getAttribute('href')).toBe(`/studio?video=${encodeURIComponent(URL_A)}`);
  });

  it('filters by visibility tab and by search', async () => {
    createOrUpdateLocalProject({ sourceUrl: URL_A, title: 'Alpha Pack', visibility: 'private' });
    createOrUpdateLocalProject({ sourceUrl: URL_B, title: 'Beta Pack', visibility: 'shared' });
    render(<ProjectsLibrary />);
    expect(await screen.findAllByTestId('project-card')).toHaveLength(2);

    fireEvent.click(screen.getByRole('tab', { name: /Shared/ }));
    let cards = screen.getAllByTestId('project-card');
    expect(cards).toHaveLength(1);
    expect(within(cards[0]).getByText('Beta Pack')).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: /All/ }));
    fireEvent.change(screen.getByLabelText('Search projects'), { target: { value: 'alpha' } });
    cards = screen.getAllByTestId('project-card');
    expect(cards).toHaveLength(1);
    expect(within(cards[0]).getByText('Alpha Pack')).toBeTruthy();
  });
});

describe('ProjectsLibrary (signed in)', () => {
  beforeEach(() => {
    mocks.status = 'authenticated';
  });

  it('loads remote projects and creates one through POST /api/projects', async () => {
    fetchMock
      .mockResolvedValueOnce(json({ projects: [remoteProject()] }))
      .mockResolvedValueOnce(json({ project: remoteProject({ title: 'New' }), created: true }, 201))
      .mockResolvedValueOnce(json({ projects: [remoteProject(), remoteProject({ id: 'x', title: 'New' })] }));
    render(<ProjectsLibrary />);
    expect(await screen.findByText('Remote Pack')).toBeTruthy();
    expect(screen.queryByTestId('guest-banner')).toBeNull();

    const input = screen.getByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: URL_B } });
    fireEvent.submit(input.closest('form')!);
    expect(await screen.findByText('Project created.')).toBeTruthy();
    const [, init] = fetchMock.mock.calls[1];
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toMatchObject({ sourceUrl: URL_B, visibility: 'private' });
  });

  it('falls back to local projects with an honest notice when cloud storage is unavailable', async () => {
    createOrUpdateLocalProject({ sourceUrl: URL_A, title: 'Local Pack' });
    fetchMock.mockResolvedValueOnce(json({ error: 'Project storage is unavailable.', code: 'projects_unavailable' }, 503));
    render(<ProjectsLibrary />);
    expect(await screen.findByText('Local Pack')).toBeTruthy();
    expect(screen.getByText(/Cloud project storage is currently unavailable/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Import local projects' })).toBeNull();
  });

  it('imports local projects and removes only the ones that succeeded', async () => {
    const a = createOrUpdateLocalProject({ sourceUrl: URL_A, title: 'Local A' })!.project;
    createOrUpdateLocalProject({ sourceUrl: URL_B, title: 'Local B' });
    fetchMock
      .mockResolvedValueOnce(json({ projects: [] }))
      .mockResolvedValueOnce(json({ project: remoteProject(), created: true }, 201))
      .mockResolvedValueOnce(json({ error: 'nope', code: 'projects_unavailable' }, 503))
      .mockResolvedValueOnce(json({ projects: [remoteProject()] }));
    render(<ProjectsLibrary />);
    fireEvent.click(await screen.findByRole('button', { name: 'Import local projects' }));
    expect(await screen.findByText('Imported 1 of 2 local project(s).')).toBeTruthy();
    const remaining = readLocalProjects();
    expect(remaining).toHaveLength(1);
    // Local list is newest-first, so Local B was imported first and Local A failed.
    expect(remaining[0].id).toBe(a.id);
  });
});

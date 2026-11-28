import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { StudioError } from '@/lib/studio/errors';

const boundary = vi.hoisted(() => ({
  owner: vi.fn(),
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  remove: vi.fn(),
}));

vi.mock('@/lib/studio/security', async (original) => ({
  ...(await original<object>()),
  requireStudioOwner: boundary.owner,
}));
vi.mock('@/lib/projects/project-store', async (original) => ({
  ...(await original<object>()),
  listProjects: boundary.list,
  getProject: boundary.get,
  createOrFindProject: boundary.create,
  updateProject: boundary.update,
  deleteProject: boundary.remove,
}));

import { GET as listRoute, POST as createRoute } from '../route';
import { DELETE, GET as getRoute, PATCH } from '../[projectId]/route';

const owner = { subject: 'verified-owner' };
const id = '0b0b55ec-81f8-4cbf-91b3-75f67796b9c1';
const SOURCE_URL = 'https://www.youtube.com/watch?v=auJzb1D-fag';
const project = {
  id,
  sourceHash: '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea',
  sourceUrl: SOURCE_URL,
  videoId: 'auJzb1D-fag',
  title: 'Test Video Pack',
  visibility: 'private',
  createdAt: '2026-11-27T00:00:00.000Z',
  updatedAt: '2026-11-27T00:00:00.000Z',
  storage: 'remote',
};
const ctx = { params: Promise.resolve({ projectId: id }) };

function req(method = 'GET', body?: unknown, path = '/api/projects', headers: Record<string, string> = {}) {
  return new NextRequest(`https://uvai.io${path}`, {
    method,
    headers: { origin: 'https://uvai.io', 'content-type': 'application/json', ...headers },
    ...(body === undefined || method === 'GET' ? {} : { body: JSON.stringify(body) }),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  boundary.owner.mockResolvedValue(owner);
  boundary.list.mockResolvedValue([project]);
  boundary.get.mockResolvedValue(project);
  boundary.create.mockResolvedValue({ project, created: true });
  boundary.update.mockResolvedValue({ ...project, visibility: 'shared' });
  boundary.remove.mockResolvedValue(undefined);
});

const authError = () => new StudioError(401, 'authentication_required', 'Sign in to manage projects.');

describe('GET /api/projects', () => {
  it('lists owned projects with private no-store headers', async () => {
    const response = await listRoute(req());
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ projects: [project] });
    expect(boundary.list).toHaveBeenCalledWith(owner);
    expect(response.headers.get('cache-control')).toBe('private, no-store');
    expect(response.headers.get('x-content-type-options')).toBe('nosniff');
  });

  it('requires verified authentication', async () => {
    boundary.owner.mockRejectedValue(authError());
    const response = await listRoute(req());
    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ error: 'Sign in to manage projects.', code: 'authentication_required' });
    expect(boundary.list).not.toHaveBeenCalled();
  });
});

describe('POST /api/projects', () => {
  it('creates a project (201) and reports duplicates (200, created: false)', async () => {
    const created = await createRoute(req('POST', { sourceUrl: SOURCE_URL, title: 'Test Video Pack' }));
    expect(created.status).toBe(201);
    expect(await created.json()).toEqual({ project, created: true });

    boundary.create.mockResolvedValue({ project, created: false });
    const duplicate = await createRoute(req('POST', { sourceUrl: SOURCE_URL }));
    expect(duplicate.status).toBe(200);
    expect((await duplicate.json()).created).toBe(false);
  });

  it('requires authentication and a same-origin request', async () => {
    boundary.owner.mockRejectedValue(authError());
    expect((await createRoute(req('POST', { sourceUrl: SOURCE_URL }))).status).toBe(401);
    boundary.owner.mockResolvedValue(owner);
    const cross = await createRoute(req('POST', { sourceUrl: SOURCE_URL }, '/api/projects', { origin: 'https://evil.example' }));
    expect(cross.status).toBe(403);
    expect((await cross.json()).code).toBe('invalid_origin');
    expect(boundary.create).not.toHaveBeenCalled();
  });

  it('rejects bad bodies and extra fields', async () => {
    for (const body of [{}, { sourceUrl: '' }, { sourceUrl: SOURCE_URL, owner_subject: 'spoof' }]) {
      const response = await createRoute(req('POST', body));
      expect(response.status).toBe(400);
      expect((await response.json()).code).toBe('invalid_request');
    }
    expect(boundary.create).not.toHaveBeenCalled();
  });

  it('requires a JSON content type', async () => {
    const response = await createRoute(req('POST', { sourceUrl: SOURCE_URL }, '/api/projects', { 'content-type': 'text/plain' }));
    expect(response.status).toBe(415);
  });

  it('maps unexpected failures to a sanitized 500', async () => {
    boundary.create.mockRejectedValue(new Error('secret database detail'));
    const response = await createRoute(req('POST', { sourceUrl: SOURCE_URL }));
    expect(response.status).toBe(500);
    expect(JSON.stringify(await response.json())).not.toContain('secret');
  });
});

describe('/api/projects/[projectId]', () => {
  const path = `/api/projects/${id}`;

  it('gets a project', async () => {
    const response = await getRoute(req('GET', undefined, path), ctx);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ project });
    expect(boundary.get).toHaveBeenCalledWith(owner, id);
  });

  it('returns 404 for a missing or other-owner project', async () => {
    boundary.get.mockRejectedValue(new StudioError(404, 'project_not_found', 'Project not found.'));
    const response = await getRoute(req('GET', undefined, path), ctx);
    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ error: 'Project not found.', code: 'project_not_found' });
  });

  it('patches title/visibility and validates the body', async () => {
    const ok = await PATCH(req('PATCH', { visibility: 'shared' }, path), ctx);
    expect(ok.status).toBe(200);
    expect((await ok.json()).project.visibility).toBe('shared');
    expect(boundary.update).toHaveBeenCalledWith(owner, id, { visibility: 'shared' });
    for (const body of [{}, { visibility: 'public' }, { title: '' }, { owner_subject: 'spoof' }]) {
      expect((await PATCH(req('PATCH', body, path), ctx)).status).toBe(400);
    }
  });

  it('deletes a project', async () => {
    const response = await DELETE(req('DELETE', undefined, path), ctx);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ deleted: true, id });
    expect(boundary.remove).toHaveBeenCalledWith(owner, id);
  });

  it('requires auth and same-origin on PATCH and DELETE', async () => {
    const cross = { origin: 'https://evil.example' };
    expect((await PATCH(req('PATCH', { title: 'x' }, path, cross), ctx)).status).toBe(403);
    expect((await DELETE(req('DELETE', undefined, path, cross), ctx)).status).toBe(403);
    boundary.owner.mockRejectedValue(authError());
    expect((await getRoute(req('GET', undefined, path), ctx)).status).toBe(401);
    expect((await PATCH(req('PATCH', { title: 'x' }, path), ctx)).status).toBe(401);
    expect((await DELETE(req('DELETE', undefined, path), ctx)).status).toBe(401);
    expect(boundary.update).not.toHaveBeenCalled();
    expect(boundary.remove).not.toHaveBeenCalled();
  });
});

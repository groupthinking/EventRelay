import type { NextRequest } from 'next/server';
import { guardedProjectRoute } from '@/lib/projects/project-http';
import { createOrFindProject, createProjectSchema, listProjects } from '@/lib/projects/project-store';
import { StudioError } from '@/lib/studio/errors';
import { readStudioJson, requireStudioMutationOrigin, requireStudioOwner } from '@/lib/studio/security';

export const runtime = 'nodejs';

export function GET(request: NextRequest): Promise<Response> {
  return guardedProjectRoute(async () => {
    const owner = await requireStudioOwner(request);
    return Response.json({ projects: await listProjects(owner) });
  });
}

export function POST(request: NextRequest): Promise<Response> {
  return guardedProjectRoute(async () => {
    const owner = await requireStudioOwner(request);
    requireStudioMutationOrigin(request);
    const parsed = createProjectSchema.safeParse(await readStudioJson(request));
    if (!parsed.success) throw new StudioError(400, 'invalid_request', 'Invalid project request.');
    const { project, created } = await createOrFindProject(owner, parsed.data);
    return Response.json({ project, created }, { status: created ? 201 : 200 });
  });
}

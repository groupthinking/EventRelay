import type { NextRequest } from 'next/server';
import { z } from 'zod';
import { guardedProjectRoute } from '@/lib/projects/project-http';
import { createOrFindProject, createProjectSchema, listProjects } from '@/lib/projects/project-store';
import { PROJECT_VISIBILITIES } from '@/lib/projects/project-types';
import { StudioError } from '@/lib/studio/errors';
import { readStudioJson, requireStudioMutationOrigin, requireStudioOwner } from '@/lib/studio/security';

export const runtime = 'nodejs';

const listQuerySchema = z
  .object({
    visibility: z.enum(PROJECT_VISIBILITIES).optional(),
    q: z.string().trim().max(160).optional(),
  })
  .strict();

export function GET(request: NextRequest): Promise<Response> {
  return guardedProjectRoute(async () => {
    const owner = await requireStudioOwner(request);
    const params = Object.fromEntries(request.nextUrl.searchParams.entries());
    const query = listQuerySchema.safeParse(params);
    if (!query.success) throw new StudioError(400, 'invalid_query', 'Invalid project query.');
    const projects = await listProjects(owner, { visibility: query.data.visibility, query: query.data.q });
    return Response.json({ projects });
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

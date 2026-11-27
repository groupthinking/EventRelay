import type { NextRequest } from 'next/server';
import { guardedProjectRoute } from '@/lib/projects/project-http';
import { deleteProject, getProject, updateProject, updateProjectSchema } from '@/lib/projects/project-store';
import { StudioError } from '@/lib/studio/errors';
import { readStudioJson, requireStudioMutationOrigin, requireStudioOwner } from '@/lib/studio/security';

export const runtime = 'nodejs';

type RouteContext = { params: Promise<{ projectId: string }> };

export function GET(request: NextRequest, context: RouteContext): Promise<Response> {
  return guardedProjectRoute(async () => {
    const owner = await requireStudioOwner(request);
    const { projectId } = await context.params;
    return Response.json({ project: await getProject(owner, projectId) });
  });
}

export function PATCH(request: NextRequest, context: RouteContext): Promise<Response> {
  return guardedProjectRoute(async () => {
    const owner = await requireStudioOwner(request);
    requireStudioMutationOrigin(request);
    const { projectId } = await context.params;
    const parsed = updateProjectSchema.safeParse(await readStudioJson(request));
    if (!parsed.success) throw new StudioError(400, 'invalid_request', 'Invalid project update.');
    return Response.json({ project: await updateProject(owner, projectId, parsed.data) });
  });
}

export function DELETE(request: NextRequest, context: RouteContext): Promise<Response> {
  return guardedProjectRoute(async () => {
    const owner = await requireStudioOwner(request);
    requireStudioMutationOrigin(request);
    const { projectId } = await context.params;
    await deleteProject(owner, projectId);
    return Response.json({ deleted: true, id: projectId });
  });
}

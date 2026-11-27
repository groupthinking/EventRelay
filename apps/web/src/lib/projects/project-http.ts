import 'server-only';

import { StudioError } from '@/lib/studio/errors';

export function privateProjectResponse(response: Response): Response {
  const headers = new Headers(response.headers);
  headers.set('cache-control', 'private, no-store');
  headers.set('vary', 'Cookie, Origin');
  headers.set('x-content-type-options', 'nosniff');
  return new Response(response.body, { status: response.status, headers });
}

/** Run a handler; map every failure to a flat `{ error, code }` envelope. */
export async function guardedProjectRoute(work: () => Promise<Response>): Promise<Response> {
  try {
    return privateProjectResponse(await work());
  } catch (error) {
    if (error instanceof StudioError) {
      const status = error.status >= 400 && error.status <= 599 ? error.status : 502;
      return privateProjectResponse(Response.json({ error: error.message, code: error.code }, { status }));
    }
    return privateProjectResponse(
      Response.json(
        { error: 'Project request could not be completed. Reload and try again.', code: 'projects_error' },
        { status: 500 },
      ),
    );
  }
}

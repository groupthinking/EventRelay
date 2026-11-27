import 'server-only';

import { StudioError } from '@/lib/studio/errors';
import { privateResponse } from '@/lib/studio/security';

/** Run a handler; map every failure to a flat `{ error, code }` envelope. */
export async function guardedProjectRoute(work: () => Promise<Response>): Promise<Response> {
  try {
    return privateResponse(await work());
  } catch (error) {
    if (error instanceof StudioError) {
      const status = error.status >= 400 && error.status <= 599 ? error.status : 502;
      return privateResponse(Response.json({ error: error.message, code: error.code }, { status }));
    }
    return privateResponse(
      Response.json(
        { error: 'Project request could not be completed. Reload and try again.', code: 'projects_error' },
        { status: 500 },
      ),
    );
  }
}

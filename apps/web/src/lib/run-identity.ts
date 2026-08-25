import 'server-only';

import { getToken } from 'next-auth/jwt';

/**
 * Who is acting on a delivery run.
 *
 * Runs are owned rows: `delivery_runs.user_id` scopes every read and every
 * approval. There is no RLS here, so the identity must be resolved from the
 * signed session on the server and never from a request body — a client-supplied
 * user id would let anyone approve anyone else's spec.
 *
 * In development without NEXTAUTH_SECRET the app has no session at all; rather
 * than silently ownerless runs, a single explicit local identity is used and is
 * refused outright in production.
 */

export const LOCAL_DEV_USER = 'local-dev@eventrelay.invalid';

export async function resolveRunUserId(request: Request): Promise<string | null> {
  const secret = process.env.NEXTAUTH_SECRET;

  if (secret) {
    try {
      const token = await getToken({
        req: request as Parameters<typeof getToken>[0]['req'],
        secret,
      });
      const email = typeof token?.email === 'string' ? token.email.trim() : '';
      if (email) return email.toLowerCase();
    } catch {
      // fall through — an unreadable token is the same as no session
    }
  }

  if (process.env.NODE_ENV === 'production') return null;
  return LOCAL_DEV_USER;
}

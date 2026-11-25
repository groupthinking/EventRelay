import 'server-only';

import { getNextAuthJwtFromRequest } from '@/lib/auth-jwt';
import type { NextRequest } from 'next/server';
import { StudioError } from './errors';

export type StudioOwner = Readonly<{ subject: string }>;

export async function requireStudioOwner(request: NextRequest): Promise<StudioOwner> {
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret?.trim()) {
    throw new StudioError(503, 'authentication_unavailable', 'Studio authentication is unavailable.');
  }

  const token = await getNextAuthJwtFromRequest(request, secret);
  const subject = token?.sub;
  if (typeof subject !== 'string' || !subject.trim() || subject.length > 512) {
    throw new StudioError(401, 'authentication_required', 'Sign in to use the app builder.');
  }
  return Object.freeze({ subject });
}

function isDevelopmentPreviewOrigin(origin: string | null): boolean {
  if (!origin || process.env.NODE_ENV !== 'development') return false;

  // The sandbox proxy can expose a public origin while Next sees a local URL.
  // Only platform configuration adds trust; request/forwarding headers never do.
  return [process.env.V0_SANDBOX_URL, process.env.V0_RUNTIME_URL, process.env.V0_BUILD_URL].some((value) => {
    if (!value) return false;
    try {
      const url = new URL(value);
      return url.protocol === 'https:' && !url.username && !url.password && url.origin === origin;
    } catch {
      return false;
    }
  });
}

export function requireStudioMutationOrigin(request: NextRequest): void {
  const origin = request.headers.get('origin');
  if (request.headers.get('sec-fetch-site') === 'cross-site' ||
      (origin !== request.nextUrl.origin && !isDevelopmentPreviewOrigin(origin))) {
    throw new StudioError(403, 'invalid_origin', 'This request must originate from Studio.');
  }
}

export async function readStudioJson(request: NextRequest): Promise<unknown> {
  const maxBytes = 32_768;
  if (request.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') {
    throw new StudioError(415, 'json_required', 'Send an application/json request.');
  }
  const tooLarge = () => new StudioError(413, 'request_too_large', 'The Studio request is too large.');
  const declaredSize = request.headers.get('content-length');
  if (declaredSize !== null && Number(declaredSize) > maxBytes) throw tooLarge();
  if (!request.body) throw new StudioError(400, 'invalid_json', 'Invalid JSON request.');

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maxBytes) {
        await reader.cancel().catch(() => undefined);
        throw tooLarge();
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)) as unknown;
  } catch (error) {
    if (error instanceof StudioError) throw error;
    throw new StudioError(400, 'invalid_json', 'Invalid JSON request.');
  } finally {
    reader.releaseLock();
  }
}

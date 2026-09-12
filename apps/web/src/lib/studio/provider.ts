import 'server-only';

import { createV0Client } from 'v0';
import { StudioError } from './errors';

export function studioProvider() {
  const key = process.env.V0_API_KEY?.trim();
  if (!key) throw new StudioError(503, 'builder_unavailable', 'The app builder is not configured.');
  return createV0Client({
    auth: key,
    throwOnError: true,
    fetch: async (input) => {
      const request = new Request(input);
      const signal = AbortSignal.any([request.signal, AbortSignal.timeout(20_000)]);
      try {
        const response = await fetch(new Request(request, { signal, cache: 'no-store', redirect: 'error' }));
        if (!response.ok) {
          await response.body?.cancel().catch(() => undefined);
          throw new StudioError(response.status, 'builder_request_failed', 'The app builder could not complete this request. Reload the chat before retrying.');
        }
        return response;
      } catch (error) {
        if (error instanceof StudioError) throw error;
        throw new StudioError(502, 'builder_unreachable', 'The app builder could not be reached. Reload the chat before retrying.');
      }
    },
  });
}

export function unwrapStudioResult<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || !result.response?.ok) {
    const status = result.response?.status;
    throw new StudioError(status && status >= 400 && status <= 599 ? status : 502, 'builder_request_failed', 'The app builder could not complete this request. Reload the chat before retrying.');
  }
  if (result.data === undefined) throw new StudioError(502, 'invalid_builder_response', 'The app builder returned an invalid response.');
  return result.data;
}
